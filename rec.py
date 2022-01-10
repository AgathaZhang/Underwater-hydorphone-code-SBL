import matplotlib
import time
import pyaudio
import struct
import numpy as np
import tkinter
import matplotlib.pyplot as plt
from scipy.fftpack import fft


def FFT(Fs, data):
    L = len(data)
    N = np.power(2, np.ceil(np.log2(L)))
    FFT_y1 = np.abs(fft(data, int(N)))/L*2
    Fre = np.arange(int(N/2))*Fs/N
    FFT_y1 = FFT_y1[range(int(N/2))]
    return Fre, FFT_y1


FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 192000
CHUNK = int(RATE/2)

p = pyaudio.PyAudio()
stream_in = p.open(
    format=FORMAT,
    channels=CHANNELS,
    rate=RATE,
    input=True,
    frames_per_buffer=CHUNK
)

print(matplotlib.get_backend())

# plt.switch_backend('agg')
fig, ax = plt.subplots(2, 1)

t = np.arange(0, CHUNK, 1)
line, = ax[0].plot(t, np.random.rand(CHUNK))
freq, = ax[1].plot(t, np.random.rand(CHUNK))

plt.show(block=False)
plt.grid()

ax[0].set_xlim(0, CHUNK)
ax[0].set_ylim(-1000, 1000)

ax[1].set_ylim(0, 150)
ax[1].set_xlim(0, RATE)

while True:
    data = stream_in.read(CHUNK)
#    print(time.time()-tstart)
    tstart = time.time()
    data_int = struct.unpack(str(CHUNK)+'h', data)

    line.set_ydata(data_int)

    # fft
    fx, fy = FFT(RATE, data_int)
    freq.set_xdata(fx)
    freq.set_ydata(fy)

    fig.canvas.draw()
    fig.canvas.flush_events()

    print("%.6f" % (time.time()-tstart))

