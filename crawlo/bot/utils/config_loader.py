# -*- coding: utf-8 -*-
"""
===================================
通知系统配置加载器
===================================

从框架配置中加载通知系统相关配置并应用到各渠道。
"""
from typing import Optional

from crawlo.logging import get_logger
from crawlo.bot.core.notifier import get_notifier
from crawlo.bot.channels.dingtalk import get_dingtalk_channel
from crawlo.bot.channels.feishu import get_feishu_channel
from crawlo.bot.channels.wecom import get_wecom_channel
from crawlo.bot.channels.email import get_email_channel
from crawlo.bot.channels.sms import get_sms_channel

logger = get_logger(__name__)


# 全局配置加载状态
_config_loaded = False


def ensure_config_loaded():
    """
    确保配置已加载，如果未加载则立即加载
    """
    global _config_loaded
    
    # 如果已经加载过配置，直接返回
    if _config_loaded:
        logger.debug("[ConfigLoader] 配置已加载，跳过")
        return
    
    # 检查钉钉渠道是否已有配置（双重检查）
    try:
        dingtalk_channel = get_dingtalk_channel()
        if dingtalk_channel.webhook_url:
            # 渠道已有配置，标记为已加载
            logger.debug("[ConfigLoader] 钉钉渠道已有配置，标记为已加载")
            _config_loaded = True
            return
    except Exception as e:
        logger.debug(f"[ConfigLoader] 检查渠道配置时出错: {e}")
    
    # 执行配置加载
    logger.debug("[ConfigLoader] 开始加载配置")
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
        
        # 加载各渠道配置（静默加载，不输出日志）
        
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

        # 加载邮件配置
        if settings.get('EMAIL_HOST') and settings.get('EMAIL_USERNAME'):
            email_channel = get_email_channel()
            email_channel.set_config(
                smtp_host=settings.get('EMAIL_HOST'),
                smtp_port=settings.get('EMAIL_PORT', 587),
                smtp_user=settings.get('EMAIL_USERNAME'),
                smtp_password=settings.get('EMAIL_PASSWORD', ''),
                sender_email=settings.get('EMAIL_FROM', settings.get('EMAIL_USERNAME')),
            )
            # 扩展属性：接收人列表
            email_channel._to_addrs = settings.get('EMAIL_TO', [])
            email_channel._use_tls = settings.get('EMAIL_USE_TLS', True)

        # 加载短信配置
        if settings.get('SMS_PROVIDER') and settings.get('SMS_ACCESS_KEY_ID'):
            sms_channel = get_sms_channel()
            sms_channel.set_config(
                provider=settings.get('SMS_PROVIDER'),
                access_key_id=settings.get('SMS_ACCESS_KEY_ID'),
                access_key_secret=settings.get('SMS_ACCESS_KEY_SECRET', ''),
                sign_name=settings.get('SMS_SIGN_NAME', ''),
            )
            # 扩展属性
            sms_channel._template_code = settings.get('SMS_TEMPLATE_CODE', '')
            sms_channel._phone_numbers = settings.get('SMS_PHONE_NUMBERS', [])

    except Exception as e:
        logger.error(f"[ConfigLoader] 配置加载失败: {e}")
        logger.exception(e)


def _get_settings_module_from_cfg():
    """
    从 crawlo.cfg 文件中读取 settings 模块路径
    
    Returns:
        settings 模块路径，如果未找到则返回 None
    """
    import os
    from crawlo.project import read_crawlo_cfg
    
    current_dir = os.getcwd()
    cfg_path = os.path.join(current_dir, 'crawlo.cfg')
    settings_path = read_crawlo_cfg(cfg_path)
    
    if settings_path:
        logger.debug(f"[ConfigLoader] 从 crawlo.cfg 读取到 settings 路径: {settings_path}")
    
    return settings_path


def apply_settings_config():
    """
    应用 settings.py 中的配置到通知系统
    这是一个便捷函数，用于直接从 settings 模块加载配置
    
    加载顺序：
    1. 首先尝试从 crawlo.project.get_settings() 获取配置
    2. 如果失败，尝试从 crawlo.cfg 读取 settings 路径
    3. 最后尝试常见的 settings 模块路径
    """
    try:
        import importlib
        settings_dict = {}
        
        # 优先使用框架统一的配置获取方式
        try:
            from crawlo.project import get_settings
            settings = get_settings()
            if settings:
                # 获取所有大写的配置项
                settings_dict = {
                    attr: getattr(settings, attr)
                    for attr in dir(settings)
                    if attr.isupper()
                }
                logger.debug("[ConfigLoader] 成功从 crawlo.project.get_settings() 加载配置")
        except (ImportError, Exception) as e:
            logger.debug(f"[ConfigLoader] 无法从 crawlo.project 获取配置: {e}")
        
        # 如果未获取到配置，尝试其他方式
        if not settings_dict:
            # 尝试从 crawlo.cfg 读取 settings 路径
            settings_paths = []
            cfg_settings = _get_settings_module_from_cfg()
            if cfg_settings:
                settings_paths.append(cfg_settings)
            
            # 如果没有找到配置，尝试通用的 'settings' 作为备选
            if not settings_paths:
                settings_paths.append('settings')
            
            for settings_path in settings_paths:
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
            logger.warning("[ConfigLoader] 未找到有效的 settings 模块，通知系统将使用默认配置")
            
    except Exception as e:
        logger.error(f"[ConfigLoader] 应用 settings 配置失败: {e}")
        logger.exception(e)