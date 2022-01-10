# coding=utf-8
# config.py
import configparser
import struct
import json
import socket
from define import PLAT_FORM, get_plat_form


class Sn(object):
    sn = "00000000"

    def init(self):
        # self.sn = config.get("sn", "sn")
        hostname = socket.gethostname()
        if len(hostname) == 8:
            self.sn = hostname
        else:
            self.sn = config.get("sn", "sn")


class Tcp(object):
    ip = "127.0.0.1"
    port = 9500

    def init(self):
        self.ip = config.get("tcp", "ip")
        self.port = config.getint("tcp", "port")


class Data(object):
    # 数据开关
    depth = True  # 水深传感器
    system_top = True  # 系统top命令
    humidity = True  # 温湿度传感器
    gps = False  # GPS
    sonar = True  # 水听器
    inclinometer = True  # 倾角仪

    def init(self):
        self.depth = config.getboolean("data", "depth")
        self.system_top = config.getboolean("data", "system_top")
        self.humidity = config.getboolean("data", "humidity")
        self.gps = config.getboolean("data", "gps")
        self.sonar = config.getboolean("data", "sonar")
        self.inclinometer = config.getboolean("data", "inclinometer")


class Robot(object):
    s_tx_depth = 0.5  # s项目tx的工作水深

    def init(self):
        self.s_tx_depth = config.getfloat("robot", "s_tx_depth")

    def pack(self):
        return struct.pack('<f', self.s_tx_depth)

    def set_config(self, s_tx_depth):
        self.s_tx_depth = s_tx_depth
        config.set('robot', 's_tx_depth', format(s_tx_depth, '.2f'))
        with open('config.ini', 'w') as f:
            config.write(f)


class Sonar(object):
    overlay_count = 10  # 叠加次数
    threshold_factor = 0  # 阈值因子
    threshold_offset = 0  # 阈值向前查找个数
    follow_index_range = 12800  # 跟随的index范围 12800：±6400

    # 不需要发给服务
    use_lora = True  # 是否使用LORA通讯

    # 不需要写入配置文件，也不需要发给服务
    follow_index = 0  # 跟随的index
    read_step = 0  # 读取音频步进值
    save_wav_second = 0  # 写wav文件剩余秒数

    def init(self):
        self.threshold_factor = config.getfloat("sonar", "threshold_factor")
        self.threshold_offset = config.getint("sonar", "threshold_offset")
        self.overlay_count = config.getint("sonar", "overlay_count")
        self.follow_index_range = config.getint("sonar", "follow_index_range")
        self.use_lora = config.getboolean("sonar", "use_lora")

    def pack(self):
        return struct.pack('<f3i', self.threshold_factor, self.threshold_offset, self.overlay_count, self.follow_index_range)

    def set_config(self, threshold_factor, threshold_offset, overlay_count, follow_index_range):
        self.threshold_factor = threshold_factor
        self.threshold_offset = threshold_offset
        self.overlay_count = overlay_count
        self.follow_index_range = follow_index_range
        config.set('sonar', 'threshold_factor',
                   format(threshold_factor, '.2f'))
        config.set('sonar', 'threshold_offset', str(threshold_offset))
        config.set('sonar', 'overlay_count', str(overlay_count))
        config.set('sonar', 'follow_index_range', str(follow_index_range))
        with open('config.ini', 'w') as f:
            config.write(f)

    def set_follow_index(self, follow_index):
        if follow_index < 0 or follow_index >= 96000:
            print("Sonar set_follow_index follow_index error. follow_index=%d" %
                  (follow_index))
            return

        self.follow_index = follow_index

    def set_read_step(self, read_step):
        if read_step <= 0:
            print("Sonar set_read_step read_step error. read_step=%.2f" %
                  (read_step))
            return

        if self.read_step > 0:
            print("Sonar set_read_step self.read_step error." %
                  (self.read_step))
            return

        self.read_step = read_step

    def set_save_wav_second(self, second):
        if second <= 0:
            print("Sonar set_save_wav_second second error. second=%d" % (second))
            return

        if self.save_wav_second > 0:
            print("Sonar set_read_step self.write_wav_second error. write_wav_second=%d" %
                  (self.save_wav_second))
            return

        self.save_wav_second = second


class Config:
    sn = Sn()
    plat_form = PLAT_FORM.PLATFORM_NONE
    tcp = Tcp()
    data = Data()
    robot = Robot()
    sonar = Sonar()

    def init(self):
        config.read("config.ini")

        self.sn.init()
        self.plat_form = get_plat_form(self.sn.sn)

        self.tcp.init()
        self.data.init()
        self.robot.init()
        self.sonar.init()

        return True


config = configparser.ConfigParser()  # 配置表
configIns = Config()  # 配置单例

