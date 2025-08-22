#!/usr/bin/python
# -*- coding: UTF-8 -*-
import asyncio
import signal
from typing import Type, Optional, Set, List

from crawlo.spider import Spider
from crawlo.core.engine import Engine
from crawlo.utils.log import get_logger
from crawlo.subscriber import Subscriber
from crawlo.extension import ExtensionManager
from crawlo.exceptions import SpiderTypeError
from crawlo.stats_collector import StatsCollector
from crawlo.event import spider_opened, spider_closed
from crawlo.settings.setting_manager import SettingManager
from crawlo.utils.project import merge_settings, get_settings


logger = get_logger(__name__)


class Crawler:
    """单个爬虫运行实例，绑定 Spider 与引擎"""

    def __init__(self, spider_cls: Type[Spider], settings: SettingManager):
        self.spider_cls = spider_cls
        self.spider: Optional[Spider] = None
        self.engine: Optional[Engine] = None
        self.stats: Optional[StatsCollector] = None
        self.subscriber: Optional[Subscriber] = None
        self.extension: Optional[ExtensionManager] = None
        self.settings: SettingManager = settings.copy()
        self._closed = False  # 新增状态
        self._close_lock = asyncio.Lock()

    async def crawl(self):
        """启动爬虫核心流程"""
        self.subscriber = self._create_subscriber()
        self.spider = self._create_spider()
        self.engine = self._create_engine()
        self.stats = self._create_stats()
        self.extension = self._create_extension()

        await self.engine.start_spider(self.spider)

    @staticmethod
    def _create_subscriber() -> Subscriber:
        return Subscriber()

    def _create_spider(self) -> Spider:
        spider = self.spider_cls.create_instance(self)

        # --- 关键属性检查 ---
        if not getattr(spider, 'name', None):
            raise AttributeError(f"爬虫类 '{self.spider_cls.__name__}' 必须定义 'name' 属性。")

        if not callable(getattr(spider, 'start_requests', None)):
            raise AttributeError(f"爬虫 '{spider.name}' 必须实现可调用的 'start_requests' 方法。")

        start_urls = getattr(spider, 'start_urls', [])
        if isinstance(start_urls, str):
            raise TypeError(f"爬虫 '{spider.name}' 的 'start_urls' 必须是列表或元组，不能是字符串。")

        if not callable(getattr(spider, 'parse', None)):
            logger.warning(
                f"爬虫 '{spider.name}' 未定义 'parse' 方法。请确保所有 Request 都指定了回调函数，否则响应将被忽略。")

        self._set_spider(spider)
        return spider

    def _create_engine(self) -> Engine:
        engine = Engine(self)
        engine.engine_start()
        return engine

    def _create_stats(self) -> StatsCollector:
        return StatsCollector(self)

    def _create_extension(self) -> ExtensionManager:
        return ExtensionManager.create_instance(self)

    def _set_spider(self, spider: Spider):
        self.subscriber.subscribe(spider.spider_opened, event=spider_opened)
        self.subscriber.subscribe(spider.spider_closed, event=spider_closed)
        merge_settings(spider, self.settings)

    async def close(self, reason='finished') -> None:
        async with self._close_lock:
            if self._closed:
                return
            self._closed = True
            await self.subscriber.notify(spider_closed)
            if self.stats and self.spider:
                self.stats.close_spider(spider=self.spider, reason=reason)


