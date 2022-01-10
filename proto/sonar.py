# coding=utf-8
# sonar.py
from enum import Enum

CMD_SONAR_NONE = 1200000
CMD_SONAR_END = 1300000

CMD_SONAR = Enum('CMD_SONAR', (
    "CMD_READY_LOGIN_REQ",  # 准备登录请求
    "CMD_READY_LOGIN_RES",  # 准备登录回复

    "CMD_LOGIN_REQ",  # 登录请求
    "CMD_LOGIN_RES",  # 登录回复

    "CMD_POST_INFO_REQ",  # 上报信息请求
    "CMD_POST_INFO_RES",  # 上报信息回复 - 不使用

    "CMD_SET_CONFIG_REQ",  # 设置配置回复 - 不使用
    "CMD_SET_CONFIG_RES",  # 设置配置请求

    "CMD_POST_CONFIG_REQ",  # 上报配置请求
    "CMD_POST_CONFIG_RES",  # 上报配置回复 - 不使用

    "CMD_POST_SONAR_INFO_REQ",  # 上报声纳信息
    "CMD_POST_SONAR_INFO_RES",  # 回复声纳信息 - 不使用

    "CMD_POST_DISTANCE_INFO_REQ",  # 上报距离信息
    "CMD_POST_DISTANCE_INFO_RES",  # 回复距离信息 - 不使用

    "CMD_POST_READ_STEP_REQ",  # 读取音频步进回复 - 不使用
    "CMD_POST_READ_STEP_RES",  # 读取音频步进请求

    "CMD_POST_SAVE_WAV_REQ",  # 录音回复 - 不使用
    "CMD_POST_SAVE_WAV_RES",  # 录音请求

    "CMD_POST_INFO_LORA_REQ",  # 上报信息请求（LORA版本）
    "CMD_POST_INFO_LOAR_RES",  # 上报信息请求（LORA版本） - 不使用

    "CMD_GET_INFO_LORA_REQ", # 上报信息（LORA版本）
	"CMD_GET_INFO_LOAR_RES", # 获取信息（LORA版本）

    "CMD_POST_FOLLOW_REQ",  # 跟随回复 - 不使用
    "CMD_POST_FOLLOW_RES",  # 跟随请求

    "CMD_POST_RELOGIN_REQ", # 请求重新上线回复 - 不使用
	"CMD_POST_RELOGIN_RES", # 请求重新上线

))


def get_sonar_cmd(cmd):
    return CMD_SONAR_NONE + cmd.value
