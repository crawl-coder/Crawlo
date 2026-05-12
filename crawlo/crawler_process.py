#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawler进程管理器

负责多个 Crawler 的编排与并发执行，包括信号处理、爬虫注册、并发控制等。

主要组件：
- CrawlerProcess: 爬虫进程管理器，支持单个/多个爬虫运行
"""

import asyncio
import time
from typing import Optional, Type, Dict, Any, List, Union, TYPE_CHECKING, cast

from crawlo.crawler import Crawler
from crawlo.initialization import initialize_framework
from crawlo.logging import get_logger
from crawlo.utils.process_utils import ProcessSignalHandler, SpiderDiscoveryUtils, SettingsUtils
from crawlo.spider import get_global_spider_registry, SpiderResolver

if TYPE_CHECKING:
    from crawlo.spider import Spider
    from crawlo.settings.setting_manager import SettingManager


class CrawlerProcess:
    """
    Crawler进程管理器 - 管理多个Crawler的执行

    简化版本，专注于核心功能
    """

    def __init__(self, settings: Optional['SettingManager'] = None, max_concurrency: int = 3, spider_modules: Optional[List[str]] = None) -> None:
        """
        初始化爬虫进程管理器

        Args:
            settings: 配置管理器
            max_concurrency: 最大并发数
            spider_modules: 爬虫模块列表
        """
        # 初始化框架配置
        self._settings: Optional['SettingManager'] = settings or initialize_framework()
        self._max_concurrency: int = max_concurrency
        self._crawlers: List[Crawler] = []
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(max_concurrency)
        self._logger = get_logger('crawler.process')
        
        # Windows 平台: 在框架层面自动应用猴子补丁修复
        # 必须在 _logger 初始化之后调用
        self._apply_windows_asyncio_fix()

        # 信号处理相关
        # ProcessSignalHandler 已在顶部导入
        self._signal_handler = ProcessSignalHandler(self._logger, self._crawlers)
        self._shutdown_event: asyncio.Event = self._signal_handler.shutdown_event
        self._shutdown_requested: bool = self._signal_handler.shutdown_requested

        # 如果没有显式提供spider_modules，则从settings中获取
        if spider_modules is None and self._settings:
            spider_modules = self._settings.get('SPIDER_MODULES', [])
            self._logger.debug(f"从settings中获取SPIDER_MODULES: {spider_modules}")

        self._spider_modules: List[str] = spider_modules or []  # 保存spider_modules

        # 如果提供了spider_modules，自动注册这些模块中的爬虫
        if self._spider_modules:
            self._register_spider_modules(self._spider_modules)

        # 指标
        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None

        # 注册信号处理器
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """设置信号处理器以优雅地处理关闭信号

        注意：在 Windows 上，信号处理器需要在事件循环启动后设置
        """
        self._signal_handler.set_crawlers(self._crawlers)
        # 延迟信号处理器设置到事件循环启动后

    def _apply_windows_asyncio_fix(self) -> None:
        """
        在 Windows 平台自动应用 asyncio 传输关闭警告的修复。
        
        这个方法在 CrawlerProcess 初始化时调用，确保所有使用 CrawlerProcess
        的项目都能自动获得修复，无需用户手动导入和调用。
        """
        import sys
        if sys.platform != 'win32':
            return
        
        try:
            import asyncio.proactor_events
            import warnings
            
            # 1. 猴子补丁 _ProactorBasePipeTransport.__del__
            _original_del = asyncio.proactor_events._ProactorBasePipeTransport.__del__

            def _patched_del(self):
                try:
                    _original_del(self)
                except (ValueError, OSError):
                    pass

            asyncio.proactor_events._ProactorBasePipeTransport.__del__ = _patched_del

            # 2. 同样修补 BaseSubprocessTransport
            try:
                import asyncio.base_subprocess
                _original_sub_del = asyncio.base_subprocess.BaseSubprocessTransport.__del__

                def _patched_sub_del(self):
                    try:
                        _original_sub_del(self)
                    except (ValueError, OSError):
                        pass

                asyncio.base_subprocess.BaseSubprocessTransport.__del__ = _patched_sub_del
            except Exception:
                pass

            # 3. 抑制 warnings 模块的 ResourceWarning
            warnings.filterwarnings('ignore', message='unclosed transport', category=ResourceWarning)
            
            self._logger.debug("已自动应用 Windows asyncio 传输关闭警告修复")
        except Exception as e:
            # 修复失败不应该影响正常运行
            self._logger.debug(f"应用 Windows asyncio 修复失败(可忽略): {e}")
        try:
            loop = asyncio.get_running_loop()
            # 如果事件循环已经在运行，直接设置
            self._signal_handler.setup_signal_handlers()
        except RuntimeError:
            # 事件循环尚未启动，将在 crawl() 方法中设置
            self._logger.debug("Event loop not running, signal handlers will be set up later")

    async def _graceful_shutdown(self):
        """优雅地关闭所有爬虫"""
        self._signal_handler.set_crawlers(self._crawlers)
        await self._signal_handler.graceful_shutdown()

    def _register_spider_modules(self, spider_modules: List[str]) -> None:
        """
        注册爬虫模块

        Args:
            spider_modules: 爬虫模块列表
        """
        # SpiderDiscoveryUtils 已在顶部导入
        SpiderDiscoveryUtils.register_spider_modules(spider_modules, self._logger)

    def _auto_discover_spider_modules(self, spider_modules: List[str]) -> None:
        """
        自动发现并导入爬虫模块中的所有爬虫
        这个方法会扫描指定模块目录下的所有Python文件并自动导入

        Args:
            spider_modules: 爬虫模块列表
        """
        # SpiderDiscoveryUtils 已在顶部导入
        SpiderDiscoveryUtils.auto_discover_spider_modules(spider_modules, self._logger)

    def is_spider_registered(self, name: str) -> bool:
        """
        检查爬虫是否已注册

        Args:
            name: 爬虫名称

        Returns:
            bool: 是否已注册
        """
        # get_global_spider_registry 已在顶部导入
        registry = get_global_spider_registry()
        return name in registry

    def get_spider_class(self, name: str) -> Optional[Type['Spider']]:
        """
        获取爬虫类

        Args:
            name: 爬虫名称

        Returns:
            Optional[Type[Spider]]: 爬虫类
        """
        # get_global_spider_registry 已在顶部导入
        registry = get_global_spider_registry()
        return registry.get(name)

    def get_spider_names(self) -> List[str]:
        """
        获取所有注册的爬虫名称

        Returns:
            List[str]: 爬虫名称列表
        """
        # get_global_spider_registry 已在顶部导入
        registry = get_global_spider_registry()
        return list(registry.keys())

    async def crawl(self, spider_cls_or_name: Union[Type['Spider'], str, List[Union[Type['Spider'], str]]], settings: Optional[Dict[str, Any]] = None) -> Union[Crawler, List[Union[Crawler, BaseException]]]:
        """
        运行爬虫（单个或多个）

        Args:
            spider_cls_or_name: 爬虫类/名称或爬虫类/名称列表
            settings: 配置字典

        Returns:
            Union[Crawler, List[Union[Crawler, BaseException]]]: 单个爬虫实例或爬虫实例列表
        """
        # Windows平台兼容性处理
        import sys
        if sys.platform.lower().startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        # 确保信号处理器已设置（在事件循环启动后）
        self._signal_handler.setup_signal_handlers()

        result = None
        try:
            # 判断输入是单个还是多个爬虫
            if not isinstance(spider_cls_or_name, list):
                result = await self._crawl_single(spider_cls_or_name, settings)
            else:
                result = await self._crawl_multiple(spider_cls_or_name, settings)
            return result

        except KeyboardInterrupt:
            # 捕获 Ctrl+C (Windows/Linux 都支持)
            self._shutdown_event.set()
            # 执行优雅关闭
            await self._graceful_shutdown()
            # 重新抛出以便调用者知道是被中断的
            raise
        except asyncio.CancelledError:
            # 处理取消异常
            await self._graceful_shutdown()
            raise
        except Exception as e:
            self._logger.error(f"Error during crawl: {e}")
            await self._graceful_shutdown()
            raise
        finally:
            # 在事件循环关闭前，主动关闭所有残留的 transport
            # 这是解决 Windows ProactorEventLoop "unclosed transport" 警告的根本方案
            await self._shutdown_loop_transports()

    async def _crawl_single(self, spider_cls_or_name: Union[Type['Spider'], str], settings: Optional[Dict[str, Any]] = None) -> Crawler:
        """
        运行单个爬虫

        Args:
            spider_cls_or_name: 爬虫类或名称
            settings: 配置字典

        Returns:
            Crawler: 爬虫实例
        """
        spider_cls = self._resolve_spider_class(spider_cls_or_name)

        # 记录启动的爬虫名称
        self._logger.info(f"Starting spider: {spider_cls.name}")

        merged_settings = self._merge_settings(settings)
        crawler = Crawler(spider_cls, merged_settings)

        # 将 crawler 添加到信号处理器的列表中
        if crawler not in self._crawlers:
            self._crawlers.append(crawler)

        async with self._semaphore:
            # 创建爬虫任务
            crawl_task = asyncio.create_task(crawler.crawl())

            try:
                # 等待爬虫完成或收到关闭信号
                done, pending = await asyncio.wait(
                    [crawl_task, asyncio.create_task(self._shutdown_event.wait())],
                    return_when=asyncio.FIRST_COMPLETED
                )

                # 如果收到关闭信号，取消爬虫任务
                if self._shutdown_event.is_set() and not crawl_task.done():
                    self._logger.info(f"Shutdown requested, cancelling spider: {spider_cls.name}")
                    crawl_task.cancel()
                    try:
                        await crawl_task
                    except asyncio.CancelledError:
                        self._logger.debug(f"Spider {spider_cls.name} cancelled successfully")

                # 检查爬虫任务是否异常（排除 CancelledError）
                if crawl_task.done() and not crawl_task.cancelled():
                    exc = crawl_task.exception()
                    if exc:
                        raise exc

            except asyncio.CancelledError:
                # 处理任务取消异常
                self._logger.debug(f"Crawl task was cancelled: {spider_cls.name}")
                raise
            finally:
                # 确保任务被清理
                if not crawl_task.done():
                    crawl_task.cancel()
                    try:
                        await crawl_task
                    except asyncio.CancelledError:
                        pass

        # 执行优雅关闭流程（保存检查点、打印统计信息等）
        await self._graceful_shutdown()

        # 清理crawler资源，防止内存泄漏
        await self._cleanup_crawler(crawler, spider_cls.name)

        return crawler

    async def _crawl_multiple(self, spider_classes_or_names: List[Union[Type['Spider'], str]], settings: Optional[Dict[str, Any]] = None) -> List[Union[Crawler, BaseException]]:
        """
        运行多个爬虫

        Args:
            spider_classes_or_names: 爬虫类/名称列表
            settings: 配置字典

        Returns:
            List[Union[Crawler, BaseException]]: 爬虫实例列表
        """
        self._start_time = time.time()

        try:
            spider_classes = []
            for cls_or_name in spider_classes_or_names:
                spider_cls = self._resolve_spider_class(cls_or_name)
                spider_classes.append(spider_cls)

            # 记录启动的爬虫名称
            spider_names = [cls.name for cls in spider_classes]
            if len(spider_names) == 1:
                self._logger.info(f"Starting spider: {spider_names[0]}")
            else:
                self._logger.info(f"Starting spiders: {', '.join(spider_names)}")

            tasks = []
            for spider_cls in spider_classes:
                merged_settings = self._merge_settings(settings)
                crawler = Crawler(spider_cls, merged_settings)
                self._crawlers.append(crawler)

                task = asyncio.create_task(self._run_with_semaphore(crawler))
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果
            successful = sum(1 for r in results if not isinstance(r, Exception))
            failed = len(results) - successful

            self._logger.info(f"Crawl completed: {successful} successful, {failed} failed")

            return cast(List[Union[Crawler, BaseException]], results)

        finally:
            # 清理所有crawler，防止资源累积
            await self._cleanup_all_crawlers()

            self._end_time = time.time()
            if self._start_time:
                duration = self._end_time - self._start_time
                self._logger.info(f"Total execution time: {duration:.2f}s")

    async def _cleanup_crawler(self, crawler: Crawler, spider_name: str) -> None:
        """
        清理单个爬虫资源

        Args:
            crawler: 爬虫实例
            spider_name: 爬虫名称
        """
        await self._cleanup_single_crawler(crawler)
        self._logger.debug(f"Cleaned up crawler: {spider_name}")

    async def _cleanup_all_crawlers(self) -> None:
        """清理所有爬虫资源"""
        self._logger.debug(f"Cleaning up {len(self._crawlers)} crawler(s)...")
        for crawler in self._crawlers:
            await self._cleanup_single_crawler(crawler)

        # 清空crawlers列表，释放引用
        self._crawlers.clear()

    async def _cleanup_single_crawler(self, crawler: Crawler) -> None:
        """
        清理单个爬虫资源的内部方法

        Args:
            crawler: 爬虫实例
        """
        try:
            if hasattr(crawler, '_resource_manager'):
                await crawler._resource_manager.cleanup_all()
        except Exception as e:
            self._logger.warning(f"Failed to cleanup crawler: {e}")

    async def _shutdown_loop_transports(self) -> None:
        """
        在事件循环关闭前主动关闭残留的 transport。

        作为猴子补丁之外的额外防御，在循环还活着时尽量关闭已知 transport，
        减少 GC 时 __del__ 被调用的机会。猴子补丁（在 crawlo 包导入时自动应用）
        负责兜底拦截任何遗漏 transport 的析构错误。
        """
        import sys
        if sys.platform != 'win32':
            return

        try:
            loop = asyncio.get_running_loop()

            # 关闭所有异步生成器
            await loop.shutdown_asyncgens()

            # 主动关闭 ProactorEventLoop 上注册的 transport
            transports = []
            if hasattr(loop, '_transports'):
                transports = list(loop._transports.values())
            if hasattr(loop, '_subprocesses'):
                transports.extend(list(loop._subprocesses.values()))

            closed_count = 0
            for transport in transports:
                try:
                    if hasattr(transport, 'is_closing') and not transport.is_closing():
                        transport.close()
                        closed_count += 1
                except Exception:
                    pass

            if closed_count:
                self._logger.debug(f"Proactively closed {closed_count} transport(s)")
                await asyncio.sleep(0.05)

        except Exception as e:
            self._logger.debug(f"Loop transport cleanup error (ignorable): {e}")

    async def _run_with_semaphore(self, crawler: Crawler) -> Crawler:
        """
        在信号量控制下运行爬虫

        Args:
            crawler: 爬虫实例

        Returns:
            Crawler: 爬虫实例
        """
        async with self._semaphore:
            await crawler.crawl()
            return crawler

    def _resolve_spider_class(self, spider_cls_or_name: Union[Type['Spider'], str]) -> Type['Spider']:
        """
        解析Spider类

        Args:
            spider_cls_or_name: 爬虫类或名称

        Returns:
            Type[Spider]: 爬虫类

        Raises:
            ValueError: 无法解析爬虫类
        """
        # SpiderResolver 已在顶部导入
        return SpiderResolver.resolve_spider_class(spider_cls_or_name, getattr(self, '_spider_modules', None))

    def _merge_settings(self, additional_settings: Optional[Dict[str, Any]]) -> Optional['SettingManager']:
        """
        合并配置

        Args:
            additional_settings: 额外配置字典

        Returns:
            Optional[SettingManager]: 合并后的配置管理器
        """
        # SettingsUtils 已在顶部导入
        return SettingsUtils.merge_settings(self._settings, additional_settings)

    def get_metrics(self) -> Dict[str, Any]:
        """
        获取整体指标

        Returns:
            Dict[str, Any]: 整体指标字典
        """
        total_duration = 0.0
        if self._start_time and self._end_time:
            total_duration = self._end_time - self._start_time

        crawler_metrics = [crawler.metrics for crawler in self._crawlers]

        return {
            'total_duration': total_duration,
            'crawler_count': len(self._crawlers),
            'total_requests': sum(m.request_count for m in crawler_metrics),
            'total_success': sum(m.success_count for m in crawler_metrics),
            'total_errors': sum(m.error_count for m in crawler_metrics),
            'average_success_rate': sum(m.get_success_rate() for m in crawler_metrics) / len(crawler_metrics) if crawler_metrics else 0.0
        }
