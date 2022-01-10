# coding=utf-8
import sys
import time
from tcp import tcpIns
from data import dataIns
from config import configIns


def main():
    version = "1.2.1"

    if False:
        log_file = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime()) + '.log'
        sys.stdout = open(log_file, mode='w', encoding='utf-8')

    print("Neptune pi start. version=%s" % (version))

    # 配置模块
    if not configIns.init():
        print("main configIns init error.")
        exit(1)

    # tcp模块
    if not tcpIns.init(configIns.tcp.ip, configIns.tcp.port):
        print("main tcpIns init error.")
        exit(1)

    # 数据模块
    if not dataIns.init():
        print("main dataIns init error.")
        exit(1)

    return


if __name__ == "__main__":
    main()

