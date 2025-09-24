import os
import threading
from logging import (
    Formatter,
    StreamHandler,
    FileHandler,
    Logger,
    DEBUG,
    INFO,
    getLevelName,
)
from weakref import WeakValueDictionary
from functools import lru_cache
from typing import Optional, Dict, Any

LOG_FORMAT = '%(asctime)s - [%(name)s] - %(levelname)s: %(message)s'

# 日志系统状态管理
_log_state = {
    'configured': False,
    'lock': threading.Lock(),
    'init_order': [
        'basic_setup',
        'handlers_config',
        'full_config'
    ],
    'current_step': 'uninitialized'
}


class LoggerManager:
    """
    优化的日志管理器，提供统一的日志配置和获取接口
    
    优化要点：
    1. 使用WeakValueDictionary防止内存泄漏
    2. LRU缓存减少重复计算
    3. 延迟初始化减少启动开销
    4. 减少锁竞争
    """
    
    # 使用WeakValueDictionary防止内存泄漏
    logger_cache: WeakValueDictionary = WeakValueDictionary()
    
    # 简化的配置管理
    _config = {
        'initialized': False,
        'level': INFO,
        'filename': None,
        'format': LOG_FORMAT,
        'encoding': 'utf-8',
        'module_levels': {}
    }
    
    # 读写锁 - 减少锁竞争
    _lock = threading.RLock()
    _config_lock = threading.Lock()
    _early_initialized = False

    @classmethod
    @lru_cache(maxsize=256)
    def _parse_level(cls, level) -> int:
        """缓存级别解析结果"""
        if level is None:
            return INFO
        if isinstance(level, int):
            return level
        if isinstance(level, str):
            level_value = getLevelName(level.upper())
            return level_value if isinstance(level_value, int) else INFO
        return INFO
    
    @classmethod
    @lru_cache(maxsize=128)
    def _get_module_level_cached(cls, module_name: str) -> int:
        """缓存模块级别查找"""
        module_levels = cls._config['module_levels']
        if not module_levels:
            return cls._config['level']
        
        # 优化查找算法
        parts = module_name.split('.')
        for i in range(len(parts), 0, -1):
            partial_name = '.'.join(parts[:i])
            if partial_name in module_levels:
                return cls._parse_level(module_levels[partial_name])
        
        return cls._config['level']

    @classmethod
    def configure(cls, settings=None, **kwargs):
        """
        线程安全的配置方法
        使用 settings 对象或关键字参数配置日志
        这个方法可以安全地被多次调用，但只有第一次调用才会生效
        """
        with cls._config_lock:
            if cls._config['initialized']:
                return
                
            get_val = settings.get if hasattr(settings, 'get') else kwargs.get
            
            cls._config.update({
                'initialized': True,
                'level': cls._parse_level(get_val('LOG_LEVEL', 'INFO')),
                'filename': get_val('LOG_FILE'),
                'format': get_val('LOG_FORMAT', LOG_FORMAT),
                'encoding': get_val('LOG_ENCODING', 'utf-8'),
                'module_levels': get_val('LOG_LEVELS', {})
            })
            
            # 清理缓存
            cls._parse_level.cache_clear()
            cls._get_module_level_cached.cache_clear()
            cls._early_initialized = True

    @classmethod
    def get_logger(cls, name: str = 'default', level: Optional[int] = None) -> Logger:
        """
        优化的logger获取方法
        如果日志系统尚未初始化，会自动进行早期初始化
        """
        # 快速路径 - 避免不必要的锁
        if not cls._config['initialized']:
            with cls._config_lock:
                if not cls._config['initialized']:
                    cls.configure()
        
        # 使用简化的cache key
        final_level = level if level is not None else cls._get_module_level_cached(name)
        cache_key = f"{name}:{final_level}:{cls._config['filename'] or 'console'}"
        
        # 读锁检查缓存
        with cls._lock:
            if cache_key in cls.logger_cache:
                return cls.logger_cache[cache_key]
        
        # 创建新logger
        logger = cls._create_logger(name, final_level)
        
        # 写锁更新缓存
        with cls._lock:
            cls.logger_cache[cache_key] = logger
            
        return logger
    
    @classmethod
    def _create_logger(cls, name: str, level: int) -> Logger:
        """创建logger实例"""
        logger = Logger(name)
        logger.setLevel(DEBUG)  # Logger本身设为最低级别
        
        formatter = Formatter(cls._config['format'])
        
        # 控制台handler
        console_handler = StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        logger.addHandler(console_handler)
        
        # 文件handler
        filename = cls._config['filename']
        if filename:
            try:
                log_dir = os.path.dirname(filename)
                if log_dir and not os.path.exists(log_dir):
                    os.makedirs(log_dir, exist_ok=True)
                
                file_handler = FileHandler(filename, encoding=cls._config['encoding'])
                file_handler.setFormatter(formatter)
                file_handler.setLevel(level)
                logger.addHandler(file_handler)
            except Exception as e:
                print(f"[OptimizedLogger] 创建文件handler失败: {e}")
        
        return logger

    @classmethod
    def is_configured(cls):
        """检查日志系统是否已配置"""
        return cls._config['initialized']
    
    @classmethod
    def is_early_initialized(cls):
        """检查日志系统是否已进行早期初始化"""
        return cls._early_initialized
        
    @classmethod
    def reset(cls):
        """重置日志系统状态（主要用于测试）"""
        with cls._config_lock:
            cls._config['initialized'] = False
            cls._early_initialized = False
            cls.logger_cache.clear()
            cls._parse_level.cache_clear()
            cls._get_module_level_cached.cache_clear()

