# -*- coding: UTF-8 -*-
"""
日志管理器：安全版本，使用字符串化 key 避免 unhashable 问题
"""
import os
from logging import (
    Formatter,
    StreamHandler,
    FileHandler,
    Logger,
    DEBUG,
    INFO,
    WARNING,
    ERROR,
    CRITICAL,
)

LOG_FORMAT = '%(asctime)s - [%(name)s] - %(levelname)s： %(message)s'


class LoggerManager:
    logger_cache = {}
    _default_filename = None
    _default_level = INFO
    _default_file_level = INFO
    _default_console_level = INFO
    _default_log_format = LOG_FORMAT
    _default_encoding = 'utf-8'

    _level_map = {
        'DEBUG': DEBUG,
        'INFO': INFO,
        'WARNING': WARNING,
        'ERROR': ERROR,
        'CRITICAL': CRITICAL,
    }

    @classmethod
    def _to_level(cls, level):
        """安全转换为日志级别 int"""
        if level is None:
            return INFO
        if isinstance(level, int):
            return level
        if isinstance(level, str):
            return cls._level_map.get(level.upper(), INFO)
        if hasattr(level, 'get'):  # 如 SettingManager 或 dict
            lv = level.get('LOG_LEVEL')
            if isinstance(lv, int):
                return lv
            if isinstance(lv, str):
                return cls._level_map.get(lv.upper(), INFO)
        return INFO

    @classmethod
    def configure(cls, settings=None, **kwargs):
        """
        使用 settings 对象或关键字参数配置日志
        """
        # 优先使用 settings，否则用 kwargs
        get_val = settings.get if hasattr(settings, 'get') else (lambda k, d=None: kwargs.get(k, d))

        filename = get_val('LOG_FILE')
        level = get_val('LOG_LEVEL', 'INFO')
        file_level = get_val('LOG_FILE_LEVEL', level)
        console_level = get_val('LOG_CONSOLE_LEVEL', level)
        log_format = get_val('LOG_FORMAT', LOG_FORMAT)
        encoding = get_val('LOG_ENCODING', 'utf-8')

        cls._default_filename = filename
        cls._default_level = cls._to_level(level)
        cls._default_file_level = cls._to_level(file_level)
        cls._default_console_level = cls._to_level(console_level)
        cls._default_log_format = log_format
        cls._default_encoding = encoding

    @classmethod
    def get_logger(cls, name='default', level=None, filename=None):
        """
        简化接口，只暴露必要参数
        """
        # 确定最终参数
        final_level = cls._to_level(level) if level is not None else cls._default_level
        final_filename = filename if filename is not None else cls._default_filename

        # ✅ 安全的字符串化 key，避免任何 unhashable 类型
        key_parts = [
            name,
            str(final_level),
            final_filename or 'no_file',
        ]
        key = '|'.join(key_parts)  # 如 "my_spider|20|logs/app.log"

        if key in cls.logger_cache:
            return cls.logger_cache[key]

        # 创建 logger
        _logger = Logger(name=name)
        _logger.setLevel(final_level)

        formatter = Formatter(cls._default_log_format)

        # 控制台
        if cls._default_console_level is not False:
            ch = StreamHandler()
            ch.setFormatter(formatter)
            ch.setLevel(cls._default_console_level)
            _logger.addHandler(ch)

        # 文件
        if final_filename:
            try:
                log_dir = os.path.dirname(final_filename)
                if log_dir and not os.path.exists(log_dir):
                    os.makedirs(log_dir, exist_ok=True)

                fh = FileHandler(final_filename, encoding=cls._default_encoding)
                fh.setFormatter(formatter)
                fh.setLevel(cls._default_file_level)
                _logger.addHandler(fh)
            except Exception as e:
                print(f"[Logger] 无法创建日志文件 {final_filename}: {e}")

        cls.logger_cache[key] = _logger
        return _logger


# 全局快捷函数
get_logger = LoggerManager.get_logger