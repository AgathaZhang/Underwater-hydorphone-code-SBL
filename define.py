# coding=utf-8
# define.py
from enum import Enum

PLAT_FORM = Enum('PLAT_FORM', (
    "PLATFORM_NONE",

    "PLATFORM_ROUTER",  # router
    "PLATFORM_ROBOT",  # robot
    "PLATFORM_RC",     # rc
    "PLATFORM_TRITON",  # triton
    "PLATFORM_SONAR",  # sonar

    "PLATFORM_END",
))


def get_plat_form(sn):
    plat_form = sn[1]

    if plat_form == 'T':
        return PLAT_FORM.PLATFORM_ROUTER
    elif plat_form == 'R':
        return PLAT_FORM.PLATFORM_ROBOT
    elif plat_form == 'C':
        return PLAT_FORM.PLATFORM_RC
    elif plat_form == 'I':
        return PLAT_FORM.PLATFORM_TRITON
    elif plat_form == 'S':
        return PLAT_FORM.PLATFORM_SONAR
    else:
        return PLAT_FORM.PLATFORM_NONE

