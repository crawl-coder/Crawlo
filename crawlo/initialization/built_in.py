#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Built-in Initializers - Provide initialization implementations for framework core components
"""

import os
import time
import importlib
from typing import TYPE_CHECKING, Optional

from .registry import BaseInitializer, register_initializer
from .phases import InitializationPhase, PhaseResult
from .context import InitializationContext
from crawlo.logging import configure_logging, get_logger, LogConfig, LoggerFactory
from crawlo.utils.misc import ConfigUtils, load_object


class LoggingInitializer(BaseInitializer):
    """日志系统初始化器"""
    
    def __init__(self):
        super().__init__(InitializationPhase.LOGGING)
    
    def initialize(self, context: InitializationContext) -> PhaseResult:
        """初始化日志系统"""
        start_time = time.time()
        
        try:
            # 导入日志模块（已在顶部导入）
            
            # 获取日志配置（已在顶部导入）
            log_config = self._get_log_config(context)
            
            # 确保日志目录存在
            if log_config and log_config.file_path and log_config.file_enabled:
                # os 已在顶部导入
                log_dir = os.path.dirname(log_config.file_path)
                if log_dir and not os.path.exists(log_dir):
                    os.makedirs(log_dir, exist_ok=True)
            
            # 配置日志系统
            configure_logging(log_config)
            
            # 存储到共享数据
            context.add_shared_data('log_config', log_config)
            
            # 创建框架logger（get_logger 已在顶部导入）
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
    
    def _get_log_config(self, context: InitializationContext) -> LogConfig:
        """
        从配置上下文中提取LogConfig
        
        Args:
            context: 初始化上下文
            
        Returns:
            LogConfig: Log configuration object
        """
        # LogConfig 和 ConfigUtils 已在顶部导入
        
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
    
    def _create_log_config_from_source(self, config_source) -> Optional['LogConfig']:
        """
        Create log configuration from config source
        
        Args:
            config_source: Configuration source
            
        Returns:
            LogConfig: Log configuration object, None if source is invalid
        """
        from crawlo.logging import LogConfig
        from crawlo.utils.misc import ConfigUtils
        
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
        log_console_enabled = ConfigUtils.get_config_value([config_source], 'LOG_CONSOLE_ENABLED', True, bool)
        log_file_enabled = ConfigUtils.get_config_value([config_source], 'LOG_FILE_ENABLED', True, bool)
        
        # 创建日志配置
        return LogConfig(
            level=log_level,
            format=log_format,
            encoding=log_encoding,
            file_path=log_file,
            console_enabled=log_console_enabled,
            file_enabled=log_file_enabled
        )
    
    def _load_project_config(self):
        """
        Automatically load project configuration to retrieve log settings
        """
        try:
            from crawlo.project import read_crawlo_cfg
            from crawlo.utils.misc import ConfigUtils
            
            current_path = os.getcwd()
            
            # 向上查找直到找到crawlo.cfg
            checked_paths = set()
            path = current_path
            
            while path not in checked_paths:
                checked_paths.add(path)
                
                # 检查crawlo.cfg
                cfg_file = os.path.join(path, "crawlo.cfg")
                settings_module_path = read_crawlo_cfg(cfg_file)
                
                if settings_module_path:
                    # Add project root directory to Python path
                    if path not in sys.path:
                        sys.path.insert(0, path)
                    
                    # Import project settings module
                    settings_module = importlib.import_module(settings_module_path)
                    
                    # Create configuration dictionary
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
    """Core components initializer"""
    
    def __init__(self):
        super().__init__(InitializationPhase.CORE_COMPONENTS)
    
    def initialize(self, context: InitializationContext) -> PhaseResult:
        """
        Initialize core components
        
        Note: Most core components require crawler parameter, so they cannot be
        initialized in this phase. Actual initialization will occur when
        the crawler is created. This phase serves as a placeholder.
        """
        start_time = time.time()
        
        try:
            # Log that core components will be initialized later
            logger = context.get_shared_data('framework_logger')
            if logger:
                logger.debug("Core components initialization deferred to crawler creation")
            
            return self._create_result(
                success=True,
                duration=time.time() - start_time,
                artifacts={'note': 'Core components initialized during crawler creation'}
            )
            
        except Exception as e:
            return self._create_result(
                success=False,
                duration=time.time() - start_time,
                error=e
            )
    
    def _get_spider_module_initializer_config(self, context: InitializationContext) -> dict:
        """获取爬虫模块初始化器配置"""
        # ConfigUtils 已在顶部导入
        return ConfigUtils.get_config_value(
            [context.settings, context.custom_settings],
            'SPIDER_MODULE_INITIALIZER',
            {}
        )
    
    def _get_custom_downloader_path(self, context: InitializationContext) -> Optional[str]:
        """获取自定义下载器路径"""
        # load_object 和 ConfigUtils 已在顶部导入
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
        """记录框架启动信息"""
        start_time = time.time()
        
        try:
            # 关键步骤：在记录框架启动日志前，重新配置日志系统
            # 这样确保 LOG_FILE 被正确地应用到所有logger（包括框架logger）
            if context.settings:
                # configure_logging 和 LoggerFactory 已在顶部导入
                # 重新配置日志，这次会正确读取settings中的LOG_FILE
                configure_logging(context.settings)
                # 清除缓存以强制重新创建logger（使其包含新的文件处理器）
                LoggerFactory.clear_cache()
            
            # 获取框架logger（get_logger 已在顶部导入）
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