# coding=utf-8
# sonar.py
import numpy as np
import time
from tkinter import *
from scipy.fftpack import hilbert, fft, ifft
from scipy import signal
import matplotlib.pyplot as plt
import pyaudio
import threading
import queue
import struct
import wave
from ctypes import *
from tcp import tcpIns
from array import array
from proto.sonar import CMD_SONAR, get_sonar_cmd
from config import configIns
import pynmea2
from datetime import datetime


def normalization(data):
    '''归一化'''
    _range = np.max(abs(data))
    return data / _range


class SonarData(object):
    send_times = 0  # 发送次数（针对LORA，查看掉包率）
    auto_step_times = 0  # 自动步进次数
    gps_parse_failed_times = 0  # gps数据解析失败次数

    times = 0  # 读取次数

    def __init__(self, send_times=0, times=0):
        self.send_times = send_times
        self.times = times

    def pack(self):
        return struct.pack('<3i', self.send_times, self.auto_step_times, self.gps_parse_failed_times)


class Sonar:
    def __init__(self):
        print('this is Father class Sonar')
    # 基本属性
    _data = SonarData()
    _pyaudio = None  # 音频设备
    _pyaudio_ok = False  # 音频设备是否就绪
    _device_id = 1  # 音频设备ID
    _stream = None  # 音频流
    _channel = 0  # 声道数
    _rate = 0  # 采样率
    _chunk = 0  # 音频流缓冲区大小
    _format = pyaudio.paInt16  # 数据格式 16bit 32bit
    _times_pre_second = 0  # 每秒标识信号出现次数
    _overlay_max_count = 100  # 叠加历史次数
    _bp_b = 0  # 带通左边
    _bp_a = 0  # 带通右边
    _threads = []  # 线程池
    _draw_plt = False  # 是否画图
    _draw_channel = 0  # 画图的声道
    _channel_data_queue = []  # 声道数据队列
    _channel_res_queue = queue.Queue(maxsize=1024)  # 声道数据计算结果队列
    _frames = []  # 保存音频文件缓冲流
    _auto_step_chunk = 0  # 自动步进
    _bit_width = 20  # GPS数据的位宽
    _min_step = 9600  # 0.05*192000
    _refer_step = 19200  # 0.1*192000
    _max_step = 48000  # 0.25*192000
    _auto_step_times = 0  # 自动步进次数
    _parse_gps_ok_times = 0  # gps解析成功次数
    _parse_gps_failed_times = 0  # gps解析失败次数

    # 初始化函数
    '''由data init调用:'''
    def init(self,  channel=2, rate=192000, format=pyaudio.paInt16, times_pre_second=2, ):
        self._channel = channel                         # 声道数
        self._rate = rate                               # 采样率
        self._format = format                           # 数据格式 16bit
        self._chunk = int(rate / times_pre_second)      # 音频流缓冲区大小
        self._times_pre_second = times_pre_second       # 每秒标识信号出现次数


        # 带通滤波器参数  // 192khz 34khz-36khz  // WN = fc1 / fa; (fa = fs / 2)
        _bp_hz = 35000  # 特征信号频率 khz
        _bp_low = (_bp_hz - 1000) / (self._rate / 2)
        _bp_up = (_bp_hz + 1000) / (self._rate / 2)
        _bp_b, _bp_a = signal.butter(8, [_bp_low, _bp_up], 'bandpass')      # 返回滤波器分子分母形式 分子b 分母a
        self._bp_b = _bp_b
        self._bp_a = _bp_a

        # 创建队列和线程，队列和线程的数量和声道数有关
        for i in range(self._channel):                      # 有两通道，所以有两线程
            _q = queue.Queue(maxsize=1024)                  # 创建私有队列
            self._channel_data_queue.append(_q)             # _channel_data_queue = []  # 声道数据队列已经初始化

            t = threading.Thread(
                target=self._handle_data, name="sonar_audio_"+str(i),
                args=(i, ))                                 # 实例化线程                                                     question 这里的args=(i,)含义
            t.start()
            self._threads.append(t)                         # _threads = []  # 线程池

        # 打开音频设备
        '''这里是Linux硬件声卡的调度 包含于Sonar.init()当中'''
        self._pyaudio = pyaudio.PyAudio()
        info = self._pyaudio.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        for i in range(0, numdevices):
            device_index = self._pyaudio.get_device_info_by_host_api_device_index(
                0, i)
            if (device_index.get('maxInputChannels')) > 0:
                device_name = device_index.get('name')
                if "seeed-4mic-voicecard" in device_name:
                    self._device_id = i
                    break

        # 启动声纳run线程
        _sonar_run_thread = threading.Thread(
            target=self._run, name="sonar_run", args=())
        _sonar_run_thread.start()

        # 启动声纳计算距离线程
        _sonar_run_calc_thread = threading.Thread(
            target=self._run_calc, name="sonar_run_calc", args=())
        _sonar_run_calc_thread.start()

        return True

    def _run(self):
        while True:
            if not self._pyaudio_ok:            # init False
                if not self._connect():         # 执行_connect() 并return ture
                    time.sleep(5)               # 线程等待5s
            else:
                self._read()                    # _connect成功了 就执行read

    def _run_calc(self):
        _unwork_datas = {}                   #含义
        _pre_point_time = 1 / self._rate     #含义
        _voice_speed = 1500  # 海水中的音速
        dis_filter_count = 10                #含义
        follow_dis_list = np.zeros((dis_filter_count), dtype=np.int32)  # 跟随的距离
        follow_dis_list_index = 0

        while True:
            # 从队列中获取音频数据，阻塞操作
            _res = self._channel_res_queue.get(1)           # 一直阻塞 等同于 (block=True, timeout=None)

            # 获取声纳水听器数据
            _channel_id, _data_id, _val_index, _val, _follow_val_index, _follow_val, _gps_time = _res.get_info()

            # 计算距离
            # 整合所有声道数据
            if _data_id not in _unwork_datas:
                _unwork_datas[_data_id] = [Result(), Result()]        # 这里要明确含义

            # 存储
            _data_id_datas = _unwork_datas[_data_id]
            _data_id_datas[_channel_id] = _res

            # 检测是否满足计算距离条件
            b = True
            for d in _data_id_datas:
                _channel_id, _data_id, _val_index, _val, _follow_val_index, _follow_val, _gps_time = d.get_info()
                if _data_id == 0 and _val_index == 0 and _val == 0:
                    b = False
                    break

            # 满足计算需求
            if b == True:
                # todo 写死1声道是换能器，2声道是GPS数据
                # 1声道(换能器)数据
                _, _, _val_index_1, _val_1, _follow_val_index_1, _follow_val_1, _ = _data_id_datas[0].get_info(
                )
                # 2声道(GPS)数据
                _, _, _val_index_2, _val_2, _, _, _gps_time = _data_id_datas[1].get_info(
                )

                _dis = (_val_index_1 - _val_index_2) * \
                    _pre_point_time * _voice_speed  # 1声道计算距离

                _follow_dis = 0
                if _follow_val_index_1 != 0 and _follow_val != 0:
                    _follow_dis = (_follow_val_index_1 - _val_index_2) * \
                        _pre_point_time * _voice_speed  # 1声道计算跟随距离

                val_index_1 = np.uint16(_val_index_1)
                _follow_val_index_1 = np.uint16(_follow_val_index_1)
                val_index_2 = np.uint16(_val_index_2)
                val_1 = np.int32(_val_1)
                _follow_val_1 = np.int32(_follow_val_1)
                val_2 = np.int32(_val_2)
                dis = np.int32(_dis * 100)
                follow_dis = np.int32(_follow_dis * 100)

                # 距离滤波
                follow_dis_list[follow_dis_list_index] = follow_dis
                tmp = follow_dis_list.copy()
                tmp.sort()
                sum = 0
                for i in range(len(tmp)):
                    if i == 0 or i == dis_filter_count - 1:
                        continue
                    sum += tmp[i]
                average_dis = np.int32(sum / (dis_filter_count-2))

                follow_dis_list_index += 1
                if follow_dis_list_index >= dis_filter_count:
                    follow_dis_list_index = 0

                _body = struct.pack('<3H6iq', val_index_1, _follow_val_index_1,
                                    val_index_2, val_1, _follow_val_1, val_2, dis, follow_dis, average_dis, _gps_time)

                # todo 因为是LORA，send有可能会阻塞，要把send做成队列比较好
                tcpIns.send(CMD_SONAR.CMD_POST_INFO_LORA_REQ, _body)
                self._data.send_times += 1

                # print("[DISTANCE] time=%.2f, val_index_1=%d, val_index_2=%d, val_1=%d, val_2=%d, dis=%d[%.2f], follow_dis=%d" %
                #       (time.time(), val_index_1, val_index_2, val_1, val_2, dis, _dis, follow_dis))

    def _connect(self):
        try:
            self._stream = self._pyaudio.open(
                format=self._format,
                channels=self._channel,
                rate=self._rate,
                frames_per_buffer=self._chunk,
                input=True,
                input_device_index=self._device_id,)
        except Exception as e:                  # 错误类型抛给别名e 打印出来
            print("Sonar _connect open error. err=%s, channel=%d" %
                  (str(e), self._channel))

            return False        # 两个return同为一个吗

        self._pyaudio_ok = True     # 这里设备只检验一次 是否有问题
        return True     # 两个return同为一个吗

    def _read(self):
        _times = 0
        _channel_byte_count = self._chunk * 2
        _all_channel_byte_count = _channel_byte_count * self._channel

        plt.ion()  # 开启一个画图的窗口
        _st = time.time()
        while True:
            try:
                # 读音频流是否要步进
                if configIns.sonar.read_step > 0:
                    _chunk = int(self._chunk * configIns.sonar.read_step)
                    print("[Sonar Step] time=%.2f read_step=%.2f, chunk=%d" %
                          (time.time(), configIns.sonar.read_step, _chunk))
                    _data = self._stream.read(
                        _chunk, exception_on_overflow=False)
                    configIns.sonar.read_step = 0
                    # 写文件
                    if configIns.sonar.save_wav_second > 0:
                        self._frames.append(_data)
                        configIns.sonar.save_wav_second -= 1
                        if configIns.sonar.save_wav_second == 0:
                            # 启动声纳run线程
                            _sonar_write_wav_file_thread = threading.Thread(
                                target=self._write_wav_file, name="sonar_write_wav_file", args=())
                            _sonar_write_wav_file_thread.start()

                # 读音频流自动步进
                if self._auto_step_chunk > 0:
                    self._data.auto_step_times += 1
                    _chunk = int(self._auto_step_chunk)
                    print("read auto step. chunk=%d" % (_chunk))
                    _data = self._stream.read(
                        _chunk, exception_on_overflow=False)
                    self._auto_step_chunk = 0
                    # 写文件
                    if configIns.sonar.save_wav_second > 0:
                        self._frames.append(_data)
                        configIns.sonar.save_wav_second -= 1
                        if configIns.sonar.save_wav_second == 0:
                            # 启动声纳run线程
                            _sonar_write_wav_file_thread = threading.Thread(
                                target=self._write_wav_file, name="sonar_write_wav_file", args=())
                            _sonar_write_wav_file_thread.start()

                # 读取设备音频流
                _data = self._stream.read(
                    self._chunk, exception_on_overflow=False)

                # 长度校验
                _data_len = len(_data)
                if _data_len != _all_channel_byte_count:
                    print("Sonar run read error. data_len=%d, byte_count=%d" %
                          (_data_len, _all_channel_byte_count))

                # 计数+1
                _times += 1

                # 过滤起始的音频(有干扰)
                if _times < 10:
                    continue

                # 解析数据
                _src_data = np.zeros(self._chunk, dtype=np.int16)
                _np_data = np.array(_data)
                _tmp_np_data_file_name = 'tmp_np_data.dat'
                with open(_tmp_np_data_file_name, 'wb+') as fs:
                    _np_data.tofile(_tmp_np_data_file_name)
                    _src_data = np.fromfile(
                        _tmp_np_data_file_name, dtype=np.int16)

                #  画图
                if False:
                    plt.clf()
                    plt.subplot(211)
                    plt.plot(_src_data[0::self._channel])
                    plt.subplot(212)
                    plt.plot(_src_data[1::self._channel])
                    plt.pause(0.01)
                    plt.ioff()
                    continue

                # 写文件
                if configIns.sonar.save_wav_second > 0:
                    self._frames.append(_data)
                    configIns.sonar.save_wav_second -= 1
                    if configIns.sonar.save_wav_second == 0:
                        # 启动声纳run线程
                        _sonar_write_wav_file_thread = threading.Thread(
                            target=self._write_wav_file, name="sonar_write_wav_file", args=())
                        _sonar_write_wav_file_thread.start()

                # 双声道数据
                channel_data_1 = _src_data[0::2]  # 声道1 水听器
                channel_data_2 = _src_data[1::2]  # 声道2 GPS

                # 检测是否需要步进
                step = self._check_need_setp(channel_data_2)
                if step != 0:
                    print("need step. step=%d" % (step))
                    if step > 0:
                        self._auto_step_chunk = step

                    # 如果需要步进，不要再往下走
                    continue

                # 丢进处理线程
                for i in range(self._channel):
                    self._channel_data_queue[i].put(
                        _src_data[i::self._channel])
            except Exception as e:
                self._pyaudio_ok = False
                print("Sonar _read error. err=%s" % (str(e)))
                break

    def _handle_data(self, index):
        _times = 0  # 统计次数
        hil_data_list = np.zeros(
            (self._overlay_max_count, self._chunk), dtype=float)  # 最近的包络数据

        val_index_list = np.zeros(
            (self._overlay_max_count, self._chunk), dtype=np.int32)  # 最近的val_index
        val_list = np.zeros(
            (self._overlay_max_count, self._chunk), dtype=np.int32)  # 最近的val
        list_index = 0

        follow_val_index_list = np.zeros(
            (self._overlay_max_count, self._chunk), dtype=np.int32)  # 最近跟随的val_index
        follow_val_list = np.zeros(
            (self._overlay_max_count, self._chunk), dtype=np.int32)  # 最近跟随的val
        follow_list_index = 0
        tmp_follow_index = -1
        last_follow_index = -1

        # 上次定位到的gps时间
        last_gps_time = 0  # 上次定位到的gps时间
        last_gps_time_times = 0  # 上次定位到时的dataid

        # 实时画图
        if self._draw_plt and index == self._draw_channel:
            # plt.ion()  # 开启一个画图的窗口

            fig, ax = plt.subplots(2, 1)
            t = np.arange(0, int(self._chunk/32), 1)
            line, = ax[0].plot(t, np.random.rand(int(self._chunk/32)))
            freq, = ax[1].plot(t, np.random.rand(int(self._chunk/32)))

            plt.show(block=False)
            # plt.grid()

            ax[0].set_xlim(0, int(self._chunk/32))
            ax[0].set_ylim(-1000, 1000)

            ax[1].set_xlim(0, int(self._chunk/32))
            ax[1].set_ylim(-1000, 1000)

        while True:
            # 叠加次数
            _overlay_count = configIns.sonar.overlay_count

            # 从队列中获取音频数据，阻塞操作
            src_data = self._channel_data_queue[index].get(1)

            # 记录开始时间
            _st = time.time()

            # 叠加数据
            overlay_data = np.zeros(self._chunk)

            _val = -1
            _val_index = -1
            _follow_val = -1
            _follow_val_index = -1
            _gps_time = 0
            if index == 1:
                # GPS
                # 解析出时间信息
                print("------ ----- ----- -----")
                try:
                    _gps_time, ret = self._parse_gps_data(src_data)
                    if ret != 0:
                        self._data.gps_parse_failed_times += 1
                        if last_gps_time != 0 and last_gps_time_times != 0:
                            n = _times - last_gps_time_times
                            _gps_time = last_gps_time + n * 500
                            print("use gpstime auto-increment.")
                    else:
                        last_gps_time = _gps_time
                        last_gps_time_times = _times
                    print("gps_time=%d, ret=%s(%d)" %
                          (_gps_time, ret == 0, ret))
                except:
                    print("gps_time=%d, ret=%s(%d)" % (-999))
                print("-----> GPSTIME=%d" % _gps_time)

                    

                # 存储原始数据
                hil_data_list[list_index] = src_data

                # 叠加
                for i in range(_overlay_count):
                    overlay_data += hil_data_list[i]

                # 计算捕获特征信号的位置
                _val_index = np.argmin(overlay_data)
                _val = overlay_data[_val_index]
            else:
                # 水听器
                # 带通
                bp_data = signal.filtfilt(self._bp_b, self._bp_a, src_data)

                # 包络
                hil_bp_data = hilbert(bp_data)
                uphil_bp_data = np.sqrt(bp_data**2 + hil_bp_data**2)

                # 存储包络数据
                hil_data_list[list_index] = uphil_bp_data

                # 叠加
                for i in range(_overlay_count):
                    overlay_data += hil_data_list[i]

                # 计算捕获特征信号的位置
                _val_index = np.argmax(overlay_data)
                _val = overlay_data[_val_index]

                # 计算捕获特征信号的位置（跟随算法）
                follow_index = configIns.sonar.follow_index
                if follow_index > 0 and follow_index <= 96000:
                    if last_follow_index != follow_index:
                        tmp_follow_index = -1
                    if tmp_follow_index == -1:
                        tmp_follow_index = follow_index
                    follow_index_range = configIns.sonar.follow_index_range
                    startIndex = tmp_follow_index - (follow_index_range / 2)
                    if startIndex < 0:
                        startIndex = 0
                    endIndex = tmp_follow_index + (follow_index_range / 2)
                    if endIndex > 96000:
                        endIndex = 96000
                    follow_overlay_data = overlay_data[int(
                        startIndex): int(endIndex)]
                    _follow_val_index = np.argmax(
                        follow_overlay_data) + startIndex
                    _follow_val = overlay_data[int(_follow_val_index)]

                    tmp_follow_index = _follow_val_index
                    last_follow_index = follow_index
                else:
                    _follow_val_index = 0
                    _follow_val = 0
                    tmp_follow_index = -1
                    last_follow_index = -1

                # 加阈值
                if configIns.sonar.threshold_offset != 0 and configIns.sonar.threshold_factor != 0:
                    _threshold = _val * configIns.sonar.threshold_factor  # 阈值
                    _threshold_start = _val_index - configIns.sonar.threshold_offset  # 待过滤的阈值区域
                    if configIns.sonar.threshold_offset > _val_index:  # 超出当前秒数时,默认取0
                        _threshold_start = 0

                    _temp_index = _threshold_start
                    while _temp_index < _val_index:
                        if overlay_data[_temp_index] > _threshold:
                            _val_index = _temp_index
                            _val = overlay_data[_temp_index]
                            break
                        _temp_index += 1

            # 存储历史数据
            val_list[list_index] = _val
            val_index_list[list_index] = _val_index
            # index+1
            list_index += 1
            if list_index >= _overlay_count:
                list_index = 0

            # 存储历史跟随数据
            follow_val_list[follow_list_index] = _follow_val
            follow_val_index_list[follow_list_index] = _follow_val_index
            # follow_list_index+1
            follow_list_index += 1
            if follow_list_index >= _overlay_count:
                follow_list_index = 0

            # 计算结果丢进队列
            res = Result(index, _times, _val_index, _val,
                         _follow_val, _follow_val_index, _gps_time)
            self._channel_res_queue.put(res)

            if False:
                print("[VOICE] time=%.2f, channel=%d, val_index=%d, val=%.4f, overlay_count=%d" % (
                    time.time(), index, _val_index, _val, _overlay_count))

            # 次数+1
            _times += 1

            # 实时画图
            if self._draw_plt and index == self._draw_channel:
                # print("val_index=%d, val=%.2f" % (_val_index, _val))
                print("overlay_data.", len(overlay_data),
                      overlay_data[::19200])

                # 计算时间轴
                data_time = np.arange(0, self._chunk) * (
                    (1 / self._times_pre_second)/self._chunk) + (_times / self._times_pre_second)
                # line.set_xdata(data_time)
                line.set_ydata(src_data[::32])

                # freq.set_xdata(data_time)
                freq.set_ydata(overlay_data[::32])

                fig.canvas.draw()
                fig.canvas.flush_events()

    def _check_need_setp(self, src_data):
        data = normalization(src_data)  # 归一化

        len_data = len(data)

        # 找到第1个下降沿的index
        first_negative_one_index = -1
        for i in range(len_data):
            temp = data[i]
            if temp < -0.5:
                first_negative_one_index = i
                break

        # 根据下降沿检测是否需要步进min
        if first_negative_one_index < self._min_step:
            print("i think need auto step min. first_negative_one_index=%d" %
                  (first_negative_one_index))
            need_step = self._chunk - \
                (self._refer_step - first_negative_one_index)
            return need_step

        # 根据下降沿检测是否需要步进max
        if first_negative_one_index > self._max_step:
            print("i think need auto step max. first_negative_one_index=%d" %
                  (first_negative_one_index))
            need_step = first_negative_one_index - self._refer_step
            return need_step

        # 找到第1个上升沿的index
        first_one_index = -1
        for i in range(len_data):
            temp = data[i]
            if temp > 0.5:
                first_one_index = i
                break

        # 根据上升沿检测是否需要步进min
        if first_one_index < self._min_step:
            print("i think need auto step min. first_one_index=%d" %
                  (first_one_index))
            need_step = self._chunk - (self._refer_step - first_one_index)
            return need_step

        # 根据上升沿检测是否需要步进max
        if first_one_index > self._max_step:
            print("i think need auto step max. first_one_index=%d" %
                  (first_one_index))
            need_step = first_negative_one_index - self._refer_step
            return need_step

        # 下降沿和上升沿之间的位宽
        first_bit_width = first_one_index-first_negative_one_index

        # 是否已定位
        is_location = True
        if first_bit_width < 1900:
            is_location = False

        # 未定位，步进0.5s
        # todo 步进长度是不是可以优化一下
        if not is_location:
            print("i think need auto step no location. first_bit_width=%d, first_one_index=%d, first_negative_one_index=%d" % (
                first_bit_width, first_one_index, first_negative_one_index))
            return 48000

        return 0

    def _parse_gps_data(self, src_data):
        bit_width = self._bit_width  # 1个位的位宽

        data = normalization(src_data)  # 归一化

        len_data = len(data)

        # 找到第1个下降沿的index
        first_negative_one_index = -1
        for i in range(len_data):
            temp = data[i]
            if temp < -0.5:
                first_negative_one_index = i
                break

        # 找到第1个上升沿的index
        first_one_index = -1
        for i in range(len_data):
            temp = data[i]
            if temp > 0.5:
                first_one_index = i
                break

        # 下降沿和上升沿之间的位宽
        first_bit_width = first_one_index-first_negative_one_index

        # 是否已定位
        is_location = True
        if first_bit_width < 1900:
            is_location = False

        print("first_negative_one_index=%d, first_one_index=%d, first_bit_width=%d, is_location=%s" %
              (first_negative_one_index, first_one_index, first_bit_width, is_location))

        if not is_location:
            return 0, -2

        # 正序寻找第一个遇到的最小值（因为起点从-1开始）
        start_add = first_one_index+10000
        temp_index = start_add
        min_index = -1
        while temp_index < 96000:
            if data[temp_index] < -0.5:
                min_index = temp_index
                break
            temp_index += 1
        min_val = data[min_index]
        print("min_index=%d, min_val=%d" % (min_index, min_val))

        # 增强刚开始时的信号强度
        temp_index = min_index
        end_index = min_index + \
            (bit_width * 10 * 10)  # 往后数10个byte进行信号增强
        if end_index > 96000:
            end_index = 96000
        while temp_index < end_index:
            if data[temp_index] > 0:
                data[temp_index] = 1
            temp_index += 1

        # 过滤数据，只剩下-1,0,1
        data[data >= 0.2] = 1
        data[(data < 0.2) & (data > -0.2)] = 0
        data[data <= -0.2] = -1

        # 倒序寻找第一个遇到的最大值（因为终点从1结束）
        f_data = data[::-1]  # 倒序
        max_index = np.argmax(f_data)
        max_val = f_data[max_index]
        # 找到起点位置和终点位置
        start_index = min_index - 1
        # end_index = f - max_index - 1
        end_index = start_index + 680*bit_width

        # 截取有效信号区间
        temp_data = data[start_index: end_index+1]
        temp = -1  # 从低电平开始
        last_index = 0
        result = []
        temp_num_str = ""
        for j in range(len(temp_data)):
            val = temp_data[j]
            # todo 为什么如果头只要解析到下降沿(幅值为-1,bit为1)，就会在前面缺少了3个bit(000)
            if j == 0:
                if val == -1:
                    result.append("000")
            # 解析成二进制信号
            if val != 0 and val != temp:
                if last_index != 0:
                    count = 0
                    if val == 1:
                        temp_num_str = "0"
                    elif val == -1:
                        temp_num_str = "1"

                    temp_bit_width = j-last_index

                    count = round(temp_bit_width / bit_width, 0)
                    for k in range(int(count)):
                        result.append(temp_num_str)

                last_index = j
            temp = val

        result.append("1")
        result_str = ''.join(i for i in result)
        print("val_len=%d, start_index=%d, end_index=%d" %
              (len(result_str), start_index, end_index))
        # print("val=%s" % (result_str))

        # 二进制字符串->二进制->字符->字符串
        val = ""
        len_result_str = len(result_str)
        for j in range(len_result_str):
            if j % 10 == 0:
                if j + 10 > len_result_str:
                    print("the result str end, not found LF. j=%d, val=%s" % (j, val))
                    return 0, -3
                temp_str = result_str[j:j+10]
                inverted_temp_str = temp_str[::-1]
                binary_str = inverted_temp_str[1:9]
                s = chr(int(binary_str, 2))
                val += s
                if s == "\n":
                    print("stop find val. out_index=%d" % (j))
                    break

        len_val = len(val)

        # 检验
        temp_index = 2
        calc_crc = ord(val[1])
        while val[temp_index] != '*':
            calc_crc ^= ord(val[temp_index])
            temp_index += 1
            if temp_index >= len_val:
                print("val not found *.")
                return 0, -4

        try:
            real_crc = int(val[-4:-2], 16)
        except ValueError:
            print("get real_crc ValueError. val=%s" % (val))
            return 0, -4
        except:
            print("get real_crc error. val=%s" % (val))
            return 0, -4

        print("gpsData(%d)=%s[%X], real_crc=%X" %
              (len(val), val[:-2], calc_crc, real_crc))

        if real_crc != calc_crc:
            print("real_crc != calc_crc.")
            return 0, -5

        if not val.startswith('$GPRMC'):
            print("start is not $GPRMC.")
            return 0, -6

        # 解析GPS时间数据
        rmc = pynmea2.parse(val)
        print(rmc.data)

        # 解析GPS数据中的时间信息
        hhmmss = rmc.data[0]
        hour = hhmmss[0:2]
        min = hhmmss[2:4]
        sec = hhmmss[4:6]
        ms = hhmmss[7:9]
        ddmmyy = rmc.data[8]
        day = ddmmyy[0:2]
        mounth = ddmmyy[2:4]
        year = "20"+ddmmyy[4:6]

        # 转为时间数组
        time_str = year+"-"+mounth+"-"+day + " "+hour+":"+min+":"+sec + "."+ms
        time_array = datetime.strptime(
            time_str, "%Y-%m-%d %H:%M:%S.%f")
        time_stamp = int(time.mktime(time_array.timetuple())
                         * 1000.0 + time_array.microsecond / 1000.0)
        print("time=%s[%d]" % (time_str, time_stamp))

        return time_stamp, 0

    def _write_wav_file(self):
        wf = wave.open(time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime())+".wav", 'wb')
        wf.setnchannels(self._channel)
        wf.setsampwidth(
            self._pyaudio.get_sample_size(self._format))
        wf.setframerate(self._rate)
        wf.writeframes(b''.join(self._frames))
        wf.close()

        self._frames = []
        print("Sonar _write_wav_file ok.")

    def get(self):
        return self._data


def FFT(Fs, data):
    L = len(data)
    N = np.power(2, np.ceil(np.log2(L)))
    FFT_y1 = np.abs(fft(data, int(N)))/L*2
    Fre = np.arange(int(N/2))*Fs/N
    FFT_y1 = FFT_y1[range(int(N/2))]
    return Fre, FFT_y1


class Result(object):
    _channel_id = 0
    _data_id = 0
    _val_index = 0
    _val = 0
    _follow_val = 0
    _follow_val_index = 0
    _gps_time = 0

    def __init__(self, id=0, data_id=0, val_index=0, val=0, _follow_val=0, _follow_val_index=0, _gps_time=0):
        self._channel_id = id
        self._data_id = data_id
        self._val_index = val_index
        self._val = val
        self._follow_val = _follow_val
        self._follow_val_index = _follow_val_index
        self._gps_time = _gps_time

    def get_info(self):
        return self._channel_id, self._data_id, self._val_index, self._val, self._follow_val_index, self._follow_val, self._gps_time

