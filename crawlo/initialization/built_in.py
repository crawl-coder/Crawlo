#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
内置初始化器 - 提供框架核心组件的初始化实现
"""

import time
from typing import TYPE_CHECKING

from .registry import BaseInitializer, register_initializer
from .phases import InitializationPhase, PhaseResult
from .context import InitializationContext

if TYPE_CHECKING:
    from crawlo.logging import LogConfig


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
            
            # 获取日志配置
            log_config = self._get_log_config(context)
            
            # 确保日志目录存在
            if log_config and log_config.file_path and log_config.file_enabled:
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
    
    def _get_log_config(self, context: InitializationContext) -> 'LogConfig | None':
        """
        获取日志配置
        
        Args:
            context: 初始化上下文
            
        Returns:
            LogConfig: 日志配置对象
        """
        # 导入日志配置类
        from crawlo.logging import LogConfig
        from crawlo.utils.config_manager import ConfigUtils
        
        # 按优先级获取配置：自定义配置 > 上下文配置 > 项目配置 > 默认配置
        config_sources = [
            context.custom_settings,
            context.settings,
            self._load_project_config()
        ]
        
        # 遍历配置源
        for config_source in config_sources:
            if config_source and ConfigUtils.has_config_prefix(config_source, 'LOG_'):
                log_config = self._create_log_config_from_source(config_source)
                if log_config:
                    return log_config
        
        # 使用默认配置
        return LogConfig()
    
    def _create_log_config_from_source(self, config_source) -> 'LogConfig | None':
        """
        从配置源创建日志配置
        
        Args:
            config_source: 配置源
            
        Returns:
            LogConfig: 日志配置对象，如果配置源无效则返回None
        """
        # 导入日志配置类
        from crawlo.logging import LogConfig
        from crawlo.utils.config_manager import ConfigUtils
        
        # 检查配置源是否有效
        if not config_source:
            return None
            
        # 检查是否有日志相关配置
        if not ConfigUtils.has_config_prefix(config_source, 'LOG_'):
            return None
            
        # 从配置源获取日志配置
        log_level = ConfigUtils.get_config_value([config_source], 'LOG_LEVEL', 'INFO')
        log_file = ConfigUtils.get_config_value([config_source], 'LOG_FILE')
        log_format = ConfigUtils.get_config_value([config_source], 'LOG_FORMAT', '%(asctime)s - [%(name)s] - %(levelname)s: %(message)s')
        log_encoding = ConfigUtils.get_config_value([config_source], 'LOG_ENCODING', 'utf-8')
        log_max_bytes = ConfigUtils.get_config_value([config_source], 'LOG_MAX_BYTES', 10 * 1024 * 1024, int)
        log_backup_count = ConfigUtils.get_config_value([config_source], 'LOG_BACKUP_COUNT', 5, int)
        log_console_enabled = ConfigUtils.get_config_value([config_source], 'LOG_CONSOLE_ENABLED', True, bool)
        log_file_enabled = ConfigUtils.get_config_value([config_source], 'LOG_FILE_ENABLED', True, bool)
        
        # 创建日志配置
        return LogConfig(
            level=log_level,
            format=log_format,
            encoding=log_encoding,
            file_path=log_file,
            max_bytes=log_max_bytes,
            backup_count=log_backup_count,
            console_enabled=log_console_enabled,
            file_enabled=log_file_enabled
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
                        from crawlo.utils.config_manager import ConfigUtils
                        project_config = ConfigUtils.merge_config_sources([settings_module])
                        
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
            
            # 如果上下文中已有设置，则使用它作为基础配置
            if context.settings:
                # 使用用户传递的设置作为基础配置
                settings = context.settings
                # 加载项目配置并合并
                project_settings = _load_project_settings(context.custom_settings)
                # 合并配置，用户配置优先
                settings.update_attributes(project_settings.attributes)
            else:
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


class CoreComponentsInitializer(BaseInitializer):
    """核心组件初始化器"""
    
    def __init__(self):
        super().__init__(InitializationPhase.CORE_COMPONENTS)
    
    def initialize(self, context: InitializationContext) -> PhaseResult:
        """初始化核心组件"""
        start_time = time.time()
        
        try:
            # 在核心组件初始化阶段，大多数组件需要crawler参数
            # 因此我们只初始化那些完全独立的组件
            # 或者只记录需要初始化的组件类型，实际初始化在crawler创建时进行
            
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
    
# 注意：核心组件需要crawler参数，不能在此阶段初始化
        # 实际初始化将在crawler创建时进行


class ExtensionsInitializer(BaseInitializer):
    """扩展组件初始化器"""
    
    def __init__(self):
        super().__init__(InitializationPhase.EXTENSIONS)
    
    def initialize(self, context: InitializationContext) -> PhaseResult:
        """初始化扩展组件"""
        start_time = time.time()
        
        try:
            # 初始化扩展组件
            self._initialize_extensions(context)
            
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
    
    def _initialize_extensions(self, context: InitializationContext):
        """初始化扩展组件"""
        try:
            # 获取扩展配置
            extensions = []
            if context.settings:
                extensions = context.settings.get('EXTENSIONS', [])
            elif context.custom_settings:
                extensions = context.custom_settings.get('EXTENSIONS', [])
            
            # 初始化每个扩展
            initialized_extensions = []
            for extension_path in extensions:
                try:
                    from crawlo.utils.misc import load_object
                    extension_class = load_object(extension_path)
                    extension_instance = extension_class()
                    initialized_extensions.append(extension_instance)
                except Exception as e:
                    if context.settings and context.settings.get('EXTENSIONS_STRICT', False):
                        raise
                    else:
                        # 非严格模式下记录警告但继续
                        context.add_warning(f"Failed to initialize extension {extension_path}: {e}")
            
            # 存储到上下文
            context.add_shared_data('extensions', initialized_extensions)
        except Exception as e:
            context.add_error(f"Failed to initialize extensions: {e}")
            raise


class FrameworkStartupLogger(BaseInitializer):
    """框架启动日志记录器"""
    
    def __init__(self):
        # 使用新的FRAMEWORK_STARTUP_LOG阶段
        super().__init__(InitializationPhase.FRAMEWORK_STARTUP_LOG)
    
    def initialize(self, context: InitializationContext) -> PhaseResult:
        """记录框架启动日志"""
        start_time = time.time()
        
        try:
            # 获取框架logger
            from crawlo.logging import get_logger
            logger = get_logger('crawlo.framework')
            
            # 获取框架版本
            version = self._get_framework_version()
            
            # 记录框架启动信息（符合规范要求）
            logger.info(f"Crawlo Framework Started {version}")
            
            # 获取运行模式
            run_mode = "unknown"
            if context.settings:
                run_mode = context.settings.get('RUN_MODE', 'standalone')
            logger.info(f"Run mode: {run_mode}")
            
            # 注意：爬虫名称信息将在实际启动爬虫时记录，而不是在框架初始化时
            
            return self._create_result(
                success=True,
                duration=time.time() - start_time,
                artifacts={}
            )
            
        except Exception as e:
            # 即使日志记录失败，也不应该影响框架初始化
            return self._create_result(
                success=True,  # 不影响初始化成功与否
                duration=time.time() - start_time,
                error=e
            )
    
    def _get_framework_version(self):
        """获取框架版本"""
        try:
            from crawlo import __version__
            return __version__
        except Exception:
            return "unknown"


def register_built_in_initializers():
    """注册所有内置初始化器"""
    register_initializer(LoggingInitializer())
    register_initializer(SettingsInitializer())
    register_initializer(CoreComponentsInitializer())
    register_initializer(ExtensionsInitializer())
    register_initializer(FrameworkStartupLogger())  # 添加框架启动日志记录器