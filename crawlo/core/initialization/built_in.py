#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
内置初始化器
============
5 个内置初始化器 + register_built_in_initializers:
- LoggingInitializer: 日志系统
- SettingsInitializer: 配置系统
- CoreComponentsInitializer: 核心组件
- ExtensionsInitializer: 扩展组件
- FrameworkStartupLogger: 框架启动日志
"""
import importlib as _importlib
import os as _os
import sys as _sys
import time as _time
from typing import Optional

from crawlo.core.initialization.context import InitializationContext
from crawlo.core.initialization.phases import InitializationPhase
from crawlo.core.initialization.registry import BaseInitializer, register_initializer
from crawlo.logging import configure_logging, get_logger, LogConfig, LoggerFactory
from crawlo.utils.misc import ConfigUtils, load_object


class LoggingInitializer(BaseInitializer):
    """日志系统初始化器"""

    def __init__(self):
        super().__init__(InitializationPhase.LOGGING)

    def initialize(self, context: InitializationContext):
        start_time = _time.time()

        try:
            log_config = self._get_log_config(context)

            if log_config and log_config.file_path and log_config.file_enabled:
                log_dir = _os.path.dirname(log_config.file_path)
                if log_dir and not _os.path.exists(log_dir):
                    _os.makedirs(log_dir, exist_ok=True)

            configure_logging(log_config)

            context.add_shared_data('log_config', log_config)

            framework_logger = get_logger('crawlo.framework')
            context.add_shared_data('framework_logger', framework_logger)

            return self._create_result(
                success=True,
                duration=_time.time() - start_time,
                artifacts={'log_config': log_config}
            )

        except Exception as e:
            return self._create_result(
                success=False,
                duration=_time.time() - start_time,
                error=e
            )

    def _get_log_config(self, context: InitializationContext) -> 'LogConfig':
        config_sources = [
            context.custom_settings,
            context.settings,
            self._load_project_config()
        ]

        for config_source in config_sources:
            if config_source and ConfigUtils.has_config_prefix(config_source, 'LOG_'):
                log_config = self._create_log_config_from_source(config_source)
                if log_config:
                    return log_config

        return LogConfig()

    def _create_log_config_from_source(self, config_source) -> Optional['LogConfig']:
        if not config_source:
            return None

        if not ConfigUtils.has_config_prefix(config_source, 'LOG_'):
            return None

        log_level = ConfigUtils.get_config_value([config_source], 'LOG_LEVEL', 'INFO')
        log_file = ConfigUtils.get_config_value([config_source], 'LOG_FILE')
        # LOG_FILE 仅接受字符串；dict/list 等非字符串值丢弃，
        # 避免 str(dict) 被当作日志文件路径导致创建垃圾文件
        if not isinstance(log_file, str):
            log_file = None
        log_format = ConfigUtils.get_config_value([config_source], 'LOG_FORMAT', '%(asctime)s - [%(name)s] - %(levelname)s: %(message)s')
        log_encoding = ConfigUtils.get_config_value([config_source], 'LOG_ENCODING', 'utf-8')
        log_console_enabled = ConfigUtils.get_config_value([config_source], 'LOG_CONSOLE_ENABLED', True, bool)
        log_file_enabled = ConfigUtils.get_config_value([config_source], 'LOG_FILE_ENABLED', True, bool)

        return LogConfig(
            level=log_level,
            format=log_format,
            encoding=log_encoding,
            file_path=log_file,
            console_enabled=log_console_enabled,
            file_enabled=log_file_enabled
        )

    def _load_project_config(self):
        try:
            from crawlo.project import read_crawlo_cfg  # noqa: WPS433

            current_path = _os.getcwd()
            checked_paths = set()
            path = current_path

            while path not in checked_paths:
                checked_paths.add(path)

                cfg_file = _os.path.join(path, "crawlo.cfg")
                settings_module_path = read_crawlo_cfg(cfg_file)

                if settings_module_path:
                    if path not in _sys.path:
                        _sys.path.insert(0, path)

                    settings_module = _importlib.import_module(settings_module_path)
                    project_config = ConfigUtils.merge_config_sources([settings_module])

                    return project_config

                parent = _os.path.dirname(path)
                if parent == path:
                    break
                path = parent

            return {}

        except Exception:
            return {}


class SettingsInitializer(BaseInitializer):
    """配置系统初始化器"""

    def __init__(self):
        super().__init__(InitializationPhase.SETTINGS)

    def initialize(self, context: InitializationContext):
        start_time = _time.time()

        try:
            from crawlo.project import _load_project_settings  # noqa: WPS433

            if context.settings:
                settings = context.settings
                project_settings = _load_project_settings(context.custom_settings)
                settings.update_attributes(project_settings.attributes)
            else:
                settings = _load_project_settings(context.custom_settings)

            context.settings = settings
            context.add_shared_data('settings', settings)

            return self._create_result(
                success=True,
                duration=_time.time() - start_time,
                artifacts={'settings': settings}
            )

        except Exception as e:
            return self._create_result(
                success=False,
                duration=_time.time() - start_time,
                error=e
            )


class CoreComponentsInitializer(BaseInitializer):
    """Core components initializer"""

    def __init__(self):
        super().__init__(InitializationPhase.CORE_COMPONENTS)

    def initialize(self, context: InitializationContext):
        start_time = _time.time()

        try:
            logger = context.get_shared_data('framework_logger')
            if logger:
                logger.debug("Core components initialization deferred to crawler creation")

            return self._create_result(
                success=True,
                duration=_time.time() - start_time,
                artifacts={'note': 'Core components initialized during crawler creation'}
            )

        except Exception as e:
            return self._create_result(
                success=False,
                duration=_time.time() - start_time,
                error=e
            )

    def _get_spider_module_initializer_config(self, context: InitializationContext) -> dict:
        return ConfigUtils.get_config_value(
            [context.settings, context.custom_settings],
            'SPIDER_MODULE_INITIALIZER',
            {}
        )

    def _get_custom_downloader_path(self, context: InitializationContext) -> Optional[str]:
        custom_downloader_path = ConfigUtils.get_config_value(
            [context.settings, context.custom_settings],
            'CUSTOM_DOWNLOADER',
            None
        )
        if custom_downloader_path:
            return load_object(custom_downloader_path)
        return None


class ExtensionsInitializer(BaseInitializer):
    """扩展组件初始化器"""

    def __init__(self):
        super().__init__(InitializationPhase.EXTENSIONS)

    def initialize(self, context: InitializationContext):
        start_time = _time.time()

        try:
            self._initialize_extensions(context)

            return self._create_result(
                success=True,
                duration=_time.time() - start_time,
                artifacts={}
            )

        except Exception as e:
            return self._create_result(
                success=False,
                duration=_time.time() - start_time,
                error=e
            )

    def _initialize_extensions(self, context: InitializationContext):
        try:
            extensions = []
            if context.settings:
                extensions = context.settings.get('EXTENSIONS', [])
            elif context.custom_settings:
                extensions = context.custom_settings.get('EXTENSIONS', [])

            initialized_extensions = []
            for extension_path in extensions:
                try:
                    extension_class = load_object(extension_path)
                    extension_instance = extension_class()
                    initialized_extensions.append(extension_instance)
                except Exception as e:
                    if context.settings and context.settings.get('EXTENSIONS_STRICT', False):
                        raise
                    else:
                        context.add_warning(f"Failed to initialize extension {extension_path}: {e}")

            context.add_shared_data('extensions', initialized_extensions)
        except Exception as e:
            context.add_error(f"Failed to initialize extensions: {e}")
            raise


class FrameworkStartupLogger(BaseInitializer):
    """框架启动日志记录器"""

    def __init__(self):
        super().__init__(InitializationPhase.FRAMEWORK_STARTUP_LOG)

    def initialize(self, context: InitializationContext):
        start_time = _time.time()

        try:
            if context.settings:
                configure_logging(context.settings)
                LoggerFactory.clear_cache()

            logger = get_logger('crawlo.framework')
            version = self._get_framework_version()
            logger.info(f"Crawlo Framework Started {version}")

            run_mode = "unknown"
            queue_type = "unknown"
            if context.settings:
                run_mode = context.settings.get('RUN_MODE', 'standalone')
                queue_type = context.settings.get('QUEUE_TYPE', 'memory')
                if queue_type == 'auto':
                    queue_type = 'auto-detect'
            logger.info(f"Run mode: {run_mode}, Queue type: {queue_type}")

            return self._create_result(
                success=True,
                duration=_time.time() - start_time,
                artifacts={}
            )

        except Exception as e:
            return self._create_result(
                success=True,
                duration=_time.time() - start_time,
                error=e
            )

    def _get_framework_version(self):
        try:
            from crawlo import __version__  # noqa: WPS433
            return __version__
        except Exception:
            return "unknown"


def register_built_in_initializers():
    """注册所有内置初始化器"""
    register_initializer(LoggingInitializer())
    register_initializer(SettingsInitializer())
    register_initializer(CoreComponentsInitializer())
    register_initializer(ExtensionsInitializer())
    register_initializer(FrameworkStartupLogger())


__all__ = [
    "LoggingInitializer",
    "SettingsInitializer",
    "CoreComponentsInitializer",
    "ExtensionsInitializer",
    "FrameworkStartupLogger",
    "register_built_in_initializers",
]
