import os
from logging import (
    Formatter,
    StreamHandler,
    FileHandler,
    Logger,
    DEBUG,
    INFO,
    getLevelName,
)
# 导入日志轮转处理器
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

LOG_FORMAT = '%(asctime)s - [%(name)s] - %(levelname)s: %(message)s'


class LoggerManager:
    logger_cache = {}
    _default_filename = None
    _default_level = DEBUG  # 设置为最低级别，由handler控制实际输出
    _default_file_level = INFO
    _default_console_level = INFO
    _default_log_format = LOG_FORMAT
    _default_encoding = 'utf-8'
    # 添加日志轮转相关默认配置
    _default_log_max_bytes = 10 * 1024 * 1024  # 10MB
    _default_log_backup_count = 5
    _default_log_when = 'midnight'
    _default_log_interval = 1
    _default_log_use_rotation = False
    _default_log_rotation_type = 'size'  # 'size' or 'time'
    _default_log_rotation_suffix = None  # 轮转文件后缀格式

    @classmethod
    def _to_level(cls, level):
        """安全转换为日志级别 int"""
        if level is None:
            return INFO
        if isinstance(level, int):
            return level
        if isinstance(level, str):
            # 使用logging模块内置的级别转换
            level_value = getLevelName(level.upper())
            # getLevelName在无效级别时返回字符串，我们需要返回数字
            if isinstance(level_value, int):
                return level_value
            else:
                return INFO
        if hasattr(level, 'get'):  # 如 SettingManager 或 dict
            lv = level.get('LOG_LEVEL')
            if isinstance(lv, int):
                return lv
            if isinstance(lv, str):
                level_value = getLevelName(lv.upper())
                if isinstance(level_value, int):
                    return level_value
                else:
                    return INFO
        return INFO

    @classmethod
    def configure(cls, settings=None, **kwargs):
        """
        使用 settings 对象或关键字参数配置日志
        """
        # 优先使用 settings，否则用 kwargs
        get_val = settings.get if hasattr(settings, 'get') else (lambda k, d=None: kwargs.get(k, d))

        filename = get_val('LOG_FILE')
        level = get_val('LOG_LEVEL', 'DEBUG')  # 默认为DEBUG级别
        file_level = get_val('LOG_FILE_LEVEL', 'INFO')
        console_level = get_val('LOG_CONSOLE_LEVEL', 'INFO')  # 保留LOG_CONSOLE_LEVEL配置
        log_format = get_val('LOG_FORMAT', LOG_FORMAT)
        encoding = get_val('LOG_ENCODING', 'utf-8')
        # 获取日志轮转配置
        use_rotation = get_val('LOG_USE_ROTATION', False)
        rotation_type = get_val('LOG_ROTATION_TYPE', 'size')
        max_bytes = get_val('LOG_MAX_BYTES', cls._default_log_max_bytes)
        backup_count = get_val('LOG_BACKUP_COUNT', cls._default_log_backup_count)
        when = get_val('LOG_WHEN', cls._default_log_when)
        interval = get_val('LOG_INTERVAL', cls._default_log_interval)
        rotation_suffix = get_val('LOG_ROTATION_SUFFIX', cls._default_log_rotation_suffix)  # 轮转文件后缀

        cls._default_filename = filename
        cls._default_level = cls._to_level(level)
        cls._default_file_level = cls._to_level(file_level)
        cls._default_console_level = cls._to_level(console_level)
        cls._default_log_format = log_format
        cls._default_encoding = encoding
        # 设置日志轮转配置
        cls._default_log_use_rotation = use_rotation
        cls._default_log_rotation_type = rotation_type
        cls._default_log_max_bytes = max_bytes
        cls._default_log_backup_count = backup_count
        cls._default_log_when = when
        cls._default_log_interval = interval
        cls._default_log_rotation_suffix = rotation_suffix
        
        # 移除对根日志记录器级别的修改，避免副作用

    @classmethod
    def get_logger(cls, name='default', level=None, filename=None):
        """
        简化接口，只暴露必要参数
        """
        # 确定最终参数
        # 如果传入了level参数，则使用它，否则使用默认级别
        if level is not None:
            final_level = cls._to_level(level)
        else:
            # Logger级别设置为DEBUG（最低级别），由handler控制实际输出
            final_level = DEBUG
            
        final_filename = filename if filename is not None else cls._default_filename

        # 安全的字符串化 key，避免任何 unhashable 类型
        key_parts = [
            name,
            str(final_level),
            final_filename or 'no_file',
        ]
        key = '|'.join(key_parts)  # 如 "my_spider|20|logs/app.log"

        if key in cls.logger_cache:
            # 更新logger级别
            cls.logger_cache[key].setLevel(final_level)
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

                # 检查是否启用日志轮转
                if cls._default_log_use_rotation:
                    if cls._default_log_rotation_type == 'size':
                        # 使用大小轮转
                        fh = RotatingFileHandler(
                            final_filename, 
                            maxBytes=cls._default_log_max_bytes,
                            backupCount=cls._default_log_backup_count,
                            encoding=cls._default_encoding
                        )
                    else:
                        # 使用时间轮转
                        fh = TimedRotatingFileHandler(
                            final_filename,
                            when=cls._default_log_when,
                            interval=cls._default_log_interval,
                            backupCount=cls._default_log_backup_count,
                            encoding=cls._default_encoding
                        )
                        # 如果提供了自定义后缀格式，则设置
                        if cls._default_log_rotation_suffix:
                            fh.suffix = cls._default_log_rotation_suffix
                else:
                    # 使用普通文件处理器（默认行为，会追加到文件）
                    fh = FileHandler(final_filename, mode='a', encoding=cls._default_encoding)
                    
                fh.setFormatter(formatter)
                fh.setLevel(cls._default_file_level)
                _logger.addHandler(fh)
            except (PermissionError, FileNotFoundError) as e:
                print(f"[Logger] 无法创建日志文件 {final_filename}: {e}")
            except Exception as e:
                print(f"[Logger] 创建日志文件时发生未知错误 {final_filename}: {e}")

        cls.logger_cache[key] = _logger
        return _logger


# 全局快捷函数
get_logger = LoggerManager.get_logger