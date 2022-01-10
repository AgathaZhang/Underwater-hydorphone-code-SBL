# coding=utf-8
# humidity.py
import threading
import struct
import time
import smbus


class HumidityData(object):
    _temp = 0  # 温度
    _humi = 0  # 湿度
    _times = 0  # 读取次数

    def __init__(self, temp=0, humi=0, times=0):
        self._temp = temp
        self._humi = humi
        self._times = times

    def pack(self):
        return struct.pack('<2fi', self._humi, self._temp, self._times)


class Humidity:
    _data = HumidityData()
    _bus = None  # 控制总线
    _times = 0  # 读取次数

    def init(self):
        # 初始化控制总线
        self._bus = smbus.SMBus(1)

        # 启动深度传感器run线程
        _humi_run_thread = threading.Thread(
            target=self._run, name="humi_run", args=())
        _humi_run_thread.start()

        return True

    def get(self):
        return self._data

    def _run(self):
        while True:
            self._read()
            time.sleep(1)

    def _read(self):
        try:
            self._bus.write_i2c_block_data(0x44, 0x2C, [0x06])
            time.sleep(0.5)
            _data = self._bus.read_i2c_block_data(0x44, 0x00, 6)
            _temp = ((((_data[0] * 256.0) + _data[1]) * 175) / 65535.0) - 45
            _humi = 100 * (_data[3] * 256 + _data[4]) / 65535.0

            self._data = HumidityData(_temp, _humi, self._times)

            self._times += 1
        except:
            print("Humidity _read error.")

