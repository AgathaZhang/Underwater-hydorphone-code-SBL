# coding=utf-8
# tcp.py
import socket
from tkinter.constants import TRUE
import serial
import time
import struct
import numpy
import threading
import define
from multiprocessing import Process, Lock
from config import configIns
from proto.robot import CMD_ROBOT, CMD_ROBOT_NONE, CMD_ROBOT_END, get_robot_cmd
from proto.sonar import CMD_SONAR, CMD_SONAR_NONE, CMD_SONAR_END, get_sonar_cmd
from tcp_handle import handle_data


class Tcp:
    # 基本属性
    _ip = "127.0.0.1"
    _port = 9500
    _conn = None
    _tcp_ok = False
    _ready_login_ok = False  # 是否已就绪准备登录
    _login_ok = False  # 是否已就绪登录
    _post_config_ok = False  # 是否已经完成配置上报

    _portx = "/dev/serial0"
    _bps = 115200
    _timex = None
    _ser = None

    _buffer_size = 1024 * 10
    _header_size = struct.calcsize('<2HI8s')
    _lock = Lock()
    _last_send_time = 0

    # 初始化
    def init(self, ip="127.0.0.1", port=9500, portx="/dev/ttyS0", bps=115200, timex=None):
        self._ip = ip
        self._port = port
        self._tcp_ok = False

        self._portx = portx
        self._bps = bps
        self._timex = timex

        self._first_connect = True  # 第一次登录

        # 启动tcp run线程
        _tcp_run_thread = threading.Thread(
            target=self._run, name="tcp_run", args=())
        _tcp_run_thread.start()

        return True

    # 发送数据
    def send(self, cmd, data):
        if not self._tcp_ok:
            print("Tcp send tcp_ok error.")
            return

        if configIns.plat_form == define.PLAT_FORM.PLATFORM_SONAR:
            self.send_lora(cmd, data)
            return

        _cmd_value = cmd.value
        _type_cmd = type(cmd)
        if _type_cmd == CMD_SONAR:
            _cmd_value = get_sonar_cmd(cmd)
        elif _type_cmd == CMD_ROBOT:
            _cmd_value = get_robot_cmd(cmd)
        else:
            print("Tcp send _type_cmd error. _type_cmd=%s" % (str(_type_cmd)))

        header = struct.pack('<2HI8s', 0x55AA,  self._header_size +
                             2 + len(data), _cmd_value, configIns.sn.sn.encode())

        body = header + data

        _crc = self._generate_crc(body)

        body = body + struct.pack('<H', _crc)

        try:
            curtime = time.time()
            if curtime - self._last_send_time < 0.05:
                time.sleep(0.05)
            self._last_send_time = curtime
            self._conn.send(body)
        except:
            self._tcp_ok = False
            print("Tcp send send error.")

    # 发送数据给lora转发 - TCP版
    def send_lora(self, cmd, data):
        self._lock.acquire()

        if not self._tcp_ok:
            print("Tcp send tcp_ok error.")
            self._lock.release()
            return

        _cmd_value = cmd.value
        _type_cmd = type(cmd)
        if _type_cmd == CMD_SONAR:
            _cmd_value = get_sonar_cmd(cmd)
        elif _type_cmd == CMD_ROBOT:
            _cmd_value = get_robot_cmd(cmd)
        else:
            print("Tcp send _type_cmd error. _type_cmd=%s" % (str(_type_cmd)))

        header = struct.pack('<2HI8s', 0x55AA,  self._header_size +
                             2 + len(data), _cmd_value, configIns.sn.sn.encode())

        body = header + data

        _crc = self._generate_crc(body)

        body = body + struct.pack('<H', _crc)

        try:
            curtime = time.time()
            if curtime - self._last_send_time < 0.2:
                time.sleep(0.2)
            self._last_send_time = time.time()
            print("send. time=%.2f, data=%s" % (time.time(), body.hex()))

            if configIns.plat_form == define.PLAT_FORM.PLATFORM_SONAR and configIns.sonar.use_lora:
                self._ser.write(body)
            else:
                self._conn.send(body)
        except:
            self._tcp_ok = False
            self._lock.release()
            print("Tcp send_lora send error.")

        self._lock.release()

    # SONAR发送数据(LOAR数据包封装)
    def loar_pack(self, addr, ch, data):
        head = struct.pack('>HB', addr, ch)
        body = head + data
        return body

    # tcp运行线程
    def _run(self):
        while True:
            if not self._tcp_ok:
                if configIns.plat_form == define.PLAT_FORM.PLATFORM_SONAR and configIns.sonar.use_lora:
                    if not self._connect_serial():
                        time.sleep(5)
                else:
                    if not self._connect():
                        time.sleep(5)
            else:
                if configIns.plat_form == define.PLAT_FORM.PLATFORM_SONAR and configIns.sonar.use_lora:
                    self._recv_serial()
                else:
                    self._recv()

    # 连接server - TCP版
    def _connect(self):
        try:
            self._conn = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
            self._conn.connect((self._ip, self._port))
            self._tcp_ok = True

            self._login()

            print("Tcp _connect ok.")
            return True
        except Exception as e:
            self._tcp_ok = False
            print("Tcp _connect connect error. err=%s" % (str(e)))
            return False

    # 接收 - TCP版
    def _recv(self):
        _data_buffer = bytes()
        while True:
            try:
                _data = self._conn.recv(self._buffer_size)
                if not _data:
                    print("Tcp _recv data error.")
                    self._tcp_ok = False
                    break

                _data_buffer += _data
                print("Tcp _recv data. _data_buffer=%s" % (_data_buffer.hex()))
                while True:
                    data_buffer_len = len(_data_buffer)

                    # 数据流长度不足以解出头部
                    if data_buffer_len < self._header_size:
                        break

                    # 读取包头
                    _header = struct.unpack(
                        '<2HI8s', _data_buffer[:self._header_size])
                    data_size = _header[1]
                    cmd = _header[2]

                    # 分包情况处理
                    if data_buffer_len < data_size:
                        break

                    # 消息正文
                    _body = _data_buffer[self._header_size:data_size - 2]

                    if cmd == get_sonar_cmd(CMD_SONAR.CMD_READY_LOGIN_RES):
                        # SONAR准备登录
                        self._handle_sonar_ready_login_res(_body)
                    else:
                        # 数据处理
                        handle_data(cmd, _body)

                    # pop出处理完的数据
                    _data_buffer = _data_buffer[data_size:]
            except Exception as e:
                print("Tcp _recv error. err=%s" % (str(e)))
                self._tcp_ok = False
                break

    # 连接server - 串口版
    def _connect_serial(self):
        try:
            self._ser = serial.Serial(
                self._portx, self._bps, timeout=self._timex)
            self._tcp_ok = True

            self._login()

            print("Tcp _connect_serial ok.")
            return True
        except Exception as e:
            self._tcp_ok = False
            print("Tcp _connect_serial connect error. err=%s" % (str(e)))
            return False

    # 接收 - 串口版
    def _recv_serial(self):
        _data_buffer = bytes()
        print("_recv_serial start.")
        while True:
            try:
                _data = self._ser.read()
                if not _data:
                    print("Tcp _recv_serial data error.")
                    self._tcp_ok = False
                    break

                _data_buffer += _data
                # print("Tcp _recv_serial data. data=%s" % (_data_buffer.hex()))

                while True:
                    data_buffer_len = len(_data_buffer)

                    # 数据流长度不足以解出头部
                    if data_buffer_len < self._header_size:
                        break

                    # 读取包头
                    _header = struct.unpack(
                        '<2HI8s', _data_buffer[:self._header_size])
                    data_size = _header[1]
                    cmd = _header[2]

                    # 分包情况处理
                    if data_buffer_len < data_size+1:
                        break

                    # 消息正文
                    _body = _data_buffer[self._header_size:data_size - 2]

                    print("recv. time=%.2f, data=%s" % (time.time(), _data_buffer.hex()))

                    if cmd == get_sonar_cmd(CMD_SONAR.CMD_READY_LOGIN_RES):
                        # SONAR准备登录
                        self._handle_sonar_ready_login_res(_body)
                    elif cmd == get_sonar_cmd(CMD_SONAR.CMD_POST_RELOGIN_RES):
                        # SONAR再次登录
                        self._handle_sonar_relogin_res(_body)
                    elif cmd == get_sonar_cmd(CMD_SONAR.CMD_LOGIN_RES):
                        # SONAR登录
                        self._handle_sonar_login_res(_body)
                    elif cmd == get_sonar_cmd(CMD_SONAR.CMD_POST_CONFIG_RES):
                        # SONAR上报配置
                        self._handle_sonar_post_config_res(_body)
                    else:
                        # 数据处理
                        handle_data(cmd, _body)

                    # pop出处理完的数据
                    _data_buffer = _data_buffer[data_size+1:]
            except Exception as e:
                print("Tcp _recv_serial error. err=%s" % (str(e)))
                self._tcp_ok = False
                break

    # 连接成功后发送登录消息
    def _login(self):
        if not self._first_connect:
            return

        # 启动登录线程
        _run_login_thread = threading.Thread(
            target=self._run_login, name="run_login")
        _run_login_thread.start()

        return

    # 定时发送准备登录，直到准备登录成功
    def _run_ready_login(self):
        while True:
            if self._ready_login_ok:
                return

            # 发送准备登录请求
            _body = struct.pack('<8s', configIns.sn.sn.encode())
            self.send(CMD_SONAR.CMD_READY_LOGIN_REQ, _body)
            self._first_connect = False

            time.sleep(1)

    # SONAR连接成功后需要在CMD_SONAR.CMD_READY_LOGIN_RES的协议后请求登录
    def _handle_sonar_ready_login_res(self, data):
        ''' 处理SONAR准备登录回复 '''
        self._ready_login_ok = True

        _body = struct.unpack('<H', data)
        addr = _body[0]

        # # 发送登录请求
        # _body = struct.pack('<8sH', configIns.sn.sn.encode(), addr)
        # self.send_lora(CMD_SONAR.CMD_LOGIN_REQ, _body)
        # 启动登录线程
        _run_login_thread = threading.Thread(
            target=self._run_login, name="run_login", args=(addr, ))
        _run_login_thread.start()

        # # 发送配置信息
        # _body = configIns.sonar.pack()
        # self.send_lora(CMD_SONAR.CMD_POST_CONFIG_REQ, _body)
    
    # 收到此消息后，需要SONAR再次登录
    def _handle_sonar_relogin_res(self, data):
        ''' 处理SONAR的再次登录 '''
        # 发送登录请求
        _body = struct.pack('<8s', configIns.sn.sn.encode())
        self.send_lora(CMD_SONAR.CMD_LOGIN_REQ, _body)

    # 定时发送登录，直到登录成功
    def _run_login(self):
        while True:
            if self._login_ok:
                return

            # 发送登录请求
            _body = struct.pack('<8s', configIns.sn.sn.encode())
            self.send_lora(CMD_SONAR.CMD_LOGIN_REQ, _body)

            time.sleep(2)

    def _handle_sonar_login_res(self, data):
        ''' 处理SONAR登录回复 '''
        self._login_ok = True

        # 启动上报配置线程
        if True:
            _run_post_config_thread = threading.Thread(
                target=self._run_ready_post_config, name="run_post_config_thread", args=())
            _run_post_config_thread.start()

    # 定时发送上报配置，直到上报配置成功
    def _run_ready_post_config(self):
        while True:
            if self._post_config_ok:
                return

            # 发送配置信息
            _body = configIns.sonar.pack()
            self.send_lora(CMD_SONAR.CMD_POST_CONFIG_REQ, _body)

            time.sleep(2)

    def _handle_sonar_post_config_res(self, data):
        ''' 处理SONAR上报配置回复 '''
        self._post_config_ok = True

    # 生成校验码
    def _generate_crc(self, data):
        _crc = numpy.uint16(0xFFFFF)
        _index = 0
        for i in data:
            _crc ^= numpy.uint16(i)
            _n = 8
            while _n > 0:
                _temp = 0
                if (_crc & 0x0001 > 0):
                    _temp = 0xA001
                _crc = (_crc >> 1) ^ _temp
                _n -= 1
            _index += 1

        return _crc


# 单例模式
tcpIns = Tcp()

