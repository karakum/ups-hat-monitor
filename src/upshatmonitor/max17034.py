from smbus2 import SMBus
import struct


class Max17034:
    def __init__(self, address, bus):
        # MAX17043
        self.address = address
        self.i2c_bus = bus
        self.capacity = 0
        self.voltage = 0
        self.last_capacity = 0
        self.status = 1

    def readVoltage(self):
        with SMBus(self.i2c_bus) as bus:
            read = bus.read_byte_data(self.address, 2)

        swapped = struct.unpack("<H", struct.pack(">H", read))[0]
        voltage = swapped * 78.125 / 1000000
        return voltage

    def readCapacity(self):
        with SMBus(self.i2c_bus) as bus:
            read = bus.read_byte_data(self.address, 4)

        swapped = struct.unpack("<H", struct.pack(">H", read))[0]
        capacity = swapped / 256
        return capacity

    def getVoltage(self):
        return self.voltage

    def getCapacity(self):
        return self.capacity

    def isDischarging(self):
        return self.status == 0

    def collectMeasures(self):
        self.voltage = self.readVoltage()
        self.capacity = self.readCapacity()

        if self.capacity > self.last_capacity:
            self.last_capacity = self.capacity
            self.status = 1  # Charging..
        elif self.capacity < self.last_capacity:
            self.last_capacity = self.capacity
            self.status = 0  # Discharging....
        else:
            # No changes
            pass

if __name__ == '__main__':
    # 0 = /dev/i2c-0 (port I2C0)
    # 1 = /dev/i2c-1 (port I2C1)
    bus = 1
    # MAX17043
    address = 0x36

    max17034 = Max17034(address, bus)
    print('%(volt).2fV (%(cap)i%%)' % {'volt': max17034.readVoltage(), 'cap': max17034.readCapacity()})