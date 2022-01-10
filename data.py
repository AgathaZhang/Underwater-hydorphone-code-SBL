# coding=utf-8
# data.py
import time
import threading
import depth
import system
import humidity
import gps
import sonar
import inclinometer
from tcp import tcpIns
from config import configIns
from proto.sonar import CMD_SONAR
from proto.robot import CMD_ROBOT
from define import PLAT_FORM


class Data:
    _depth = depth.Depth()
    _system = system.System()
    _humidity = humidity.Humidity()
    _gps = gps.Gps()
    _sonar = sonar.Sonar()
    _inclinometer = inclinometer.Inclinometer()

    def init(self):
        # 初始化深度传感器
        if configIns.data.depth:
            if not self._depth.init():
                return False

        # 初始化系统信息读取
        if configIns.data.system_top:
            if not self._system.init():
                return False

        # 初始化湿度传感器
        if configIns.data.humidity:
            if not self._humidity.init():
                return False

        # 初始化GPS
        if configIns.data.gps:
            if not self._gps.init():
                return False

        # 初始化sonar
        if configIns.data.sonar:
            if not self._sonar.init():
                return False

        # 初始化倾角仪
        if configIns.data.inclinometer:
            if not self._inclinometer.init():
                return False

        # 启动数据模块run线程
        _data_run_thread = threading.Thread(
            target=self._run, name="data_run", args=())
        _data_run_thread.start()

        return True

    def _run(self):
        while True:
            time.sleep(5)

            body = bytes()
            if configIns.data.depth:
                _depth = self._depth.get()
                body += _depth.pack()

            if configIns.data.system_top:
                _system = self._system.get()
                body += _system.pack()

            if configIns.data.humidity:
                _humi = self._humidity.get()
                body += _humi.pack()

            if configIns.data.gps:
                _gps = self._gps.get()
                body += _gps.pack()

            if configIns.data.inclinometer:
                _inclinometer = self._inclinometer.get()
                body += _inclinometer.pack()

            if configIns.data.sonar:
                _sonar = self._sonar.get()
                body += _sonar.pack()

            cmd = None
            if configIns.plat_form == PLAT_FORM.PLATFORM_ROBOT:
                cmd = CMD_ROBOT.CMD_POST_INFO_REQ
            elif configIns.plat_form == PLAT_FORM.PLATFORM_SONAR:
                cmd = CMD_SONAR.CMD_POST_INFO_REQ
            else:
                print("Data _run plat_form error. plat_form=%s",
                      str(configIns.plat_form))
                return

            tcpIns.send(cmd, body)

    def sonar_set_read_step(self, read_step):
        self._sonar.set_read_step(read_step)


# 单例模式
dataIns = Data()

