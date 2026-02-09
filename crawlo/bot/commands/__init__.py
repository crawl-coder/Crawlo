# -*- coding: utf-8 -*-
"""
===================================
命令处理器模块
===================================

包含所有机器人命令的实现。
"""

from crawlo.bot.commands.base import BotCommand
from crawlo.bot.commands.help import HelpCommand
from crawlo.bot.commands.echo import EchoCommand

# 所有可用命令（用于自动注册）
ALL_COMMANDS = [
    HelpCommand,
    EchoCommand,
]

__all__ = [
    'BotCommand',
    'HelpCommand',
    'ALL_COMMANDS',
]