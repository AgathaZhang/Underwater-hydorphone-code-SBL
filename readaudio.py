import time
import wave
import numpy as np
import matplotlib.pyplot as plt
import numpy as np
import pynmea2
from datetime import datetime

from numpy.lib.function_base import append


def wav_show(wave_data, fs):  # 显示出来声音波形
    time = np.arange(0, len(wave_data)) * (1.0/fs)  # 计算声音的播放时间，单位为秒
    # 画声音波形
    plt.plot(time, wave_data)
    plt.show()


def normalization(data):
    '''归一化'''
    _range = np.max(abs(data))
    return data / _range


def check_need_setp(src_data):
    _min_step = 9600  # 0.05*192000
    _refer_step = 19200  # 0.1*192000
    _max_step = 48000  # 0.25*192000
    _chunk = 96000

    # 开始
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
    if first_negative_one_index < _min_step:
        print("i think need auto step min. first_negative_one_index=%d" %
              (first_negative_one_index))
        need_step = _chunk - \
            (_refer_step - first_negative_one_index)
        return need_step

    # 根据下降沿检测是否需要步进max
    if first_negative_one_index > _max_step:
        print("i think need auto step max. first_negative_one_index=%d" %
              (first_negative_one_index))
        need_step = first_negative_one_index - _refer_step
        return need_step

    # 找到第1个上升沿的index
    first_one_index = -1
    for i in range(len_data):
        temp = data[i]
        if temp > 0.5:
            first_one_index = i
            break

    # 根据上升沿检测是否需要步进min
    if first_one_index < _min_step:
        print("i think need auto step min. first_one_index=%d" %
              (first_one_index))
        need_step = _chunk - (_refer_step - first_one_index)
        return need_step

    # 根据上升沿检测是否需要步进max
    if first_one_index > _max_step:
        print("i think need auto step max. first_one_index=%d" %
              (first_one_index))
        need_step = first_negative_one_index - _refer_step
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


def parse_gps_data(src_data):
    _bit_width = 20

    # 开始
    bit_width = _bit_width  # 1个位的位宽

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


if(__name__ == '__main__'):
    wav = wave.open("acoust_data_20211103.wav", "rb")  # 打开一个wav格式的声音文件流
    num_frame = wav.getnframes()  # 获取帧数
    num_channel = wav.getnchannels()  # 获取声道数
    framerate = wav.getframerate()  # 获取帧速率

    num_sample_width = wav.getsampwidth()  # 获取实例的比特宽度，即每一帧的字节数
    str_data = wav.readframes(num_frame)  # 读取全部的帧

    wav.close()  # 关闭流

    wave_data = np.frombuffer(str_data, dtype='int16')  # 将声音文件数据转换为数组矩阵形式

    print("声道数: ", num_channel)
    print("帧数: ", num_frame)
    print("帧速率: ", framerate)
    print("str_data len: ", len(str_data))
    print("wave_data len: ", len(wave_data))

    wave_data.shape = -1, num_channel  # 按照声道数将数组整形，单声道时候是一列数组，双声道时候是两列的矩阵
    wave_data = wave_data.T  # 将矩阵转置
    wave_data = wave_data

    signal_length = len(wave_data[1])  # 信号总长度

    f = 96000  # 窗口
    bit_width = 20  # 位宽
    count = int(int(num_frame)/f)

    file_index = 0
    auto_step = 0
    times = 0
    auto_step_times = 0
    parse_gps_ok_times = 0
    parse_gps_failed_times = 0

    while True:
        times += 1
        print("----- ----- [start(%d)] ----- -----" % times)

        print("file_index=%d" % file_index)

        data_start_index = file_index  # 音频起点
        if auto_step > 0:
            print("auto step. auto_step=%d" % auto_step)
            data_end_index = data_start_index+auto_step  # 步进的音频终点

            # 是否已经读到结尾
            if data_end_index >= signal_length:
                print("end read. times=%d, data_end_index=%d, signal_length=%d" %
                      (times, data_end_index, signal_length))
                break

            auto_step = 0  # 步进清空
            file_index = data_end_index  # 文件位置变更
            continue

        data_end_index = data_start_index + f  # 音频终点

        # 是否已经读到结尾
        if data_end_index >= signal_length:
            print("end read. times=%d, data_end_index=%d, signal_length=%d" %
                  (times, data_end_index, signal_length))
            break

        file_index = data_end_index  # 文件位置变更

        data = wave_data[1][data_start_index:data_end_index]

        # 是否需要自动步进
        auto_step = check_need_setp(data)
        print("auto_step=%d" % auto_step)
        if auto_step > 0:
            auto_step_times += 1

        # 解析gps数据
        gps_time, ret = parse_gps_data(data)
        print("gps_time=%d, ret=%d" % (gps_time, ret))
        if ret == 0:
            parse_gps_ok_times += 1
        else:
            parse_gps_failed_times += 1

    print("----- ----- [result] ----- -----")
    print("times=%d, auto_step_times=%d, parse_gps_ok_times=%d,parse_gps_failed_times=%d" % (
        times, auto_step_times, parse_gps_ok_times, parse_gps_failed_times))
