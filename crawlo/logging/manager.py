#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Log Manager - Core Component

Architecture Note:
- This module manages configuration state only
- LoggerFactory depends on this module for configuration access
- No circular dependency: manager.py -> config.py (one-way)
"""

import logging
import os
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from .config import LogConfig
from crawlo.core.singleton import SingletonMeta


class LogManager(metaclass=SingletonMeta):
    """
    Log Manager - Singleton Pattern
    
    Responsibilities:
    1. Global log configuration management
    2. Configuration state tracking
    3. Thread-safe configuration updates
    """
    
    # Constants
    SECONDS_PER_DAY = 86400
    
    # Module-level logger
    logger = logging.getLogger(__name__)

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
        """Reset configuration (mainly for testing)"""
        with self._config_lock:
            self._config = None
            self._configured = False

    def set_file_path(self, file_path: str) -> bool:
        """动态更新日志文件路径（如分布式 Worker 追加 worker_id）。

        更新全局配置并对已创建的 logger 重建文件 handler（关闭旧 handler）。
        适用于 settings 阶段拿不到运行期标识（如 worker_id）的场景。

        Returns:
            bool: 是否成功更新
        """
        from .factory import _create_file_handler, LoggerFactory

        with self._config_lock:
            if not self._config or not self._config.file_enabled:
                return False
            self._config.file_path = file_path

        # 遍历已创建的 logger，替换文件 handler
        file_level = self._config.get_file_level()
        file_format = logging.Formatter(self._config.get_format())
        replaced = 0
        for logger in logging.root.manager.loggerDict.values():
            if not isinstance(logger, logging.Logger):
                continue
            for h in list(logger.handlers):
                if isinstance(h, logging.handlers.TimedRotatingFileHandler):
                    try:
                        h.close()
                    except Exception as exc:
                        logging.getLogger("crawlo.logging").debug(
                            "关闭旧日志 handler 失败: %s", exc
                        )
                    logger.removeHandler(h)
                    replaced += 1
            try:
                new_handler = _create_file_handler(self._config)
                new_handler.setFormatter(file_format)
                new_handler.setLevel(getattr(logging, file_level.upper(), logging.INFO))
                logger.addHandler(new_handler)
            except (OSError, PermissionError) as exc:
                logging.getLogger("crawlo.logging").warning(
                    "动态更新日志文件失败: %s", exc
                )

        # 清空缓存，后续 get_logger 使用新配置
        LoggerFactory.refresh_loggers(self._config)
        return True

    def cleanup_old_logs(self, log_dir: str = None, days: int = 1) -> int:
        """Clean up log files older than specified days

        Args:
            log_dir: Log directory path, defaults to configured directory
            days: Retention days, default 1 day

        Returns:
            int: Number of deleted files
        """
        # Safety check: prevent deleting files in current directory
        if not log_dir or log_dir == '.':
            with self._config_lock:
                if self._config and self._config.file_path:
                    parent = Path(self._config.file_path).parent
                    log_dir = str(parent) if parent.name else 'logs'
                else:
                    log_dir = 'logs'

        if not os.path.exists(log_dir):
            return 0

        cutoff_time = time.time() - (days * self.SECONDS_PER_DAY)
        deleted_count = 0

        # Match timestamp in filename: ofweek_standalone_20260505_171709.log
        time_pattern = re.compile(r'_(\d{8})_\d{6}\.log$')

        try:
            for filename in os.listdir(log_dir):
                if not filename.endswith('.log'):
                    continue

                file_path = os.path.join(log_dir, filename)
                if not os.path.isfile(file_path):
                    continue

                # Prefer filename timestamp, fallback to file modification time
                match = time_pattern.search(filename)
                if match:
                    try:
                        # Use local timezone to parse filename timestamp
                        file_date = datetime.strptime(match.group(1), '%Y%m%d')
                        local_tz = datetime.now().astimezone().tzinfo
                        file_date = file_date.replace(tzinfo=local_tz)
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
                        self.logger.warning(
                            f"Failed to delete log file: {file_path}, error: {e}"
                        )
        except PermissionError as e:
            self.logger.warning(
                f"Permission denied cleaning logs: {log_dir}, error: {e}"
            )
        except Exception as e:
            self.logger.warning(f"Failed to clean old logs: {e}")

        if deleted_count > 0:
            self.logger.info(
                f"Cleaned {deleted_count} log file(s) older than {days} day(s)"
            )

        return deleted_count


def worker_log_path(file_path: str, worker_id: str) -> str:
    """在日志文件名中追加 worker_id（多 Worker 日志隔离）。

    规则：``logs/app.log`` + ``worker-1`` -> ``logs/app.worker-1.log``；
    无扩展名时直接追加：``logs/app`` -> ``logs/app.worker-1``。
    仅追加进文件名，不改变目录与扩展名。
    """
    base, ext = os.path.splitext(file_path)
    return f"{base}.{worker_id}{ext}"


_log_manager: Optional[LogManager] = None


def _get_log_manager() -> LogManager:
    """获取全局 LogManager 单例（模块级，避免循环导入：日志是最底层的系统，不依赖 ApplicationContext）"""
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager()
    return _log_manager


# Module-level convenience functions
def configure(settings=None, **kwargs) -> LogConfig:
    """Configure log system"""
    return _get_log_manager().configure(settings, **kwargs)


def is_configured() -> bool:
    """Check if configured"""
    return _get_log_manager().is_configured


def get_config() -> Optional[LogConfig]:
    """Get current configuration"""
    return _get_log_manager().config


def reset():
    """Reset configuration"""
    _get_log_manager().reset()
