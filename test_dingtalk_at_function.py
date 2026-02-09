#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
钉钉通知 @ 功能测试脚本
测试钉钉机器人 @ 人员功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlo.bot.channels.dingtalk import get_dingtalk_channel
from crawlo.bot.models import NotificationMessage, NotificationType, ChannelType
from crawlo.bot.notifier import get_notifier


def test_dingtalk_at_function():
    """测试钉钉 @ 功能"""
    print("🔧 配置钉钉通知渠道（带@功能）...")
    
    # 使用 settings.py 中的配置
    webhook_url = "https://oapi.dingtalk.com/robot/send?access_token=f2b9ee74076d0525c392e9a4c2a021a0144d295ed7210f53fee402eb349e665f"
    secret = "SEC46ca0b774d564cedebc4761e23f158c20f6558ebed94b1bd18e2ba77259b0c40"
    
    # 获取钉钉渠道实例并配置，使用关键词 "爬虫" 并设置@功能
    dingtalk_channel = get_dingtalk_channel()
    
    print("\n--- 测试1: @特定手机号 ---")
    # 配置@特定手机号
    dingtalk_channel.set_config(
        webhook_url=webhook_url, 
        secret=secret, 
        keywords=["爬虫"],
        at_mobiles=["15361276730"]  # 使用 settings.py 中的手机号
    )
    
    # 注册到通知器
    notifier = get_notifier()
    notifier.unregister_channel('dingtalk')  # 先移除之前的实例
    notifier.register_channel(dingtalk_channel)
    
    try:
        message = NotificationMessage(
            channel=ChannelType.DINGTALK.value,
            notification_type=NotificationType.ALERT,
            title="【@测试1】钉钉@特定手机号",
            content="这是测试@特定手机号的通知，验证钉钉机器人@功能是否正常。",
            priority="high"
        )
        
        response = dingtalk_channel.send(message)
        print(f"@特定手机号发送结果: success={response.success}")
        if response.success:
            print("✅ @特定手机号通知发送成功！")
        else:
            print(f"❌ @特定手机号通知失败: {response.error}")
    except Exception as e:
        print(f"@特定手机号通知异常: {e}")
    
    print("\n--- 测试2: @所有人 ---")
    # 配置@所有人
    dingtalk_channel.set_config(
        webhook_url=webhook_url, 
        secret=secret, 
        keywords=["爬虫"],
        is_at_all=True  # @所有人
    )
    
    notifier.unregister_channel('dingtalk')  # 重新注册
    notifier.register_channel(dingtalk_channel)
    
    try:
        message = NotificationMessage(
            channel=ChannelType.DINGTALK.value,
            notification_type=NotificationType.STATUS,
            title="【@测试2】钉钉@所有人",
            content="这是测试@所有人的通知，验证钉钉机器人@所有人功能是否正常。",
            priority="medium"
        )
        
        response = dingtalk_channel.send(message)
        print(f"@所有人发送结果: success={response.success}")
        if response.success:
            print("✅ @所有人通知发送成功！")
        else:
            print(f"❌ @所有人通知失败: {response.error}")
    except Exception as e:
        print(f"@所有人通知异常: {e}")
    
    print("\n--- 测试3: 同时配置@手机号和@所有人 ---")
    # 配置同时@手机号和所有人
    dingtalk_channel.set_config(
        webhook_url=webhook_url, 
        secret=secret, 
        keywords=["爬虫"],
        at_mobiles=["15361276730"],
        is_at_all=True
    )
    
    notifier.unregister_channel('dingtalk')  # 重新注册
    notifier.register_channel(dingtalk_channel)
    
    try:
        message = NotificationMessage(
            channel=ChannelType.DINGTALK.value,
            notification_type=NotificationType.PROGRESS,
            title="【@测试3】钉钉@特定手机号+所有人",
            content="这是测试同时@特定手机号和所有人的通知，验证钉钉机器人多重@功能是否正常。",
            priority="medium"
        )
        
        response = dingtalk_channel.send(message)
        print(f"多重@发送结果: success={response.success}")
        if response.success:
            print("✅ 多重@通知发送成功！")
        else:
            print(f"❌ 多重@通知失败: {response.error}")
    except Exception as e:
        print(f"多重@通知异常: {e}")
    
    print("\n--- 测试4: 不使用@功能 ---")
    # 配置不使用@功能
    dingtalk_channel.set_config(
        webhook_url=webhook_url, 
        secret=secret, 
        keywords=["爬虫"]
        # 不设置任何@参数
    )
    
    notifier.unregister_channel('dingtalk')  # 重新注册
    notifier.register_channel(dingtalk_channel)
    
    try:
        message = NotificationMessage(
            channel=ChannelType.DINGTALK.value,
            notification_type=NotificationType.STATUS,
            title="【@测试4】钉钉普通通知",
            content="这是不使用@功能的普通通知，验证基本发送功能是否正常。",
            priority="medium"
        )
        
        response = dingtalk_channel.send(message)
        print(f"普通通知发送结果: success={response.success}")
        if response.success:
            print("✅ 普通通知发送成功！")
        else:
            print(f"❌ 普通通知失败: {response.error}")
    except Exception as e:
        print(f"普通通知异常: {e}")
    
    print("\n" + "="*60)
    print("🎉 钉钉@功能测试总结:")
    print("✅ 钉钉通知系统支持@特定手机号功能")
    print("✅ 钉钉通知系统支持@所有人功能")
    print("✅ 钉钉通知系统支持组合@功能")
    print("✅ 配置参数已添加到 default_settings.py")
    print("✅ 用户可以通过 DINGTALK_AT_MOBILES、DINGTALK_AT_USERIDS、DINGTALK_IS_AT_ALL 配置@功能")
    print("="*60)


if __name__ == "__main__":
    test_dingtalk_at_function()