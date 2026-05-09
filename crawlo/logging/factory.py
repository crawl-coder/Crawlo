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

from .manager import get_config, is_configured, configure
from .config import LogConfig


class LoggerFactory:
    """
    Logger Factory - Create and cache Logger instances
    
    Features:
    1. WeakValueDictionary to prevent memory leaks
    2. Thread-safe logger creation
    3. Automatic configuration management
    4. Simple caching strategy
    """
    
    # Logger cache - weak references to prevent memory leaks
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
        """Create a new Logger instance
        
        Args:
            name: Logger name
            
        Returns:
            logging.Logger: Configured logger instance
        """
        config = get_config()
        if not config:
            raise RuntimeError("日志系统未配置，请先调用 configure_logging() 进行配置")
        
        # 创建Logger
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)  # Logger本身设为最低级别
        
        # Clear existing handlers (avoid duplicate addition)
        logger.handlers.clear()
        
        # Get module level
        module_level = config.get_module_level(name)
        
        # Create formatter
        formatter = logging.Formatter(config.get_format())
        
        # Add console handler
        if config.console_enabled:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            # Use dedicated console level or module level
            console_level = config.get_console_level()
            level = getattr(logging, console_level.upper(), logging.INFO)
            console_handler.setLevel(level)
            logger.addHandler(console_handler)
        
        # Add file handler
        if config.file_enabled and config.file_path:
            try:
                # Ensure log directory exists
                log_dir = os.path.dirname(config.file_path)
                if log_dir and not os.path.exists(log_dir):
                    os.makedirs(log_dir, exist_ok=True)
                
                # Use basic FileHandler (rotation not supported)
                file_handler = logging.FileHandler(
                    filename=config.file_path,
                    encoding=config.encoding
                )
                
                file_handler.setFormatter(formatter)
                # Use dedicated file level or module level
                file_level = config.get_file_level()
                level = getattr(logging, file_level.upper(), logging.INFO)
                file_handler.setLevel(level)
                logger.addHandler(file_handler)
            except (OSError, PermissionError) as e:
                # When file handler creation fails, ensure console output at least
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(formatter)
                console_handler.setLevel(logging.WARNING)
                logger.addHandler(console_handler)
                logger.warning(f"Failed to create file log handler: {e}, using console output only.")
        
        # Prevent upward propagation (avoid duplicate output)
        logger.propagate = False
        
        return logger
    
    @classmethod
    def clear_cache(cls):
        """Clear logger cache"""
        with cls._cache_lock:
            cls._logger_cache.clear()
    
    @classmethod
    def refresh_loggers(cls, new_config: LogConfig):
        """Refresh all cached loggers (used when configuration updates)"""
        with cls._cache_lock:
            # 清空缓存，强制重新创建
            cls._logger_cache.clear()


# Convenience function
def get_logger(name: str = 'crawlo') -> logging.Logger:
    """Convenience function to get Logger instance"""
    return LoggerFactory.get_logger(name)