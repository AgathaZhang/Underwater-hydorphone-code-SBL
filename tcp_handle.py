# coding=utf-8
# tcp_handle.py
import struct
import time
from config import configIns
from proto.robot import CMD_ROBOT, get_robot_cmd
from proto.sonar import CMD_SONAR, get_sonar_cmd


def handle_data(cmd, data):
    ''' 处理data包体 '''
    func = cmd_handle_dict.get(cmd, handle_error_cmd)
    func(data)

    return


def handle_robot_set_config_res(data):
    ''' 设置ROBOT配置请求 '''
    _body = struct.unpack('<f', data)
    s_tx_depth = _body[0]
    configIns.robot.set_config(s_tx_depth)


def handle_sonar_set_config_res(data):
    ''' 设置SONAR配置请求 '''
    _body = struct.unpack('<f3i', data)
    threshold_factor = _body[0]
    threshold_offset = _body[1]
    overlay_count = _body[2]
    follow_index_range = _body[3]

    configIns.sonar.set_config(
        threshold_factor, threshold_offset, overlay_count, follow_index_range)


def handle_sonar_post_follow_res(data):
    ''' 读取跟随请求 '''
    body = struct.unpack('<I', data)
    index = body[0]
    print("跟随.", index)
    configIns.sonar.set_follow_index(index)


def handle_sonar_post_read_step_res(data):
    ''' 读取音频步进请求 '''
    body = struct.unpack('<f', data)
    read_step = body[0]
    configIns.sonar.set_read_step(read_step)


def handle_sonar_post_save_wav_res(data):
    ''' 保存音频文件请求 '''
    body = struct.unpack('<I', data)
    save_wav_second = body[0]
    configIns.sonar.set_save_wav_second(save_wav_second)


def handle_robot_login_res(data):
    ''' 登录回复 '''
    print("handle_robot_login_res", len(data))


def handle_error_cmd(data):
    ''' 处理错误cmd '''
    print("handle_error_cmd", len(data), hex(data))


cmd_handle_dict = {
    get_robot_cmd(CMD_ROBOT.CMD_LOGIN_RES): handle_robot_login_res,
    get_robot_cmd(CMD_ROBOT.CMD_SET_CONFIG_RES): handle_robot_set_config_res,

    get_sonar_cmd(CMD_SONAR.CMD_SET_CONFIG_RES): handle_sonar_set_config_res,
    get_sonar_cmd(CMD_SONAR.CMD_POST_READ_STEP_RES): handle_sonar_post_read_step_res,
    get_sonar_cmd(CMD_SONAR.CMD_POST_FOLLOW_RES): handle_sonar_post_follow_res,
    get_sonar_cmd(CMD_SONAR.CMD_POST_SAVE_WAV_RES): handle_sonar_post_save_wav_res,
}

