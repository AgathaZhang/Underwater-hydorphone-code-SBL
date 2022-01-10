# coding=utf-8
# depth.py
import time
import ms5837
import threading
import struct
from config import configIns
import smbus
import RPi.GPIO as gpio


class DepthData(object):
    depth = 0  # 深度
    temperature = 0  # 温度
    times = 0  # 读取次数

    def __init__(self, depth=0, temperature=0, times=0):
        self.depth = depth
        self.temperature = temperature
        self.times = times

    def pack(self):
        return struct.pack('<2fi', self.depth, self.temperature, self.times)


class Depth:
    _data = DepthData()
    _bus = None  # 控制总线
    _sensor = ms5837.MS5837_30BA()  # 深度传感器
    _sensor_ok = False  # 深度传感器是否就绪
    _times = 0  # 读取次数

    def init(self):
        # 启动深度传感器run线程
        _depth_run_thread = threading.Thread(
            target=self._run, name="depth_run", args=())
        _depth_run_thread.start()

        return True

    def get(self):
        return self._data

    def _run(self):
        while True:
            if not self._sensor_ok:
                if not self._connect():
                    time.sleep(5)
            else:
                self._read()
                time.sleep(1)

    def _connect(self):
        # 初始化控制总线
        self._bus = smbus.SMBus(1)

        # 初始化深度传感器
        if not self._sensor.init():
            print("Data __depth_connect init error.")
            return False

        # 读取深度传感器一次数据
        if not self._sensor.read():
            print("Data __depth_connect read error.")
            return False

        # 设置流体密度为海水
        self._sensor.setFluidDensity(ms5837.DENSITY_SALTWATER)

        # gpio初始化 用于控制S发送
        gpio.setwarnings(False)
        gpio.setmode(gpio.BCM)
        gpio.setup(13, gpio.OUT)

        # 深度传感器就绪
        self._sensor_ok = True

        return True

    def _read(self):
        if self._sensor.read():
            _depth = self._sensor.depth()
            _temperature = self._sensor.temperature()
            _times = self._times
            self._data = DepthData(_depth, _temperature, _times)

            # 是否开启sonar send
            if _depth < configIns.robot.s_tx_depth:
                gpio.output(13, gpio.HIGH)  # 关闭S发送
            else:
                gpio.output(13, gpio.LOW)  # 打开S发送

            self._times += 1

        # 深度传感器未就绪
        self._sensor_ok = False

