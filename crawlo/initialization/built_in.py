#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
内置初始化器 - 提供框架核心组件的初始化实现
"""

import time
from .registry import BaseInitializer, register_initializer
from .phases import InitializationPhase, PhaseResult
from .context import InitializationContext


class LoggingInitializer(BaseInitializer):
    """日志系统初始化器"""
    
    def __init__(self):
        super().__init__(InitializationPhase.LOGGING)
    
    def initialize(self, context: InitializationContext) -> PhaseResult:
        """初始化日志系统"""
        start_time = time.time()
        
        try:
            # 导入日志模块
            from crawlo.logging import configure_logging, LogConfig
            
            # 优先从自定义配置获取日志配置，然后尝试加载项目配置，最后使用默认配置
            log_config = None
            
            # 首先检查自定义配置
            if context.custom_settings:
                # 从自定义配置中获取日志配置
                custom_settings = context.custom_settings
                log_level = custom_settings.get('LOG_LEVEL', 'INFO')
                log_file = custom_settings.get('LOG_FILE')
                log_format = custom_settings.get('LOG_FORMAT', '%(asctime)s - [%(name)s] - %(levelname)s: %(message)s')
                log_encoding = custom_settings.get('LOG_ENCODING', 'utf-8')
                log_max_bytes = custom_settings.get('LOG_MAX_BYTES', 10 * 1024 * 1024)
                log_backup_count = custom_settings.get('LOG_BACKUP_COUNT', 5)
                log_console_enabled = custom_settings.get('LOG_CONSOLE_ENABLED', True)
                log_file_enabled = custom_settings.get('LOG_FILE_ENABLED', True)
                
                # 创建日志配置
                log_config = LogConfig(
                    level=log_level,
                    format=log_format,
                    encoding=log_encoding,
                    file_path=log_file,
                    max_bytes=log_max_bytes,
                    backup_count=log_backup_count,
                    console_enabled=log_console_enabled,
                    file_enabled=log_file_enabled
                )
            
            # 如果没有自定义配置或配置不完整，尝试从context.settings获取配置
            if not log_config and context.settings:
                settings = context.settings
                if hasattr(settings, 'get'):
                    log_level = settings.get('LOG_LEVEL', 'INFO')
                    log_file = settings.get('LOG_FILE')
                    log_format = settings.get('LOG_FORMAT', '%(asctime)s - [%(name)s] - %(levelname)s: %(message)s')
                    log_encoding = settings.get('LOG_ENCODING', 'utf-8')
                    log_max_bytes = settings.get('LOG_MAX_BYTES', 10 * 1024 * 1024)
                    log_backup_count = settings.get('LOG_BACKUP_COUNT', 5)
                    log_console_enabled = settings.get('LOG_CONSOLE_ENABLED', True)
                    log_file_enabled = settings.get('LOG_FILE_ENABLED', True)
                    
                    # 创建日志配置
                    log_config = LogConfig(
                        level=log_level,
                        format=log_format,
                        encoding=log_encoding,
                        file_path=log_file,
                        max_bytes=log_max_bytes,
                        backup_count=log_backup_count,
                        console_enabled=log_console_enabled,
                        file_enabled=log_file_enabled
                    )
            
            # 如果仍然没有配置，尝试自动加载项目配置
            if not log_config:
                project_config = self._load_project_config()
                if project_config and project_config.get('LOG_FILE'):
                    log_level = project_config.get('LOG_LEVEL', 'INFO')
                    log_file = project_config.get('LOG_FILE')
                    log_format = project_config.get('LOG_FORMAT', '%(asctime)s - [%(name)s] - %(levelname)s: %(message)s')
                    log_encoding = project_config.get('LOG_ENCODING', 'utf-8')
                    log_max_bytes = project_config.get('LOG_MAX_BYTES', 10 * 1024 * 1024)
                    log_backup_count = project_config.get('LOG_BACKUP_COUNT', 5)
                    log_console_enabled = project_config.get('LOG_CONSOLE_ENABLED', True)
                    log_file_enabled = project_config.get('LOG_FILE_ENABLED', True)
                    
                    # 创建日志配置
                    log_config = LogConfig(
                        level=log_level,
                        format=log_format,
                        encoding=log_encoding,
                        file_path=log_file,
                        max_bytes=log_max_bytes,
                        backup_count=log_backup_count,
                        console_enabled=log_console_enabled,
                        file_enabled=log_file_enabled
                    )
            
            # 如果仍然没有配置，使用默认配置
            if not log_config:
                log_config = LogConfig()
            
            # 确保日志目录存在
            if log_config.file_path and log_config.file_enabled:
                import os
                log_dir = os.path.dirname(log_config.file_path)
                if log_dir and not os.path.exists(log_dir):
                    os.makedirs(log_dir, exist_ok=True)
            
            # 配置日志系统
            configure_logging(log_config)
            
            # 存储到共享数据
            context.add_shared_data('log_config', log_config)
            
            # 创建框架logger
            from crawlo.logging import get_logger
            framework_logger = get_logger('crawlo.framework')
            context.add_shared_data('framework_logger', framework_logger)
            
            return self._create_result(
                success=True,
                duration=time.time() - start_time,
                artifacts={'log_config': log_config}
            )
            
        except Exception as e:
            return self._create_result(
                success=False,
                duration=time.time() - start_time,
                error=e
            )
    
    def _load_project_config(self):
        """
        自动加载项目配置以获取日志设置
        """
        try:
            # 查找项目根目录
            import os
            import sys
            import configparser
            
            current_path = os.getcwd()
            
            # 向上查找直到找到crawlo.cfg
            checked_paths = set()
            path = current_path
            
            while path not in checked_paths:
                checked_paths.add(path)
                
                # 检查crawlo.cfg
                cfg_file = os.path.join(path, "crawlo.cfg")
                if os.path.exists(cfg_file):
                    # 读取配置文件
                    config_parser = configparser.ConfigParser()
                    config_parser.read(cfg_file, encoding="utf-8")
                    
                    if config_parser.has_section("settings") and config_parser.has_option("settings", "default"):
                        # 获取settings模块路径
                        settings_module_path = config_parser.get("settings", "default")
                        
                        # 添加项目根目录到Python路径
                        if path not in sys.path:
                            sys.path.insert(0, path)
                        
                        # 导入项目配置模块
                        import importlib
                        settings_module = importlib.import_module(settings_module_path)
                        
                        # 创建配置字典
                        project_config = {}
                        for key in dir(settings_module):
                            if key.isupper():
                                project_config[key] = getattr(settings_module, key)
                        
                        return project_config
                    
                # 向上一级目录
                parent = os.path.dirname(path)
                if parent == path:
                    break
                path = parent
            
            return {}
            
        except Exception as e:
            return {}


class SettingsInitializer(BaseInitializer):
    """配置系统初始化器"""
    
    def __init__(self):
        super().__init__(InitializationPhase.SETTINGS)
    
    def initialize(self, context: InitializationContext) -> PhaseResult:
        """初始化配置系统"""
        start_time = time.time()
        
        try:
            # 导入配置管理器
            from crawlo.settings.setting_manager import SettingManager
            from crawlo.project import _load_project_settings
            
            # 创建配置管理器并加载项目配置
            settings = _load_project_settings(context.custom_settings)
            
            # 存储到上下文
            context.settings = settings
            context.add_shared_data('settings', settings)
            
            return self._create_result(
                success=True,
                duration=time.time() - start_time,
                artifacts={'settings': settings}
            )
            
        except Exception as e:
            return self._create_result(
                success=False,
                duration=time.time() - start_time,
                error=e
            )


# 添加缺失的初始化器类
class CoreComponentsInitializer(BaseInitializer):
    """核心组件初始化器"""
    
    def __init__(self):
        super().__init__(InitializationPhase.CORE_COMPONENTS)
    
    def initialize(self, context: InitializationContext) -> PhaseResult:
        """初始化核心组件"""
        start_time = time.time()
        
        try:
            # 这里可以添加核心组件的初始化逻辑
            # 例如：初始化调度器、下载器、管道管理器等
            
            return self._create_result(
                success=True,
                duration=time.time() - start_time,
                artifacts={}
            )
            
        except Exception as e:
            return self._create_result(
                success=False,
                duration=time.time() - start_time,
                error=e
            )


class ExtensionsInitializer(BaseInitializer):
    """扩展组件初始化器"""
    
    def __init__(self):
        super().__init__(InitializationPhase.EXTENSIONS)
    
    def initialize(self, context: InitializationContext) -> PhaseResult:
        """初始化扩展组件"""
        start_time = time.time()
        
        try:
            # 这里可以添加扩展组件的初始化逻辑
            # 例如：加载和初始化扩展模块
            
            return self._create_result(
                success=True,
                duration=time.time() - start_time,
                artifacts={}
            )
            
        except Exception as e:
            return self._create_result(
                success=False,
                duration=time.time() - start_time,
                error=e
            )


def register_built_in_initializers():
    """注册所有内置初始化器"""
    register_initializer(LoggingInitializer())
    register_initializer(SettingsInitializer())
    register_initializer(CoreComponentsInitializer())
    register_initializer(ExtensionsInitializer())