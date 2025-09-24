#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
统一框架初始化管理器
====================
提供Crawlo框架的统一初始化入口点，彻底解决日志时序问题和多重初始化问题。

设计原则：
1. 简单明确：只有一个初始化管理器
2. 早期日志：日志系统最先初始化
3. 幂等安全：可以安全地多次调用
4. 状态清晰：明确的初始化阶段和状态
"""
import asyncio
import threading
from typing import Optional, Dict, Any

from crawlo.settings.setting_manager import SettingManager
from crawlo.utils.log import LoggerManager


class InitializationPhase:
    """初始化阶段枚举"""
    UNINITIALIZED = "uninitialized"
    LOG_CONFIGURED = "log_configured"
    SETTINGS_LOADED = "settings_loaded"
    FRAMEWORK_READY = "framework_ready"


class CrawloFrameworkInitializer:
    """
    Crawlo框架统一初始化管理器
    
    职责：
    1. 管理框架组件的初始化顺序
    2. 确保日志系统早期配置
    3. 提供统一的初始化状态查询
    4. 保证初始化的幂等性
    """

    _instance = None
    _lock = threading.Lock()
    _async_lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(CrawloFrameworkInitializer, cls).__new__(cls)
                    cls._instance._phase = InitializationPhase.UNINITIALIZED
                    cls._instance._settings = None
                    cls._instance._logger = None
                    cls._instance._errors = []
        return cls._instance

    @property
    def phase(self) -> str:
        """获取当前初始化阶段"""
        return self._phase

    @property
    def settings(self) -> Optional[SettingManager]:
        """获取配置管理器实例"""
        return self._settings

    @property
    def logger(self):
        """获取框架级logger实例"""
        if self._logger is None and self._phase != InitializationPhase.UNINITIALIZED:
            from crawlo.utils.log import get_logger
            self._logger = get_logger('crawlo.framework')
        return self._logger

    @property
    def is_ready(self) -> bool:
        """检查框架是否已准备就绪"""
        return self._phase == InitializationPhase.FRAMEWORK_READY

    @property
    def errors(self) -> list:
        """获取初始化过程中的错误"""
        return self._errors.copy()

    def _configure_logging(self, settings: SettingManager = None) -> None:
        """
        配置日志系统（阶段1）
        
        Args:
            settings: 配置管理器，如果为None则使用默认配置
        """
        if self._phase != InitializationPhase.UNINITIALIZED:
            return

        try:
            # 使用LoggerManager配置日志系统
            if settings:
                LoggerManager.configure(settings)
            else:
                # 使用默认的基本配置，但保留日志文件配置
                LoggerManager.configure(
                    LOG_LEVEL='INFO',
                    LOG_FILE='logs/framework.log',  # 提供默认日志文件
                    LOG_FORMAT='%(asctime)s - [%(name)s] - %(levelname)s: %(message)s'
                )

            # 更新阶段状态
            self._phase = InitializationPhase.LOG_CONFIGURED

            # 现在可以安全地创建logger
            from crawlo.utils.log import get_logger
            self._logger = get_logger('crawlo.framework')
            self._logger.debug("日志系统配置完成")

        except Exception as e:
            self._errors.append(f"配置日志系统失败: {e}")
            # 即使日志配置失败，也要继续初始化，但记录错误
            self._phase = InitializationPhase.LOG_CONFIGURED

    def _load_settings(self, custom_settings: Optional[Dict[str, Any]] = None) -> SettingManager:
        """
        加载配置系统（阶段2）
        
        Args:
            custom_settings: 自定义配置
            
        Returns:
            配置管理器实例
        """
        if self._phase == InitializationPhase.SETTINGS_LOADED or self._phase == InitializationPhase.FRAMEWORK_READY:
            # 如果已经加载过配置，处理自定义配置
            if custom_settings and self._settings:
                settings_copy = self._settings.copy()
                settings_copy.update_attributes(custom_settings)
                return settings_copy
            return self._settings

        # 确保日志系统已配置
        if self._phase == InitializationPhase.UNINITIALIZED:
            self._configure_logging()

        try:
            # 导入并调用项目配置加载函数
            from crawlo.project import _load_project_settings
            self._settings = _load_project_settings(custom_settings)

            # 现在用实际的设置重新配置日志系统
            LoggerManager.configure(self._settings)

            # 重新创建framework logger以使用新的日志配置（包括文件handler）
            from crawlo.utils.log import get_logger
            self._logger = get_logger('crawlo.framework')

            # 更新阶段状态
            self._phase = InitializationPhase.SETTINGS_LOADED

            if self._logger:
                self._logger.debug("配置系统加载完成")

            return self._settings

        except Exception as e:
            error_msg = f"加载配置系统失败: {e}"
            self._errors.append(error_msg)
            if self._logger:
                self._logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def _finalize_initialization(self) -> None:
        """
        完成框架初始化（阶段3）
        """
        if self._phase == InitializationPhase.FRAMEWORK_READY:
            return

        # 确保前面的阶段都已完成
        if self._phase != InitializationPhase.SETTINGS_LOADED:
            raise RuntimeError(f"无法完成初始化，当前阶段: {self._phase}")

        try:
            # 这里可以添加其他需要初始化的框架组件
            # 例如：注册信号处理器、初始化全局资源等

            # 更新阶段状态
            self._phase = InitializationPhase.FRAMEWORK_READY

            if self._logger:
                self._logger.debug("Crawlo框架初始化完成")

                # 输出运行模式信息
                mode_info = self._settings.get('_mode_info') if self._settings else None
                if mode_info:
                    self._logger.debug(mode_info)

        except Exception as e:
            error_msg = f"完成框架初始化失败: {e}"
            self._errors.append(error_msg)
            if self._logger:
                self._logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def initialize(self, custom_settings: Optional[Dict[str, Any]] = None) -> SettingManager:
        """
        同步初始化框架
        
        Args:
            custom_settings: 自定义配置
            
        Returns:
            配置管理器实例
        """
        # 阶段1：配置日志系统
        self._configure_logging()

        # 阶段2：加载配置系统  
        settings = self._load_settings(custom_settings)

        # 阶段3：完成框架初始化
        self._finalize_initialization()

        return settings

    async def async_initialize(self, custom_settings: Optional[Dict[str, Any]] = None) -> SettingManager:
        """
        异步初始化框架
        
        Args:
            custom_settings: 自定义配置
            
        Returns:
            配置管理器实例
        """
        async with self._async_lock:
            return self.initialize(custom_settings)

    def reset(self) -> None:
        """
        重置初始化状态（主要用于测试）
        """
        with self._lock:
            self._phase = InitializationPhase.UNINITIALIZED
            self._settings = None
            self._logger = None
            self._errors = []

            # 重置LoggerManager状态
            LoggerManager._configured = False
            LoggerManager.logger_cache.clear()


# 全局框架初始化管理器实例
_framework_initializer = CrawloFrameworkInitializer()


def get_framework_initializer() -> CrawloFrameworkInitializer:
    """
    获取框架初始化管理器实例
    
    Returns:
        CrawloFrameworkInitializer: 框架初始化管理器实例
    """
    return _framework_initializer


def initialize_framework(custom_settings: Optional[Dict[str, Any]] = None) -> SettingManager:
    """
    初始化Crawlo框架（同步版本）
    
    这是框架的统一初始化入口点，应该在任何框架功能使用之前调用。
    
    Args:
        custom_settings: 自定义配置
        
    Returns:
        配置管理器实例
        
    Example:
        >>> from crawlo.core.framework_initializer import initialize_framework
        >>> settings = initialize_framework()
        >>> # 现在可以安全地使用框架功能
    """
    return _framework_initializer.initialize(custom_settings)


async def async_initialize_framework(custom_settings: Optional[Dict[str, Any]] = None) -> SettingManager:
    """
    异步初始化Crawlo框架
    
    Args:
        custom_settings: 自定义配置
        
    Returns:
        配置管理器实例
    """
    return await _framework_initializer.async_initialize(custom_settings)


def is_framework_ready() -> bool:
    """
    检查框架是否已准备就绪
    
    Returns:
        bool: 框架是否已准备就绪
    """
    return _framework_initializer.is_ready


def get_framework_logger(name: str = 'crawlo'):
    """
    获取框架logger实例
    
    Args:
        name: logger名称
        
    Returns:
        logger实例
    """
    if not _framework_initializer.is_ready:
        # 如果框架未初始化，先进行初始化
        initialize_framework()

    from crawlo.utils.log import get_logger
    return get_logger(name)


# 向后兼容的别名
bootstrap_framework = initialize_framework
get_bootstrap_manager = get_framework_initializer
