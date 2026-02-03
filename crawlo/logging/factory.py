#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
日志器工厂 - 创建和缓存Logger实例
"""

import logging
import os
import sys
import threading
from weakref import WeakValueDictionary

# 已取消日志轮转功能，使用基础FileHandler
# 不再导入RotatingFileHandler或ConcurrentRotatingFileHandler

from .manager import get_config, is_configured, configure
from .config import LogConfig


class LoggerFactory:
    """
    Logger工厂类 - 负责创建和缓存Logger实例
    
    特点：
    1. 使用WeakValueDictionary避免内存泄漏
    2. 线程安全的Logger创建
    3. 自动配置管理
    4. 简单的缓存策略
    5. Windows兼容的日志轮转处理
    """
    
    # Logger缓存 - 使用弱引用避免内存泄漏
    _logger_cache: WeakValueDictionary = WeakValueDictionary()
    _cache_lock = threading.RLock()
    
    @classmethod
    def get_logger(cls, name: str = 'crawlo') -> logging.Logger:
        """
        获取Logger实例
        
        Args:
            name: Logger名称
            
        Returns:
            logging.Logger: 配置好的Logger实例
        """
        # 确保日志系统已配置
        if not is_configured():
            configure()  # 使用默认配置
        
        # 检查缓存
        with cls._cache_lock:
            if name in cls._logger_cache:
                return cls._logger_cache[name]
            
            # 创建新的Logger
            logger = cls._create_logger(name)
            cls._logger_cache[name] = logger
            return logger
    
    @classmethod
    def _create_logger(cls, name: str) -> logging.Logger:
        """创建新的Logger实例"""
        config = get_config()
        if not config:
            raise RuntimeError("日志系统未配置，请先调用 configure_logging() 进行配置")
        
        # 创建Logger
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)  # Logger本身设为最低级别
        
        # 清除现有handlers（避免重复添加）
        logger.handlers.clear()
        
        # 获取模块级别
        module_level = config.get_module_level(name)
        
        # 创建formatter
        formatter = logging.Formatter(config.get_format())
        
        # 添加控制台Handler
        if config.console_enabled:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            # 使用专门的控制台级别或模块级别
            console_level = config.get_console_level()
            level = getattr(logging, console_level.upper(), logging.INFO)
            console_handler.setLevel(level)
            logger.addHandler(console_handler)
        
        # 添加文件Handler
        if config.file_enabled and config.file_path:
            try:
                # 确保日志目录存在
                log_dir = os.path.dirname(config.file_path)
                if log_dir and not os.path.exists(log_dir):
                    os.makedirs(log_dir, exist_ok=True)
                
                
                # 使用基础FileHandler，不支持轮转
                file_handler = logging.FileHandler(
                    filename=config.file_path,
                    encoding=config.encoding
                )
                
                file_handler.setFormatter(formatter)
                # 使用专门的文件级别或模块级别
                file_level = config.get_file_level()
                level = getattr(logging, file_level.upper(), logging.INFO)
                file_handler.setLevel(level)
                logger.addHandler(file_handler)
            except Exception as e:
                # 文件Handler创建失败时，至少保证控制台输出
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(formatter)
                console_handler.setLevel(logging.WARNING)
                logger.addHandler(console_handler)
                logger.warning(f"无法创建文件日志处理器: {e}，仅使用控制台输出。")
        
        # 防止向上传播（避免重复输出）
        logger.propagate = False
        
        return logger
    
    @classmethod
    def clear_cache(cls):
        """清空Logger缓存"""
        with cls._cache_lock:
            cls._logger_cache.clear()
    
    @classmethod
    def refresh_loggers(cls, new_config: LogConfig):
        """刷新所有缓存的Logger（配置更新时使用）"""
        with cls._cache_lock:
            # 清空缓存，强制重新创建
            cls._logger_cache.clear()


# 便捷函数
def get_logger(name: str = 'crawlo') -> logging.Logger:
    """获取Logger实例的便捷函数"""
    return LoggerFactory.get_logger(name)