class CrawlerProcess:
    """
    爬虫进程管理器，支持多爬虫并发调度、信号量控制、实时日志与优雅关闭
    """

    def __init__(self, settings: Optional[SettingManager] = None, max_concurrency: Optional[int] = None):
        self.settings: SettingManager = settings or self._get_default_settings()
        self.crawlers: Set[Crawler] = set()
        self._active_tasks: Set[asyncio.Task] = set()

        # 使用专用配置，降级使用 CONCURRENCY
        self.max_concurrency: int = (
            max_concurrency
            or self.settings.get('MAX_RUNNING_SPIDERS')
            or self.settings.get('CONCURRENCY', 3)
        )
        self.semaphore = asyncio.Semaphore(self.max_concurrency)

        # 注册信号量
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)
        logger.info(f"CrawlerProcess 初始化完成，最大并行爬虫数: {self.max_concurrency}")

    async def crawl(self, spiders):
        """
        启动一个或多个爬虫，流式调度，支持实时进度反馈
        """
        spider_classes = self._normalize_spiders(spiders)
        total = len(spider_classes)

        if total == 0:
            raise ValueError("至少需要提供一个爬虫类")

        # 按名称排序
        spider_classes.sort(key=lambda cls: cls.__name__.lower())

        logger.info(f"启动 {total} 个爬虫.")

        # 流式启动所有爬虫任务
        tasks = [
            asyncio.create_task(self._run_spider_with_limit(spider_cls, index + 1, total))
            for index, spider_cls in enumerate(spider_classes)
        ]

        # 等待所有任务完成（失败不中断）
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 统计异常
        failed = [i for i, r in enumerate(results) if isinstance(r, Exception)]
        if failed:
            logger.error(f"共 {len(failed)} 个爬虫执行异常: {[spider_classes[i].__name__ for i in failed]}")

    @staticmethod
    def _normalize_spiders(spiders) -> List[Type[Spider]]:
        """标准化输入为爬虫类列表"""
        if isinstance(spiders, type) and issubclass(spiders, Spider):
            return [spiders]
        elif isinstance(spiders, (list, tuple)):
            return list(spiders)
        else:
            raise TypeError("spiders 必须是爬虫类或爬虫类列表/元组")

    async def _run_spider_with_limit(self, spider_cls: Type[Spider], seq: int, total: int):
        """
        受信号量限制的爬虫运行函数，带进度日志
        """
        task = asyncio.current_task()
        self._active_tasks.add(task)

        try:
            # 获取并发许可
            await self.semaphore.acquire()

            start_msg = f"[{seq}/{total}] 启动爬虫: {spider_cls.__name__}"
            logger.info(start_msg)

            # 创建并运行爬虫
            crawler = self._create_crawler(spider_cls)
            self.crawlers.add(crawler)
            await crawler.crawl()

            end_msg = f"[{seq}/{total}] 爬虫完成: {spider_cls.__name__}"
            logger.info(end_msg)

        except Exception as e:
            logger.error(f"爬虫 {spider_cls.__name__} 执行失败: {e}", exc_info=True)
            raise
        finally:
            if task in self._active_tasks:
                self._active_tasks.remove(task)
            self.semaphore.release()  # 必须释放

    def _create_crawler(self, spider_cls: Type[Spider]) -> Crawler:
        """创建爬虫实例"""
        if isinstance(spider_cls, str):
            raise SpiderTypeError(f"不支持字符串形式的爬虫: {spider_cls}")
        return Crawler(spider_cls, self.settings)

    def _shutdown(self, _signum, _frame):
        """优雅关闭信号处理"""
        logger.warning("收到关闭信号，正在停止所有爬虫...")
        for crawler in list(self.crawlers):
            if crawler.engine:
                crawler.engine.running = False
                crawler.engine.normal = False
        asyncio.create_task(self._wait_for_shutdown())

    async def _wait_for_shutdown(self):
        """等待所有活跃任务完成"""
        pending = [t for t in self._active_tasks if not t.done()]
        if pending:
            logger.info(f"等待 {len(pending)} 个活跃任务完成...")
            await asyncio.gather(*pending, return_exceptions=True)
        logger.info("所有爬虫已优雅关闭")

    @classmethod
    def _get_default_settings(cls) -> SettingManager:
        """加载默认配置"""
        try:
            return get_settings()
        except Exception as e:
            logger.warning(f"无法加载默认配置: {e}")
            return SettingManager()



