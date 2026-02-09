# -*- coding: utf-8 -*-
"""
===================================
平台适配器模块
===================================

包含各平台的适配器实现。
"""

from crawlo.bot.platforms.base import BotPlatform

# 所有平台适配器类
ALL_PLATFORMS = {
    # 'feishu': FeishuPlatform,
    # 'dingtalk': DingTalkPlatform,
    # 'wecom': WeComPlatform,
    # 'telegram': TelegramPlatform,
}

__all__ = [
    'BotPlatform',
    'ALL_PLATFORMS',
]