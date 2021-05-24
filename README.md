UPS HAT Monitor
============

### a Python monitor script for Raspi UPS HAT

[Raspi UPS HAT](https://it.aliexpress.com/item/Geekworm-RPi-UPS-HAT-Board-for-Raspberry-Pi-3-Model-B-Pi-2B-B/32766227090.html) was a board for Raspberry Pi with a controller and a LiPo battery that act like an UPS. On board, there's a MAX17034 chip (connected to i2c bus) that could be asked for battery voltage and remaining capacity (0-100%).
With this simple script, far to be perfect (and you are encouraged to fix and improve it !), you can shutdown safely your RPi when battery on UPS Hat reach a critical level, avoid any potentials data loss.

[UPS HAT For Raspberry Pi](https://www.waveshare.com/wiki/UPS_HAT) is 5V Uninterruptible Power Supply, Multi Battery Protection Circuits. 

### Requirements

You need to install smbus2 with *sudo pip install smbus2*

### Install

Installation is pretty simple: just do *python setup.py build* and *sudo python setup.py install*. 
 
Then you can use it as other system services with:

*/etc/init.d/raspiupsmonitor [start|stop]* OR *service start / systemctl start *

### Configure

Configuration is in `raspiupsmonitor.cfg` must be copied to either 
* `/etc/upshatmonitor.conf`  
* `~/.upshatmonitor.conf`
* `upshatmonitor.conf`

You must specify driver in [General] part

    [General]
    # ina219 OR max17034
    hat_driver=ina219

and the relevant part is [Monitor]:

    [Monitor]
    # On alert level of 10%, just alert all users...
    alert_level=10
    alert_action=/usr/bin/wall "UPS Battery is dying..."
    # When battery is dying, halt the system safely
    critical_level=5
    critical_action=/sbin/halt -p

"level" is the percentage of power remained, in a range from 0 to 100. When battery is discharging and reach the alert or critical level, "action" was executed.