# ==================== 统一Logger解决方案 ====================

# 全局logger缓存 - 线程安全
_unified_loggers: Dict[str, 'UnifiedLogger'] = {}
_unified_lock = threading.RLock()


class UnifiedLogger:
    """
    统一Logger包装器
    提供始终可用的日志接口，无需延迟初始化
    """
    
    def __init__(self, name: str):
        self.name = name
        self._logger: Optional[Logger] = None
        self._lock = threading.RLock()
    
    @property
    def logger(self) -> Logger:
        """获取实际的logger实例"""
        if self._logger is None:
            with self._lock:
                if self._logger is None:
                    # 确保日志系统至少进行了早期初始化
                    if not LoggerManager.is_early_initialized():
                        LoggerManager.configure()
                    self._logger = LoggerManager.get_logger(self.name)
        return self._logger
    
    def info(self, msg, *args, **kwargs):
        """INFO级别日志"""
        return self.logger.info(msg, *args, **kwargs)
    
    def debug(self, msg, *args, **kwargs):
        """DEBUG级别日志"""
        return self.logger.debug(msg, *args, **kwargs)
    
    def warning(self, msg, *args, **kwargs):
        """WARNING级别日志"""
        return self.logger.warning(msg, *args, **kwargs)
    
    def error(self, msg, *args, **kwargs):
        """ERROR级别日志"""
        return self.logger.error(msg, *args, **kwargs)
    
    def critical(self, msg, *args, **kwargs):
        """CRITICAL级别日志"""
        return self.logger.critical(msg, *args, **kwargs)
    
    def exception(self, msg, *args, exc_info=True, **kwargs):
        """异常日志"""
        return self.logger.error(msg, *args, exc_info=exc_info, **kwargs)
    
    def refresh(self):
        """刷新logger实例（配置更新后使用）"""
        with self._lock:
            self._logger = None


def get_unified_logger(name: str) -> UnifiedLogger:
    """
    获取统一的logger实例
    
    这个函数替换所有的延迟logger初始化模式
    
    Args:
        name: logger名称
        
    Returns:
        UnifiedLogger实例，始终可用
    """
    if name not in _unified_loggers:
        with _unified_lock:
            if name not in _unified_loggers:
                _unified_loggers[name] = UnifiedLogger(name)
    
    return _unified_loggers[name]


def refresh_all_loggers():
    """刷新所有logger实例（配置更新后调用）"""
    with _unified_lock:
        for logger in _unified_loggers.values():
            logger.refresh()


# 全局快捷函数
get_logger = LoggerManager.get_logger


def get_component_logger(component_class, settings=None, level=None):
    """
    统一的组件logger创建函数
    为框架组件提供一致的日志记录器创建方式
    
    Args:
        component_class: 组件类或类名
        settings: 配置管理器实例（可选）
        level: 特定的日志级别（可选，优先级最高）
    
    Returns:
        logger实例
    
    Examples:
        # 在组件初始化中使用
        self.logger = get_component_logger(self.__class__, crawler.settings)
        
        # 或者传递特定级别
        self.logger = get_component_logger(self.__class__, crawler.settings, 'DEBUG')
        
        # 简单使用（只传类）
        self.logger = get_component_logger(self.__class__)
    """
    # 获取组件名称
    if hasattr(component_class, '__name__'):
        component_name = component_class.__name__
    elif isinstance(component_class, str):
        component_name = component_class
    else:
        component_name = str(component_class)
    
    # 确定日志级别
    final_level = None
    if level is not None:
        # 优先使用显式传递的level参数
        final_level = level
    elif settings and hasattr(settings, 'get'):
        # 其次使用settings中的LOG_LEVEL
        final_level = settings.get('LOG_LEVEL')
    
    # 创建logger
    return LoggerManager.get_logger(component_name, final_level)