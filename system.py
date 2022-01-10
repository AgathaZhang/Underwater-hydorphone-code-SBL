# coding=utf-8
# system.py
import threading
import struct
import time
import os


class SystemData(object):
    _cpu = 0  # cpu
    _cpu_temp = 0  # cpu温度
    _ram_free = 0  # 可用内存
    _ram_use = 0  # 已用内存
    _times = 0  # 读取次数

    def __init__(self, cpu=0, cpu_temp=0, ram_free=0, ram_use=0, times=0):
        self._cpu = cpu
        self._cpu_temp = cpu_temp
        self._ram_free = ram_free
        self._ram_use = ram_use
        self._times = times

    def pack(self):
        return struct.pack('<4fi', self._cpu, self._cpu_temp, self._ram_free, self._ram_use, self._times)


class System:
    _data = SystemData()
    _times = 0  # 读取次数

    def init(self):
        # 启动深度传感器run线程
        _system_run_thread = threading.Thread(
            target=self._run, name="system_run", args=())
        _system_run_thread.start()

        return True

    def get(self):
        return self._data

    def _run(self):
        while True:
            self._read()
            time.sleep(1)

    def _read(self):
        # 读取cpu温度
        with open("/sys/class/thermal/thermal_zone0/temp") as file:
            res = file.readline()
        _cpu_temp = float(res) / 1000

        # top命令
        res_str = os.popen(
            "top -bn1 | egrep '%Cpu\(s\)|MiB Mem'").read().strip()

        vals = res_str.split('\n')
        if len(vals) < 2:
            print("System _read vals len error. vals=%s" % (str(vals)))
            self._times += 1
            return False

        cpu_str = vals[0].split()
        if len(cpu_str) < 2:
            print("System _read cpu_str len error. cpu_str=%s" % (str(cpu_str)))
            return False
        _cpu = float(cpu_str[1])

        ram_str = vals[1].split()
        if len(ram_str) < 8:
            print("System _read ram_str len error. ram_str=%s" % (str(ram_str)))
            return False
        _ram_free = float(ram_str[5])
        _ram_use = float(ram_str[7])

        self._data = SystemData(
            _cpu, _cpu_temp, _ram_free, _ram_use, self._times)

        self._times += 1

