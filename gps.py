# coding=utf-8
# gps.py
import threading
import struct
import time
import serial
import pynmea2


class GpsData(object):
    gps_qual = 0  # GPS状态
    times = 0  # 读取次数

    def __init__(self, gps_qual=0, times=0):
        self.gps_qual = gps_qual
        self.times = times

    def pack(self):
        return struct.pack('<2i', self.gps_qual, self.times)


class Gps:
    _data = GpsData()
    _serial = None
    _serial_ok = False
    _times = 0  # 读取次数

    def init(self):
        # 启动gps run线程
        _gps_run_thread = threading.Thread(
            target=self._run, name="gps_run", args=())
        _gps_run_thread.start()

        return True

    def get(self):
        return self._data

    def _run(self):
        while True:
            if not self._serial_ok:
                if not self._connect():
                    time.sleep(5)
            else:
                self._read()

    def _connect(self):
        self._serial = serial.Serial("/dev/ttyAMA0", 9600, timeout=5)
        self._serial.flushInput()  # 清空缓冲区
        self._serial_ok = True

        return True

    def _read(self):
        while True:
            try:
                data = self._serial.readline()
                data = str(data, encoding='utf-8')
                if data.startswith("$GPGGA"):
                    info = pynmea2.parse(data)
                    gps_qual = info.gps_qual
                    self._data = GpsData(gps_qual, self._times)

                self._times += 1
            except:
                self._serial_ok = False
                print("Gps _read read error.")
                break

