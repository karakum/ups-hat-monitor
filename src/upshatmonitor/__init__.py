import logging.config
import os

from .daemon import Daemon

import sys
import time
import signal
import logging
import argparse
import traceback

from .INA219 import INA219
from .max17034 import Max17034

if sys.version_info[0] == 2:
    import ConfigParser as CP
else:
    import configparser as CP

from logging.handlers import SysLogHandler
from threading import Event

exitEvent = Event()

class Controller(object):
    def __init__(self, config):
        self.config = config
        self.stay_alive = True

        if self.config.get('General', 'hat_driver') not in ['max17034', 'ina219']:
            logging.error("unknown driver: %s " % self.config.get('General', 'hat_driver'))
            self.stay_alive = False
            return

        self.hat_driver = self.config.get('General', 'hat_driver')
        self.i2c_bus = int(self.config.get('General', 'i2c_bus'))

        self.alert_level = int(self.config.get('Monitor', 'alert_level'))
        self.alert_action = self.config.get('Monitor', 'alert_action')
        self.critical_level = int(self.config.get('Monitor', 'critical_level'))
        self.critical_action = self.config.get('Monitor', 'critical_action')

        if self.hat_driver == 'max17034':
            self.driver = Max17034(0x36, self.i2c_bus)
        else:
            self.driver = INA219(self.i2c_bus, 0x42)
            time.sleep(1)  # need to update ADC
        self.v = 0
        self.c = 0
        self.discharge = False

    def reload(self):
        # just log status, voltage and capacity
        logging.info("UPS HAT Monitor: %(status)s %(volt).2fV (%(cap)i%%)" %
                     {'volt': self.v, 'cap': self.c, 'status': ("ON BATTERY" if self.discharge else "ON LINE")})

    def run(self):
        logging.info("UPS HAT Monitor started: driver=%s, i2c_bus=%d, alert=%d(%s), critical=%d(%s)",
                     self.hat_driver, self.i2c_bus,
                     self.alert_level, self.alert_action, self.critical_level, self.critical_action)

        discharge_last = None
        while self.stay_alive:
            try:
                self.driver.collectMeasures()
                self.v = self.driver.getVoltage()
                self.c = self.driver.getCapacity()

                self.discharge = self.driver.isDischarging()
                if self.discharge:
                    if self.c < self.alert_level:
                        if self.c < self.critical_level:
                            # CRITICAL !!!
                            logging.warning("UPS Battery has reached a critical level (%d%% < %d%%)", self.c, self.critical_level)
                            do_action(self.critical_action)
                        else:
                            # ALERT !!!
                            logging.warning("UPS Battery has reached alert level (%d%% < %d%%)", self.c, self.alert_level)
                            do_action(self.alert_action)
                if discharge_last != self.discharge:
                    discharge_last = self.discharge
                    self.reload()
                exitEvent.wait(10)

            except KeyboardInterrupt:
                self.stay_alive = False

        # main loop exit, call cleanup method
        self._shutdown()

    def shutdown(self):
        """Tell the main loop to exit and shut down gracefully"""
        self.stay_alive = False
        exitEvent.set()

    def _shutdown(self):
        logging.info("UPS HAT Monitor shutting down")


CONFIGFILES = ['/etc/upshatmonitor.conf', os.path.expanduser('~/.upshatmonitor.conf'), 'upshatmonitor.conf']
CONTROLLER = None


def init_syslog_logging(level=logging.INFO):
    """initialize logging"""
    # logging.basicConfig(level=loglevel)
    logger = logging.getLogger()
    logger.setLevel(level)
    slh = SysLogHandler(address='/dev/log')
    slh.setFormatter(logging.Formatter("upshatmonitor[%(process)d]: %(message)s"))
    # log debug/error messages to syslog info level
    slh.priority_map["DEBUG"] = "info"
    slh.priority_map["ERROR"] = "info"

    slh.setLevel(level)
    logger.addHandler(slh)
    return logger


def reload_config():
    """reload configuration"""
    newconfig = CP.ConfigParser()
    newconfig.read(CONFIGFILES)

    return newconfig


def sighup(signum, frame):
    """handle sighup to reload config"""
    newconfig = reload_config()
    if CONTROLLER != None:
        CONTROLLER.config = newconfig

    CONTROLLER.reload()


def sigterm(signum, frame):
    CONTROLLER.shutdown()


def do_action(action):
    args = action.split()
    if len(args) > 1:
        argv = args[1:]
    else:
        argv = None

    try:
        os.execv(args[0], argv)
    except OSError as err:
        logging.error("ERROR while executing %s:%s" % (action, err))


def main():
    global CONFIGFILES, CONTROLLER

    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--foreground", action="store_true", dest="foreground", default=False, help="do not fork to background")
    parser.add_argument("--pidfile", action="store", dest="pidfile")
    parser.add_argument("-c", "--config", action="store", dest="config", help="configfile")
    parser.add_argument("--log-config", action="store", dest="logconfig", help="logging configuration file")
    parser.add_argument("--user", action="store", dest="user", help="run as user")
    parser.add_argument("--group", action="store", dest="group", help="run as group")
    parser.add_argument("-d", "--debug", action="store_true", dest="debug", default=False, help="run in debug mode")

    opts = parser.parse_args()

    # keep a copy of stderr in case something goes wrong
    stderr = sys.stderr
    try:
        daemon = Daemon(opts.pidfile)
        if not opts.foreground:
            daemon.daemonize()
        if opts.config:
            CONFIGFILES = [opts.config]
        config = reload_config()

        # drop privileges
        daemon.drop_privileges(opts.user, opts.group)

        if opts.logconfig:
            logging.config.fileConfig(opts.logconfig)

        if opts.foreground:
            if opts.debug:
                logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
            else:
                logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
        else:
            # log to syslog
            if not opts.logconfig:
                init_syslog_logging()
            signal.signal(signal.SIGHUP, sighup)
            signal.signal(signal.SIGTERM, sigterm)

        logging.info("UPS HAT Monitor starting up...")

        CONTROLLER = Controller(config)
        CONTROLLER.run()

        logging.info("UPS HAT Monitor shut down")
    except Exception:
        exc = traceback.format_exc()
        errtext = "Unhandled exception in main thread: \n %s \n" % exc
        stderr.write(errtext)
        logging.error(errtext)
