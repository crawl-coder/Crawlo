# -*- coding: utf-8 -*-
"""
===================================
帮助命令
===================================

显示所有可用命令及其说明。
"""

from typing import List

from crawlo.bot.commands.base import BotCommand
from crawlo.bot.models import BotMessage, BotResponse


class HelpCommand(BotCommand):
    """
    帮助命令
    
    显示所有可用命令列表及说明。
    """
    
    @property
    def name(self) -> str:
        return "help"
    
    @property
    def aliases(self) -> List[str]:
        return ["h", "帮助", "?"]
    
    @property
    def description(self) -> str:
        return "显示帮助信息"
    
    @property
    def usage(self) -> str:
        return "/help [命令名]"
    
    def execute(self, message: BotMessage, args: List[str]) -> BotResponse:
        """执行帮助命令"""
        from crawlo.bot.dispatcher import get_dispatcher
        
        dispatcher = get_dispatcher()
        
        if not args:
            # 显示所有命令
            commands = dispatcher.list_commands()
            
            if not commands:
                return BotResponse.text_response("暂无可用命令")
            
            help_text = "**🤖 可用命令**\n\n"
            for cmd in commands:
                help_text += f"• `/{cmd.name}` - {cmd.description}\n"
            
            help_text += f"\n💡 发送 `/help <命令名>` 获取特定命令的帮助信息"
            
            return BotResponse.markdown_response(help_text)
        else:
            # 显示特定命令帮助
            cmd_name = args[0].lower()
            command = dispatcher.get_command(cmd_name)
            
            if not command:
                return BotResponse.error_response(f"未知命令: {cmd_name}")
            
            return BotResponse.markdown_response(
                f"**/{command.name}** - {command.description}\n\n"
                f"用法: `{command.usage}`\n\n"
                f"别名: {', '.join(command.aliases) if command.aliases else '无'}"
            )