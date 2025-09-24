# ==================== 向后兼容的日志接口 ====================
# 主要功能已迁移到 crawlo.logging 模块
# 本文件仅保留最基本的兼容性接口

import logging
from typing import Optional

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

# 兼容性函数
def get_component_logger(component_class, settings=None, level=None):
    """获取组件Logger - 向后兼容"""
    if hasattr(component_class, '__name__'):
        component_name = component_class.__name__
    else:
        component_name = str(component_class)
    
    return get_logger(component_name)