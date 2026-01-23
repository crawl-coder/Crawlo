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
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.shutdown_requested = True
            self.shutdown_event.set()
            
            # 在主线程中调度关闭操作
            asyncio.create_task(self.graceful_shutdown())
        
        # 注册SIGINT (Ctrl+C) 和 SIGTERM 信号处理器
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
    def set_crawlers(self, crawlers):
        """设置爬虫列表
        
        Args:
            crawlers: 爬虫实例列表
        """
        self.crawlers = crawlers
    
    async def graceful_shutdown(self):
        """优雅地关闭所有爬虫
        
        Args:
            crawlers: 爬虫实例列表
        """
        self.logger.info("开始优雅关闭所有爬虫...")

        # 取消所有正在运行的任务
        for crawler in self.crawlers:
            try:
                # 检查crawler是否正在运行
                if hasattr(crawler, '_state') and crawler.state == getattr(crawler.__class__, 'State', {}).get('RUNNING', 'running'):
                    self.logger.debug(f"取消爬虫任务: {crawler.spider.name if crawler.spider else 'Unknown'}")
                    # 取消crawler中的任务
                    if hasattr(crawler, '_engine') and crawler._engine:
                        # 取消engine中的任务
                        if hasattr(crawler._engine, 'task_manager') and crawler._engine.task_manager:
                            for task in list(getattr(crawler._engine.task_manager, 'current_task', [])):
                                if not task.done():
                                    task.cancel()
                                    self.logger.debug(f"已取消任务: {task}")
            except Exception as e:
                self.logger.warning(f"取消爬虫任务时出错: {e}")
        
        # 通知所有爬虫开始关闭
        for crawler in self.crawlers:
            try:
                # 使用字符串比较状态，避免直接引用CrawlerState
                current_state = getattr(crawler, '_state', 'unknown')
                closing_states = ['CLOSING', 'closing', 'CLOSED', 'closed']
                if hasattr(current_state, 'value'):
                    current_state = current_state.value
                if str(current_state) not in closing_states:
                    self.logger.debug(f"关闭爬虫: {getattr(getattr(crawler, 'spider', None), 'name', 'Unknown')}")
                    await crawler._cleanup()
            except Exception as e:
                self.logger.warning(f"关闭爬虫时出错: {e}")
        
        self.logger.info("所有爬虫已关闭")


class SpiderDiscoveryUtils:
    """爬虫发现和注册相关的工具类"""
    
    @staticmethod
    def register_spider_modules(spider_modules: List[str], logger):
        """
        注册爬虫模块
        
        Args:
            spider_modules: 爬虫模块列表
            logger: 日志记录器
        """
        try:
            from crawlo.spider import get_global_spider_registry
            registry = get_global_spider_registry()
            
            logger.debug(f"Registering spider modules: {spider_modules}")
            
            initial_spider_count = len(registry)
            
            for module_path in spider_modules:
                try:
                    # 导入模块
                    __import__(module_path)
                    logger.debug(f"Successfully imported spider module: {module_path}")
                except ImportError as e:
                    logger.warning(f"Failed to import spider module {module_path}: {e}")
                    # 如果导入失败，尝试自动发现
                    SpiderDiscoveryUtils.auto_discover_spider_modules([module_path], logger)
            
            # 检查注册表中的爬虫
            spider_names = list(registry.keys())
            logger.debug(f"Registered spiders after import: {spider_names}")
            
            # 如果导入模块后没有新的爬虫被注册，则尝试自动发现
            final_spider_count = len(registry)
            if final_spider_count == initial_spider_count:
                logger.debug("No new spiders registered after importing modules, attempting auto-discovery")
                SpiderDiscoveryUtils.auto_discover_spider_modules(spider_modules, logger)
                spider_names = list(registry.keys())
                logger.debug(f"Registered spiders after auto-discovery: {spider_names}")
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
            
            registry = get_global_spider_registry()
            initial_spider_count = len(registry)
            
            for module_path in spider_modules:
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
                                logger.warning(f"Failed to auto-import spider module {full_module_path}: {e}")
                except Exception as e:
                    logger.warning(f"Error during auto-discovery for module {module_path}: {e}")
            
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