# coding=utf-8
# inclinometer.py
import time
import threading
import struct
import smbus
import math


class InclinometerData(object):
    x = 0  # 倾角x
    y = 0  # 倾角y
    z = 0  # 倾角z
    times = 0  # 读取次数

    def __init__(self, x=0, y=0, z=0, times=0):
        self.x = x
        self.y = y
        self.z = z
        self.times = times

    def pack(self):
        return struct.pack('<3fi', self.x, self.y, self.z, self.times)


class Inclinometer:
    _data = InclinometerData()
    _bus = None
    _bus_ok = False
    _address = 0x68
    _power_mgmt_1 = 0x6b
    _power_mgmt_2 = 0x6c
    _times = 0  # 读取次数

    def init(self):
        # 启动深度传感器run线程
        _inclinometer_run_thread = threading.Thread(
            target=self._run, name="inclinometer_run", args=())
        _inclinometer_run_thread.start()

        return True

    def get(self):
        return self._data

    def _run(self):
        while True:
            if not self._bus_ok:
                if not self._connect():
                    time.sleep(5)
            else:
                self._read()
                time.sleep(1)

    def _connect(self):
        self._bus = smbus.SMBus(0)
        self._bus_ok = True

        return True

    def _read(self):
        accel_xout = self._read_word_2c(0x3b)
        accel_yout = self._read_word_2c(0x3d)
        accel_zout = self._read_word_2c(0x3f)

        accel_xout_scaled = accel_xout / 16384.0
        accel_yout_scaled = accel_yout / 16384.0
        accel_zout_scaled = accel_zout / 16384.0

        x = self.get_x_rotation(
            accel_xout_scaled, accel_yout_scaled, accel_zout_scaled)
        y = self.get_y_rotation(
            accel_xout_scaled, accel_yout_scaled, accel_zout_scaled)
        z = self.get_z_rotation(
            accel_xout_scaled, accel_yout_scaled, accel_zout_scaled)

        self._data = InclinometerData(x, y, z, self._times)

        self._times += 1

    def _read_word_2c(self, adr):
        val = self.read_word(adr)
        if (val >= 0x8000):
            return -((65535 - val) + 1)
        else:
            return val

    def read_word(self, adr):
        self._bus.write_byte_data(self._address, self._power_mgmt_1, 0)
        high = self._bus.read_byte_data(self._address, adr)
        low = self._bus.read_byte_data(self._address, adr+1)
        val = (high << 8) + low
        return val

    def dist(self, a, b):
        return math.sqrt((a*a)+(b*b))

    def get_y_rotation(self, x, y, z):
        radians = math.atan2(x, self.dist(y, z))
        return -math.degrees(radians)

    def get_x_rotation(self, x, y, z):
        radians = math.atan2(y, self.dist(x, z))
        return math.degrees(radians)

    def get_z_rotation(self, x, y, z):
        radians = math.atan2(z, self.dist(x, y))
        return math.degrees(radians)

