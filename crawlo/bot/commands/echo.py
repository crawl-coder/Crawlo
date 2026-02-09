# -*- coding: utf-8 -*-
"""
===================================
回声命令
===================================

简单回声命令，用于测试机器人框架。
"""

from typing import List

from crawlo.bot.commands.base import BotCommand
from crawlo.bot.models import BotMessage, BotResponse


class EchoCommand(BotCommand):
    """
    回声命令
    
    简单回显用户输入的内容。
    """
    
    @property
    def name(self) -> str:
        return "echo"
    
    @property
    def aliases(self) -> List[str]:
        return ["repeat", "说", "重复"]
    
    @property
    def description(self) -> str:
        return "回显你输入的内容"
    
    @property
    def usage(self) -> str:
        return "/echo <内容>"
    
    def validate_args(self, args: List[str]) -> str:
        """验证参数"""
        if not args:
            return "请输入要回显的内容"
        return None
    
    def execute(self, message: BotMessage, args: List[str]) -> BotResponse:
        """执行回声命令"""
        content = " ".join(args)
        return BotResponse.text_response(f"_echo_: {content}")