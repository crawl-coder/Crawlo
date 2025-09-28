# ==================== 向后兼容的日志接口 ====================
# 主要功能已迁移到 crawlo.logging 模块
# 本文件提供向后兼容接口，同时支持新的日志系统功能

import logging
from typing import Optional, Any

# 向后兼容：导入新的日志系统
try:
    from crawlo.logging import get_logger as new_get_logger, configure_logging

    _NEW_LOGGING_AVAILABLE = True
except ImportError:
    _NEW_LOGGING_AVAILABLE = False
    new_get_logger = None
    configure_logging = None

LOG_FORMAT = '%(asctime)s - [%(name)s] - %(levelname)s: %(message)s'


# 向后兼容的日志函数
def get_logger(name: str = 'default', level: Optional[int] = None):
    """获取Logger实例 - 向后兼容函数"""
    if _NEW_LOGGING_AVAILABLE and new_get_logger:
        # 使用新的日志系统
        return new_get_logger(name)
    else:
        # 降级到基本的Python logging
        logger = logging.getLogger(name)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(LOG_FORMAT)
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(level or logging.INFO)
        return logger


def get_component_logger(component_class: Any, settings: Optional[Any] = None, level: Optional[str] = None):
    """
    获取组件Logger - 推荐的组件日志创建方式
    
    Args:
        component_class: 组件类
        settings: 配置对象，用于读取日志级别配置
        level: 日志级别（优先级低于settings中的配置）
        
    Returns:
        logging.Logger: 配置好的Logger实例
    """
    # 获取组件名称
    if hasattr(component_class, '__name__'):
        component_name = component_class.__name__
    else:
        component_name = str(component_class)
    
    # 如果新日志系统可用，使用新系统
    if _NEW_LOGGING_AVAILABLE and new_get_logger:
        return new_get_logger(component_name)
    
    # 否则使用向后兼容方式
    # 从settings中获取日志级别（如果提供）
    if settings is not None:
        # 尝试从settings获取组件特定的日志级别
        if hasattr(settings, 'get'):
            # 检查是否有组件特定的日志级别配置
            component_level = settings.get(f'LOG_LEVEL_{component_name}')
            if component_level is not None:
                level = component_level
            else:
                # 检查通用日志级别
                general_level = settings.get('LOG_LEVEL')
                if general_level is not None:
                    level = general_level
    
    # 转换日志级别
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    
    return get_logger(component_name, level)