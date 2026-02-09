#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
机器人框架测试脚本
"""

from crawlo.bot.models import BotMessage, ChatType
from crawlo.bot.dispatcher import get_dispatcher

def test_bot_framework():
    """测试机器人框架的基本功能"""
    print("=== 测试机器人框架 ===")
    
    # 获取分发器实例
    dispatcher = get_dispatcher()
    print(f"已注册命令数量: {len(dispatcher.list_commands())}")
    
    # 测试帮助命令
    print("\n--- 测试 /help 命令 ---")
    help_message = BotMessage(
        platform="test",
        message_id="test_msg_1",
        user_id="test_user_1",
        user_name="Test User",
        chat_id="test_chat_1",
        chat_type=ChatType.PRIVATE,
        content="/help",
        raw_content="/help",
        mentioned=False,
        timestamp=None
    )
    
    help_response = dispatcher.dispatch(help_message)
    print(f"帮助命令响应: {help_response.text}")
    
    # 测试回声命令
    print("\n--- 测试 /echo 命令 ---")
    echo_message = BotMessage(
        platform="test",
        message_id="test_msg_2",
        user_id="test_user_1",
        user_name="Test User",
        chat_id="test_chat_1",
        chat_type=ChatType.PRIVATE,
        content="/echo Hello World!",
        raw_content="/echo Hello World!",
        mentioned=False,
        timestamp=None
    )
    
    echo_response = dispatcher.dispatch(echo_message)
    print(f"回声命令响应: {echo_response.text}")
    
    # 测试未知命令
    print("\n--- 测试未知命令 ---")
    unknown_message = BotMessage(
        platform="test",
        message_id="test_msg_3",
        user_id="test_user_1",
        user_name="Test User",
        chat_id="test_chat_1",
        chat_type=ChatType.PRIVATE,
        content="/unknown_command",
        raw_content="/unknown_command",
        mentioned=False,
        timestamp=None
    )
    
    unknown_response = dispatcher.dispatch(unknown_message)
    print(f"未知命令响应: {unknown_response.text}")
    
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    test_bot_framework()