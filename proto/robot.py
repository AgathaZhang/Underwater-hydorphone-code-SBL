# coding=utf-8
# robot.py
from enum import Enum

CMD_ROBOT_NONE = 1300000
CMD_ROBOT_END = 1400000

CMD_ROBOT = Enum('CMD_ROBOT', (
    "CMD_LOGIN_REQ",
    "CMD_LOGIN_RES",

    "CMD_POST_INFO_REQ",
    "CMD_POST_INFO_RES",

    "CMD_SET_CONFIG_REQ",
    "CMD_SET_CONFIG_RES",

    "CMD_POST_CONFIG_REQ",
    "CMD_POST_CONFIG_RES",
))


def get_robot_cmd(cmd):
    return CMD_ROBOT_NONE + cmd.value