# #!/usr/bin/python
# # -*- coding:UTF-8 -*
# import signal
# import asyncio
# from typing import Final, Set, Optional
#
# from crawlo.spider import Spider
# from crawlo.core.engine import Engine
# from crawlo.utils.log import get_logger
# from crawlo.subscriber import Subscriber
# from crawlo.extension import ExtensionManager
# from crawlo.exceptions import SpiderTypeError
# from crawlo.stats_collector import StatsCollector
# from crawlo.event import spider_opened, spider_closed
# from crawlo.settings.setting_manager import SettingManager
# from crawlo.utils.project import merge_settings, get_settings
#
# logger = get_logger(__name__)
#
#
# class Crawler:
#
#     def __init__(self, spider_cls, settings):
#         self.spider_cls = spider_cls
#         self.spider: Optional[Spider] = None
#         self.engine: Optional[Engine] = None
#         self.stats: Optional[StatsCollector] = None
#         self.subscriber: Optional[Subscriber] = None
#         self.extension: Optional[ExtensionManager] = None
#         self.settings: SettingManager = settings.copy()
#
#     async def crawl(self):
#         self.subscriber = self._create_subscriber()
#         self.spider = self._create_spider()
#         self.engine = self._create_engine()
#         self.stats = self._create_stats()
#         self.extension = self._create_extension()
#
#         await self.engine.start_spider(self.spider)
#
#     @staticmethod
#     def _create_subscriber():
#         return Subscriber()
#
#     def _create_spider(self) -> Spider:
#         spider = self.spider_cls.create_instance(self)
#
#         # --- 关键属性检查 ---
#         # 1. 检查 name
#         if not getattr(spider, 'name', None):
#             raise AttributeError(f"Spider class '{self.spider_cls.__name__}' must have a 'name' attribute.")
#
#         # 2. 检查 start_requests 是否可调用
#         if not callable(getattr(spider, 'start_requests', None)):
#             raise AttributeError(f"Spider '{spider.name}' must have a callable 'start_requests' method.")
#
#         # 3. 检查 start_urls 类型
#         start_urls = getattr(spider, 'start_urls', [])
#         if isinstance(start_urls, str):
#             raise TypeError(f"'{spider.name}.start_urls' must be a list or tuple, not a string.")
#
#         # --- 日志提示 ---
#         # 提醒用户定义 parse 方法
#         if not callable(getattr(spider, 'parse', None)):
#             logger.warning(f"Spider '{spider.name}' lacks a 'parse' method. Ensure all Requests have callbacks.")
#
#         self._set_spider(spider)
#         return spider
#
#     def _create_engine(self) -> Engine:
#         engine = Engine(self)
#         engine.engine_start()
#         return engine
#
#     def _create_stats(self) -> StatsCollector:
#         stats = StatsCollector(self)
#         return stats
#
#     def _create_extension(self) -> ExtensionManager:
#         extension = ExtensionManager.create_instance(self)
#         return extension
#
#     def _set_spider(self, spider):
#         self.subscriber.subscribe(spider.spider_opened, event=spider_opened)
#         self.subscriber.subscribe(spider.spider_closed, event=spider_closed)
#         merge_settings(spider, self.settings)
#
#     async def close(self, reason='finished') -> None:
#         await asyncio.create_task(self.subscriber.notify(spider_closed))
#         self.stats.close_spider(spider=self.spider, reason=reason)
#
#
# class CrawlerProcess:
#     """爬虫处理类，支持跨平台动态并发控制和精细化日志"""
#
#     def __init__(self, settings=None, max_concurrency: Optional[int] = None, batch_size: int = 10):
#         self.crawlers: Final[Set] = set()
#         self._active_spiders: Final[Set] = set()
#         self.settings = settings or self._get_default_settings()
#         self.batch_size = batch_size
#
#         # 优先使用专用配置，降级使用 CONCURRENCY，最后用默认值
#         self.max_concurrency = (
#                 max_concurrency or
#                 self.settings.get('MAX_RUNNING_SPIDERS') or
#                 self.settings.get('CONCURRENCY', 5)
#         )
#         self.semaphore = asyncio.Semaphore(self.max_concurrency)
#
#         signal.signal(signal.SIGINT, self._shutdown)
#         logger.debug(f"初始化爬虫处理进程，最大并发数: {self.max_concurrency}")
#
#     async def crawl(self, spiders):
#         """支持单个或多个爬虫的批量处理，优化日志输出"""
#         if not spiders:
#             raise ValueError("至少需要提供一个爬虫类")
#
#         # 统一转换为列表
#         if isinstance(spiders, type) and issubclass(spiders, Spider):
#             spiders = [spiders]
#         elif isinstance(spiders, (list, tuple)):
#             spiders = list(spiders)
#         else:
#             raise TypeError("spiders 必须是爬虫类或爬虫类列表/元组")
#
#         # 按爬虫类名首字母排序（升序）
#         spiders.sort(key=lambda x: x.__name__.lower())
#
#         if len(spiders) == 1:
#             logger.info(f"启动爬虫: {spiders[0].__name__}")
#         else:
#             logger.info(f"启动{len(spiders)}个爬虫，按名称排序后分批处理中")
#
#         batches = [spiders[i:i + self.batch_size] for i in range(0, len(spiders), self.batch_size)]
#
#         for batch_idx, batch in enumerate(batches):
#             batch_tasks = set()
#
#             for spider_cls in batch:
#                 crawler = self._create_crawler(spider_cls)
#                 self.crawlers.add(crawler)
#
#                 await self.semaphore.acquire()
#                 task = asyncio.create_task(self._run_crawler_with_semaphore(crawler))
#                 batch_tasks.add(task)
#                 self._active_spiders.add(task)
#
#             if len(spiders) > 1:  # 仅对多爬虫显示批次信息
#                 logger.info(f"启动第 {batch_idx + 1}/{len(batches)} 批爬虫，共 {len(batch)} 个")
#
#             await asyncio.gather(*batch_tasks)
#
#             if len(spiders) > 1:  # 仅对多爬虫显示批次完成信息
#                 logger.info(f"第 {batch_idx + 1} 批爬虫处理完成")
#
#     async def _run_crawler_with_semaphore(self, crawler):
#         """使用信号量控制的爬虫运行函数"""
#         try:
#             await crawler.crawl()
#         finally:
#             self.semaphore.release()  # 确保资源释放
#
#     async def start(self):
#         """启动所有爬虫任务"""
#         if self._active_spiders:
#             logger.info(f"启动 {len(self._active_spiders)} 个爬虫任务，计算得知当前设备最大并发限制: {self.max_concurrency}")
#             await asyncio.gather(*self._active_spiders)
#
#     def _create_crawler(self, spider_cls) -> Crawler:
#         """创建爬虫实例"""
#         if isinstance(spider_cls, str):
#             raise SpiderTypeError(f"{type(self)}.crawl args: String is not supported.")
#         crawler: Crawler = Crawler(spider_cls, self.settings)
#         return crawler
#
#     def _shutdown(self, _signum, _frame):
#         """优雅关闭所有爬虫"""
#         logger.warning(f"收到关闭信号，正在优雅关闭 {len(self.crawlers)} 个爬虫...")
#         for crawler in self.crawlers:
#             if crawler.engine:
#                 crawler.engine.running = False
#                 crawler.engine.normal = False
#                 crawler.stats.close_spider(crawler.spider, 'shutdown signal')
#
#         # 等待所有任务完成
#         asyncio.create_task(self._wait_for_tasks())
#
#     async def _wait_for_tasks(self):
#         """等待所有活跃任务完成"""
#         pending = [task for task in self._active_spiders if not task.done()]
#         if pending:
#             logger.info(f"等待 {len(pending)} 个活跃任务完成...")
#             await asyncio.gather(*pending)
#         logger.info("所有爬虫已优雅关闭")
#
#     @classmethod
#     def _get_default_settings(cls):
#         """框架自动获取默认配置"""
#         try:
#             return get_settings()
#         except ImportError:
#             return {}
