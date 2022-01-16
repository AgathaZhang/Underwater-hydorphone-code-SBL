# class Temp:
#     _ppt = 1
#     def _run(self):
#         while True:
#             if not self._connect():
#                 print("第一层")
#                 if not self._connect():
#                     print("第二层 sleep")
#             else:
#                 print("enter else")
#
#     def _connect(self):
#             if _ppt == 1:
#                 return False
#
#     _ppt = 2
#         return True
# A = Temp
# A._run()
#
#
# print("stop")


# if __name__ == '__main__':print('水下节点仿真')
#
#
# def main():
#     _sonar = Sonar()        # Sonar实例化
#     # if configIns.data.sonar:
#     #     if not self._sonar.init():
#     #         return False
#
# main()
#
#
# class Sonar:
#     def __init__(self):
#         print("class sonar")
# def f1():
#
# f1()
#
# def f1():
#   print('good')


# import wave
# import numpy as np
# import pylab as plt
#
# #打开wav文件 ，open返回一个的是一个Wave_read类的实例，通过调用它的方法读取WAV文件的格式和数据。
# f = wave.open(r"acoust_data_20211103.wav","rb")
# #读取格式信息
# #一次性返回所有的WAV文件的格式信息，它返回的是一个组元(tuple)：声道数, 量化位数（byte单位）, 采
# #样频率, 采样点数, 压缩类型, 压缩类型的描述。wave模块只支持非压缩的数据，因此可以忽略最后两个信息
# params = f.getparams()
# nchannels, sampwidth, framerate, nframes = params[:4]
# #读取波形数据
# #读取声音数据，传递一个参数指定需要读取的长度（以取样点为单位）
# str_data  = f.readframes(nframes)
# f.close()
# #将波形数据转换成数组
# #需要根据声道数和量化单位，将读取的二进制数据转换为一个可以计算的数组
# wave_data = np.fromstring(str_data,dtype = np.short)
# #将wave_data数组改为2列，行数自动匹配。在修改shape的属性时，需使得数组的总长度不变。
# wave_data.shape = -1,2
# #转置数据
# wave_data = wave_data.T
# #通过取样点数和取样频率计算出每个取样的时间。
# time=np.arange(0,nframes)/framerate
# #print(params)
# plt.figure(1)
# plt.subplot(2,1,1)
# #time 也是一个数组，与wave_data[0]或wave_data[1]配对形成系列点坐标
# plt.plot(time,wave_data[0])
# plt.subplot(2,1,2)
# plt.plot(time,wave_data[1],c="r")
# plt.xlabel("time")
# plt.show()
#
#
# # ----------------------------------------------------------------------------------
#
# f = wave.open(r"acoust_data_20211103.wav", "rb")
# params = f.getparams()
# nchannels, sampwidth, framerate, nframes = params[:4]
# channel = f.getnchannels()  # 通道数
# sampwidth = f.getsampwidth()  # 比特宽度 每一帧的字节数
# framerate = f.getframerate()  # 帧率  每秒有多少帧
# frames = f.getnframes()  # 帧数
# duration = frames / framerate  # 音频持续时间 单位：秒
# audio = f.readframes(frames)  # 按帧读音频，返回二进制数据
#
# # i = 0
# # # for i in range(0, nframes/framerate):
# str_data = f.readframes(nframes)  # 读取声音数据，传递一个参数指定需要读取的长度（以取样点为单位）
# # str_data = f.readframes(192000)
# f.close()
#
# wave_data = np.fromstring(str_data, dtype=np.short)
#
#     wave_data.shape = -1, 2
#
#     wave_data = wave_data.T
#
#     time = np.arange(0, nframes) / framerate
#
#     plt.figure(1)
#     plt.subplot(2, 1, 1)
#
#     plt.plot(time, wave_data[0])
#     plt.subplot(2, 1, 2)
#     plt.plot(time, wave_data[1], c="r")
#     plt.xlabel("time")
#     plt.show()
#     print("打开音频")
# ----------------------------------------------------------------------------------
# def main(): #程序的主干
#     function1()
#     function2()
#
# def function1():
#     print('good')
#
# def function2():
#     print('good')
#
#
# main()
import queue
# 存储数据时可设置优先级的队列
# 优先级设置数越小等级越高
pq = PriorityQueue(maxsize=0)

#写入队列，设置优先级
pq.put((9,'a'))
pq.put((7,'c'))
pq.put((1,'d'))

#输出队例全部数据
print(pq.queue)

#取队例数据，可以看到，是按优先级取的。
pq.get()
pq.get()
print(pq.queue)#输出：[(9, 'a')]
print('stop')
