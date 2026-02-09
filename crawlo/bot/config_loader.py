# -*- coding: utf-8 -*-
"""
===================================
通知系统配置加载器
===================================

从框架配置中加载通知系统相关配置并应用到各渠道。
"""

import logging
from typing import Optional

from crawlo.bot.notifier import get_notifier
from crawlo.bot.channels.dingtalk import get_dingtalk_channel
from crawlo.bot.channels.feishu import get_feishu_channel
from crawlo.bot.channels.wecom import get_wecom_channel

logger = logging.getLogger(__name__)


# 全局配置加载状态
_config_loaded = False


def ensure_config_loaded():
    """
    确保配置已加载，如果未加载则立即加载
    """
    global _config_loaded
    if not _config_loaded:
        apply_settings_config()
        _config_loaded = True


def load_notification_config(settings: Optional[dict] = None):
    """
    从框架配置加载通知系统配置
    
    Args:
        settings: 框架配置字典，如果为None则尝试从全局配置获取
    """
    try:
        # 如果没有传入settings，尝试从框架获取
        if settings is None:
            try:
                from crawlo.config import get_config
                config = get_config()
                settings = config.to_dict() if hasattr(config, 'to_dict') else {}
            except ImportError:
                logger.warning("[ConfigLoader] 无法导入框架配置，使用默认配置")
                settings = {}
        
        # 获取通知器实例
        notifier = get_notifier()
        
        # 加载钉钉配置
        if 'DINGTALK_WEBHOOK' in settings and settings['DINGTALK_WEBHOOK']:
            dingtalk_channel = get_dingtalk_channel()
            dingtalk_channel.set_config(
                webhook_url=settings['DINGTALK_WEBHOOK'],
                secret=settings.get('DINGTALK_SECRET'),
                keywords=settings.get('DINGTALK_KEYWORDS', []),
                at_mobiles=settings.get('DINGTALK_AT_MOBILES', []),
                at_userids=settings.get('DINGTALK_AT_USERIDS', []),
                is_at_all=settings.get('DINGTALK_IS_AT_ALL', False)
            )
            logger.info("[ConfigLoader] 钉钉通知配置加载成功")
        else:
            logger.debug("[ConfigLoader] 未配置钉钉 Webhook URL")
        
        # 加载飞书配置
        if 'FEISHU_WEBHOOK' in settings and settings['FEISHU_WEBHOOK']:
            feishu_channel = get_feishu_channel()
            feishu_channel.set_config(
                webhook_url=settings['FEISHU_WEBHOOK'],
                secret=settings.get('FEISHU_SECRET'),
                at_users=settings.get('FEISHU_AT_USERS', []),
                at_mobile=settings.get('FEISHU_AT_MOBILE', []),
                is_at_all=settings.get('FEISHU_IS_AT_ALL', False)
            )
            logger.info("[ConfigLoader] 飞书通知配置加载成功")
        else:
            logger.debug("[ConfigLoader] 未配置飞书 Webhook URL")
        
        # 加载企业微信配置
        if 'WECOM_WEBHOOK' in settings and settings['WECOM_WEBHOOK']:
            wecom_channel = get_wecom_channel()
            wecom_channel.set_config(
                webhook_url=settings['WECOM_WEBHOOK'],
                secret=settings.get('WECOM_SECRET'),
                agent_id=settings.get('WECOM_AGENT_ID'),
                at_users=settings.get('WECOM_AT_USERS', []),
                at_mobile=settings.get('WECOM_AT_MOBILE', []),
                is_at_all=settings.get('WECOM_IS_AT_ALL', False)
            )
            logger.info("[ConfigLoader] 企业微信通知配置加载成功")
        else:
            logger.debug("[ConfigLoader] 未配置企业微信 Webhook URL")
            
        logger.info("[ConfigLoader] 通知系统配置加载完成")
        
    except Exception as e:
        logger.error(f"[ConfigLoader] 配置加载失败: {e}")
        logger.exception(e)


def apply_settings_config():
    """
    应用 settings.py 中的配置到通知系统
    这是一个便捷函数，用于直接从 settings 模块加载配置
    """
    try:
        # 尝试导入项目 settings
        import importlib
        import os
        
        # 获取当前工作目录
        current_dir = os.getcwd()
        
        # 尝试常见的 settings 模块路径
        possible_settings_paths = [
            'settings',
            'ofweek_standalone.settings',
            'crawlo.settings',
        ]
        
        settings_dict = {}
        
        for settings_path in possible_settings_paths:
            try:
                settings_module = importlib.import_module(settings_path)
                # 获取所有大写的配置项
                for attr in dir(settings_module):
                    if attr.isupper():
                        settings_dict[attr] = getattr(settings_module, attr)
                logger.debug(f"[ConfigLoader] 成功从 {settings_path} 加载配置")
                break
            except ImportError:
                continue
        
        if settings_dict:
            load_notification_config(settings_dict)
        else:
            logger.warning("[ConfigLoader] 未找到有效的 settings 模块")
            
    except Exception as e:
        logger.error(f"[ConfigLoader] 应用 settings 配置失败: {e}")
        logger.exception(e)