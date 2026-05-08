#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
日志管理器 - 核心组件
"""

import os
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from .config import LogConfig
from crawlo.utils.singleton import SingletonMeta


class LogManager(metaclass=SingletonMeta):
    """
    日志管理器 - 单例模式
    
    职责：
    1. 全局日志配置管理
    2. 配置状态跟踪
    3. 线程安全的配置更新
    """

    def __init__(self):
        self._config: Optional[LogConfig] = None
        self._configured = False
        self._config_lock = threading.RLock()

    @property
    def config(self) -> Optional[LogConfig]:
        """获取当前配置"""
        with self._config_lock:
            return self._config

    @property
    def is_configured(self) -> bool:
        """检查是否已配置"""
        return self._configured

    def configure(self, settings=None, **kwargs) -> LogConfig:
        """
        配置日志系统
        
        Args:
            settings: 配置对象或None
            **kwargs: 关键字参数配置
            
        Returns:
            LogConfig: 生效的配置对象
        """
        with self._config_lock:
            # 总是重新配置，即使已经配置过
            # 从不同来源创建配置
            if settings is not None:
                # 检查settings是否已经是LogConfig对象
                if isinstance(settings, LogConfig):
                    config = settings
                else:
                    config = LogConfig.from_settings(settings)
            elif kwargs:
                config = LogConfig.from_dict(kwargs)
            else:
                config = LogConfig()  # 使用默认配置

            # 验证配置
            is_valid, error_msg = config.validate()
            if not is_valid:
                raise ValueError(f"Invalid log configuration: {error_msg}")

            self._config = config
            self._configured = True

            return config

    def reset(self):
        """重置配置（主要用于测试）"""
        with self._config_lock:
            self._config = None
            self._configured = False
    
    def cleanup_old_logs(self, log_dir: str = None, days: int = 1) -> int:
        """清理指定天数之前的日志文件
        
        Args:
            log_dir: 日志目录路径，默认使用配置中的日志目录
            days: 保留天数，默认 1 天
            
        Returns:
            int: 删除的文件数量
        """
        
        cutoff_time = time.time() - (days * 86400)
        deleted_count = 0
        
        # 匹配文件名中的时间戳：ofweek_standalone_20260505_171709.log
        time_pattern = re.compile(r'_(\d{8})_\d{6}\.log$')
        
        # 获取日志目录
        with self._config_lock:
            if log_dir is None:
                if self._config and self._config.file_path:
                    parent = Path(self._config.file_path).parent
                    log_dir = str(parent) if parent.name else 'logs'
                else:
                    log_dir = 'logs'
        
        # 安全检查：防止误删当前目录文件
        if not log_dir or log_dir == '.':
            log_dir = 'logs'
        
        if not os.path.exists(log_dir):
            return 0
        
        try:
            for filename in os.listdir(log_dir):
                if not filename.endswith('.log'):
                    continue
                
                file_path = os.path.join(log_dir, filename)
                if not os.path.isfile(file_path):
                    continue
                
                # 优先使用文件名中的时间，回退到文件修改时间
                match = time_pattern.search(filename)
                if match:
                    try:
                        # 使用本地时区解析文件名时间，避免时区偏差
                        file_date = datetime.strptime(match.group(1), '%Y%m%d')
                        file_date = file_date.replace(tzinfo=datetime.now().astimezone().tzinfo)
                        file_mtime = file_date.timestamp()
                    except ValueError:
                        file_mtime = os.path.getmtime(file_path)
                else:
                    file_mtime = os.path.getmtime(file_path)
                
                if file_mtime < cutoff_time:
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except OSError as e:
                        import logging
                        logging.getLogger(__name__).debug(f"Failed to delete log file: {file_path}, error: {e}")
        except PermissionError as e:
            import logging
            logging.getLogger(__name__).debug(f"Permission denied cleaning logs: {log_dir}, error: {e}")
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug(f"Failed to clean old logs: {e}")
        
        return deleted_count


# 全局实例
_log_manager = LogManager()


# 模块级便捷函数
def configure(settings=None, **kwargs) -> LogConfig:
    """配置日志系统"""
    return _log_manager.configure(settings, **kwargs)


def is_configured() -> bool:
    """检查是否已配置"""
    return _log_manager.is_configured


def get_config() -> Optional[LogConfig]:
    """获取当前配置"""
    return _log_manager.config


def reset():
    """重置配置"""
    _log_manager.reset()
