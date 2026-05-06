#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
爬虫进程相关的工具函数
包含信号处理、优雅关闭等功能
"""

import asyncio
import signal
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from crawlo.crawler import Crawler, CrawlerState


class ProcessSignalHandler:
    """处理进程信号的工具类"""
    
    def __init__(self, logger, crawlers=None):
        """
        初始化信号处理器
        
        Args:
            logger: 日志记录器
            crawlers: 爬虫实例列表（可选，可通过set_crawlers方法设置）
        """
        self.logger = logger
        self.shutdown_event = asyncio.Event()
        self.shutdown_requested = False
        self.crawlers = crawlers or []
    
    def setup_signal_handlers(self):
        """设置信号处理器以优雅地处理关闭信号"""
        import sys
        
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.shutdown_requested = True
            self.shutdown_event.set()
        
        # 检测平台类型
        is_windows = sys.platform.lower().startswith('win')
        
        # Windows 平台使用标准 signal 模块
        if is_windows:
            try:
                signal.signal(signal.SIGINT, signal_handler)
                signal.signal(signal.SIGTERM, signal_handler)
                self.logger.debug("Using standard signal handlers (Windows)")
            except Exception as e:
                self.logger.warning(f"Failed to setup Windows signal handlers: {e}")
            return
        
        # Unix/Linux 平台尝试使用 asyncio 的信号处理器
        try:
            loop = asyncio.get_event_loop()
            if hasattr(loop, 'add_signal_handler'):
                loop.add_signal_handler(signal.SIGINT, lambda: signal_handler(signal.SIGINT, None))
                loop.add_signal_handler(signal.SIGTERM, lambda: signal_handler(signal.SIGTERM, None))
                self.logger.debug("Using asyncio signal handlers (Unix/Linux)")
            else:
                # 回退到标准 signal 模块
                signal.signal(signal.SIGINT, signal_handler)
                signal.signal(signal.SIGTERM, signal_handler)
                self.logger.debug("Using standard signal handlers (fallback)")
        except Exception as e:
            self.logger.warning(f"Failed to setup signal handlers: {e}")
            # 最后尝试标准 signal 模块
            try:
                signal.signal(signal.SIGINT, signal_handler)
                signal.signal(signal.SIGTERM, signal_handler)
            except Exception as e2:
                self.logger.error(f"Failed to setup fallback signal handlers: {e2}")
        
    def set_crawlers(self, crawlers):
        """设置爬虫列表
        
        Args:
            crawlers: 爬虫实例列表
        """
        self.crawlers = crawlers
    
    async def graceful_shutdown(self):
        """优雅地关闭所有爬虫

        在关闭前保存检查点，确保 Ctrl+C 后可以续爬。
        """
        # 取消所有正在运行的任务
        for crawler in self.crawlers:
            try:
                engine = getattr(crawler, '_engine', None)
                task_manager = getattr(engine, 'task_manager', None) if engine else None
                if task_manager:
                    for task in list(getattr(task_manager, 'current_task', [])):
                        if not task.done():
                            task.cancel()
            except Exception as e:
                self.logger.warning(f"取消爬虫任务时出错: {e}")
        
        # 通知所有爬虫开始关闭（使用 reason='shutdown' 触发检查点保存）
        for crawler in self.crawlers:
            try:
                # 使用字符串比较状态，避免直接引用CrawlerState
                current_state = getattr(crawler, '_state', 'unknown')
                closing_states = ['CLOSING', 'closing', 'CLOSED', 'closed']
                if hasattr(current_state, 'value'):
                    current_state = current_state.value
                if str(current_state) not in closing_states:
                    # 使用 reason='shutdown' 触发检查点保存
                    if hasattr(crawler, '_cleanup'):
                        await crawler._cleanup(reason='shutdown')
            except Exception as e:
                self.logger.warning(f"关闭爬虫时出错: {e}")


class SpiderDiscoveryUtils:
    """爬虫发现和注册相关的工具类"""
    
    @staticmethod
    def register_spider_modules(spider_modules: List[str], logger):
        """
        注册爬虫模块

        先尝试直接 import 每个模块（处理 Spider 定义在 __init__.py 的情况），
        再对未发现的模块统一执行自动发现（扫描目录中的 .py 文件）。

        Args:
            spider_modules: 爬虫模块列表
            logger: 日志记录器
        """
        try:
            from crawlo.spider import get_global_spider_registry, SpiderDiscoveryState
            registry = get_global_spider_registry()

            logger.debug(f"Registering spider modules: {spider_modules}")

            for module_path in spider_modules:
                try:
                    __import__(module_path)
                    logger.debug(f"Successfully imported spider module: {module_path}")
                except ImportError as e:
                    logger.warning(f"Failed to import spider module {module_path}: {e}")

            # 统一对未发现的模块执行自动发现（auto_discover 内部通过 is_discovered 跳过已扫描的）
            undiscovered = [m for m in spider_modules if not SpiderDiscoveryState.is_discovered(m)]
            if undiscovered:
                SpiderDiscoveryUtils.auto_discover_spider_modules(undiscovered, logger)

            spider_names = list(registry.keys())
            logger.debug(f"Registered spiders after import: {spider_names}")
        except Exception as e:
            logger.warning(f"Error registering spider modules: {e}")
    
    @staticmethod
    def auto_discover_spider_modules(spider_modules: List[str], logger):
        """
        自动发现并导入爬虫模块中的所有爬虫
        这个方法会扫描指定模块目录下的所有Python文件并自动导入
        
        Args:
            spider_modules: 爬虫模块列表
            logger: 日志记录器
        """
        try:
            from crawlo.spider import get_global_spider_registry
            import importlib
            from pathlib import Path
            import sys
            
            from crawlo.spider import SpiderDiscoveryState
            
            registry = get_global_spider_registry()
            initial_spider_count = len(registry)
            
            for module_path in spider_modules:
                if SpiderDiscoveryState.is_discovered(module_path):
                    logger.debug(f"Skipping auto-discovery for already-discovered module: {module_path}")
                    continue
                try:
                    # 将模块路径转换为文件系统路径
                    # 例如: ofweek_standalone.spiders -> ofweek_standalone/spiders
                    package_parts = module_path.split('.')
                    if len(package_parts) < 2:
                        continue
                        
                    # 获取项目根目录
                    project_root = None
                    for path in sys.path:
                        if path and Path(path).exists():
                            possible_module_path = Path(path) / package_parts[0]
                            if possible_module_path.exists():
                                project_root = path
                                break
                    
                    if not project_root:
                        # 尝试使用当前工作目录
                        project_root = str(Path.cwd())
                    
                    # 构建模块目录路径
                    module_dir = Path(project_root)
                    for part in package_parts:
                        module_dir = module_dir / part
                    
                    # 如果目录存在，扫描其中的Python文件
                    if module_dir.exists() and module_dir.is_dir():
                        # 导入目录下的所有Python文件（除了__init__.py）
                        for py_file in module_dir.glob("*.py"):
                            if py_file.name.startswith('_'):
                                continue
                                
                            # 构造模块名
                            module_name = py_file.stem  # 文件名（不含扩展名）
                            full_module_path = f"{module_path}.{module_name}"
                            
                            try:
                                # 导入模块以触发Spider注册
                                importlib.import_module(full_module_path)
                            except ImportError as e:
                                logger.warning(f"Failed to auto-import spider module {full_module_path}: {type(e).__name__}: {e}")
                                SpiderDiscoveryState.add_discovery_error(
                                    f"{full_module_path}: {type(e).__name__}: {e}"
                                )
                            except Exception as e:
                                logger.warning(f"Failed to auto-import spider module {full_module_path}: {type(e).__name__}: {e}")
                                SpiderDiscoveryState.add_discovery_error(
                                    f"{full_module_path}: {type(e).__name__}: {e}"
                                )
                except Exception as e:
                    logger.warning(f"Error during auto-discovery for module {module_path}: {e}")
                finally:
                    SpiderDiscoveryState.mark_discovered(module_path)
            
            # 检查是否有新的爬虫被注册
            final_spider_count = len(registry)
            if final_spider_count > initial_spider_count:
                new_spiders = list(registry.keys())
                logger.info(f"Auto-discovered {final_spider_count - initial_spider_count} new spiders: {new_spiders}")
                
        except Exception as e:
            logger.warning(f"Error during auto-discovery of spider modules: {e}")


class SettingsUtils:
    """配置处理相关的工具类"""
    
    @staticmethod
    def merge_settings(base_settings, additional_settings):
        """
        合并配置

        Args:
            base_settings: 基础配置
            additional_settings: 额外配置字典

        Returns:
            Optional[SettingManager]: 合并后的配置管理器
        """
        if not additional_settings:
            return base_settings

        # 这里可以实现更复杂的配置合并逻辑
        from crawlo.settings.setting_manager import SettingManager
        merged = SettingManager()

        # 复制基础配置
        if base_settings:
            if hasattr(base_settings, 'attributes'):
                # 如果 base_settings 是 SettingManager 实例，复制其 attributes
                merged.update_attributes(base_settings.attributes)
            else:
                # 否则，复制其 __dict__
                merged.update_attributes(base_settings.__dict__)

        # 应用额外配置
        merged.update_attributes(additional_settings)

        return merged