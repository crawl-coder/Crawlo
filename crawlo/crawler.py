#!/usr/bin/python
# -*- coding: UTF-8 -*-
from __future__ import annotations
import asyncio
import signal
from typing import Type, Optional, Set, List, Union, Dict
from .spider import Spider, get_global_spider_registry
from .core.engine import Engine
from .utils.log import get_logger
from .subscriber import Subscriber
from .extension import ExtensionManager
from .stats_collector import StatsCollector
from .event import spider_opened, spider_closed
from .settings.setting_manager import SettingManager
from crawlo.project import merge_settings, get_settings


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
        self._closed = False
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
                from crawlo.commands.stats import record_stats
                record_stats(self)


class CrawlerProcess:
    """
    爬虫进程管理器，支持：
    - 自动发现爬虫模块
    - 通过 name 或类启动爬虫
    - 并发控制
    - 优雅关闭
    """

    def __init__(
        self,
        settings: Optional[SettingManager] = None,
        max_concurrency: Optional[int] = None,
        spider_modules: Optional[List[str]] = None
    ):
        self.settings: SettingManager = settings or self._get_default_settings()
        self.crawlers: Set[Crawler] = set()
        self._active_tasks: Set[asyncio.Task] = set()

        # 自动发现并导入爬虫模块
        if spider_modules:
            self.auto_discover(spider_modules)

        # 使用全局注册表的快照（避免后续导入影响）
        self._spider_registry: Dict[str, Type[Spider]] = get_global_spider_registry()

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

    @staticmethod
    def auto_discover(modules: List[str]):
        """自动导入模块，触发 Spider 类定义和注册"""
        import importlib
        import pkgutil
        for module_name in modules:
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, '__path__'):
                    for _, name, _ in pkgutil.walk_packages(module.__path__, module.__name__ + "."):
                        importlib.import_module(name)
                else:
                    importlib.import_module(module_name)
                logger.debug(f"已扫描模块: {module_name}")
            except Exception as e:
                logger.error(f"扫描模块 {module_name} 失败: {e}", exc_info=True)

    # === 公共只读接口：避免直接访问 _spider_registry ===

    def get_spider_names(self) -> List[str]:
        """获取所有已注册的爬虫名称"""
        return list(self._spider_registry.keys())

    def get_spider_class(self, name: str) -> Optional[Type[Spider]]:
        """根据 name 获取爬虫类"""
        return self._spider_registry.get(name)

    def is_spider_registered(self, name: str) -> bool:
        """检查某个 name 是否已注册"""
        return name in self._spider_registry

    async def crawl(self, spiders: Union[Type[Spider], str, List[Union[Type[Spider], str]]]):
        """启动一个或多个爬虫"""
        spider_classes_to_run = self._resolve_spiders_to_run(spiders)
        total = len(spider_classes_to_run)

        if total == 0:
            raise ValueError("至少需要提供一个爬虫类或名称")

        # 按类名排序，保证启动顺序可预测
        spider_classes_to_run.sort(key=lambda cls: cls.__name__.lower())
        logger.info(f"启动 {total} 个爬虫.")

        # 流式启动
        tasks = [
            asyncio.create_task(self._run_spider_with_limit(spider_cls, index + 1, total))
            for index, spider_cls in enumerate(spider_classes_to_run)
        ]

        # 等待完成（失败不中断）
        results = await asyncio.gather(*tasks, return_exceptions=True)
        failed = [i for i, r in enumerate(results) if isinstance(r, Exception)]
        if failed:
            logger.error(f"共 {len(failed)} 个爬虫执行异常: {[spider_classes_to_run[i].__name__ for i in failed]}")

    def _resolve_spiders_to_run(
        self,
        spiders_input: Union[Type[Spider], str, List[Union[Type[Spider], str]]]
    ) -> List[Type[Spider]]:
        """解析输入为爬虫类列表"""
        inputs = self._normalize_inputs(spiders_input)
        seen_spider_names: Set[str] = set()
        spider_classes: List[Type[Spider]] = []

        for item in inputs:
            spider_cls = self._resolve_spider_class(item)
            spider_name = spider_cls.name

            if spider_name in seen_spider_names:
                raise ValueError(f"本次运行中爬虫名称 '{spider_name}' 重复。")

            seen_spider_names.add(spider_name)
            spider_classes.append(spider_cls)

        return spider_classes

    @staticmethod
    def _normalize_inputs(spiders_input) -> List[Union[Type[Spider], str]]:
        """标准化输入为列表"""
        if isinstance(spiders_input, (type, str)):
            return [spiders_input]
        elif isinstance(spiders_input, (list, tuple)):
            return list(spiders_input)
        else:
            raise TypeError("spiders 必须是爬虫类、name 字符串，或它们的列表/元组")

    def _resolve_spider_class(self, item: Union[Type[Spider], str]) -> Type[Spider]:
        """解析单个输入项为爬虫类"""
        if isinstance(item, type) and issubclass(item, Spider):
            return item
        elif isinstance(item, str):
            spider_cls = self._spider_registry.get(item)
            if not spider_cls:
                raise ValueError(f"未找到名为 '{item}' 的爬虫。")
            return spider_cls
        else:
            raise TypeError(f"无效类型 {type(item)}。必须是 Spider 类或字符串 name。")

    async def _run_spider_with_limit(self, spider_cls: Type[Spider], seq: int, total: int):
        """受信号量限制的爬虫运行函数"""
        task = asyncio.current_task()
        self._active_tasks.add(task)
        try:
            await self.semaphore.acquire()
            logger.info(f"[{seq}/{total}] 启动爬虫: {spider_cls.__name__}")
            crawler = Crawler(spider_cls, self.settings)
            self.crawlers.add(crawler)
            await crawler.crawl()
            logger.info(f"[{seq}/{total}] 爬虫完成: {spider_cls.__name__}")
        except Exception as e:
            logger.error(f"爬虫 {spider_cls.__name__} 执行失败: {e}", exc_info=True)
            raise
        finally:
            if task in self._active_tasks:
                self._active_tasks.remove(task)
            self.semaphore.release()

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
# # -*- coding: UTF-8 -*-
# import asyncio
# import signal
# from typing import Type, Optional, Set, List
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
#
# logger = get_logger(__name__)
#
#
# class Crawler:
#     """单个爬虫运行实例，绑定 Spider 与引擎"""
#
#     def __init__(self, spider_cls: Type[Spider], settings: SettingManager):
#         self.spider_cls = spider_cls
#         self.spider: Optional[Spider] = None
#         self.engine: Optional[Engine] = None
#         self.stats: Optional[StatsCollector] = None
#         self.subscriber: Optional[Subscriber] = None
#         self.extension: Optional[ExtensionManager] = None
#         self.settings: SettingManager = settings.copy()
#         self._closed = False  # 新增状态
#         self._close_lock = asyncio.Lock()
#
#     async def crawl(self):
#         """启动爬虫核心流程"""
#         self.subscriber = self._create_subscriber()
#         self.spider = self._create_spider()
#         self.engine = self._create_engine()
#         self.stats = self._create_stats()
#         self.extension = self._create_extension()
#
#         await self.engine.start_spider(self.spider)
#
#     @staticmethod
#     def _create_subscriber() -> Subscriber:
#         return Subscriber()
#
#     def _create_spider(self) -> Spider:
#         spider = self.spider_cls.create_instance(self)
#
#         # --- 关键属性检查 ---
#         if not getattr(spider, 'name', None):
#             raise AttributeError(f"爬虫类 '{self.spider_cls.__name__}' 必须定义 'name' 属性。")
#
#         if not callable(getattr(spider, 'start_requests', None)):
#             raise AttributeError(f"爬虫 '{spider.name}' 必须实现可调用的 'start_requests' 方法。")
#
#         start_urls = getattr(spider, 'start_urls', [])
#         if isinstance(start_urls, str):
#             raise TypeError(f"爬虫 '{spider.name}' 的 'start_urls' 必须是列表或元组，不能是字符串。")
#
#         if not callable(getattr(spider, 'parse', None)):
#             logger.warning(
#                 f"爬虫 '{spider.name}' 未定义 'parse' 方法。请确保所有 Request 都指定了回调函数，否则响应将被忽略。")
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
#         return StatsCollector(self)
#
#     def _create_extension(self) -> ExtensionManager:
#         return ExtensionManager.create_instance(self)
#
#     def _set_spider(self, spider: Spider):
#         self.subscriber.subscribe(spider.spider_opened, event=spider_opened)
#         self.subscriber.subscribe(spider.spider_closed, event=spider_closed)
#         merge_settings(spider, self.settings)
#
#     async def close(self, reason='finished') -> None:
#         async with self._close_lock:
#             if self._closed:
#                 return
#             self._closed = True
#             await self.subscriber.notify(spider_closed)
#             if self.stats and self.spider:
#                 self.stats.close_spider(spider=self.spider, reason=reason)
#
#
# class CrawlerProcess:
#     """
#     爬虫进程管理器，支持多爬虫并发调度、信号量控制、实时日志与优雅关闭
#     """
#
#     def __init__(self, settings: Optional[SettingManager] = None, max_concurrency: Optional[int] = None):
#         self.settings: SettingManager = settings or self._get_default_settings()
#         self.crawlers: Set[Crawler] = set()
#         self._active_tasks: Set[asyncio.Task] = set()
#
#         # 使用专用配置，降级使用 CONCURRENCY
#         self.max_concurrency: int = (
#             max_concurrency
#             or self.settings.get('MAX_RUNNING_SPIDERS')
#             or self.settings.get('CONCURRENCY', 3)
#         )
#         self.semaphore = asyncio.Semaphore(self.max_concurrency)
#
#         # 注册信号量
#         signal.signal(signal.SIGINT, self._shutdown)
#         signal.signal(signal.SIGTERM, self._shutdown)
#         logger.info(f"CrawlerProcess 初始化完成，最大并行爬虫数: {self.max_concurrency}")
#
#     async def crawl(self, spiders):
#         """
#         启动一个或多个爬虫，流式调度，支持实时进度反馈
#         """
#         spider_classes = self._normalize_spiders(spiders)
#         total = len(spider_classes)
#
#         if total == 0:
#             raise ValueError("至少需要提供一个爬虫类")
#
#         # 按名称排序
#         spider_classes.sort(key=lambda cls: cls.__name__.lower())
#
#         logger.info(f"启动 {total} 个爬虫.")
#
#         # 流式启动所有爬虫任务
#         tasks = [
#             asyncio.create_task(self._run_spider_with_limit(spider_cls, index + 1, total))
#             for index, spider_cls in enumerate(spider_classes)
#         ]
#
#         # 等待所有任务完成（失败不中断）
#         results = await asyncio.gather(*tasks, return_exceptions=True)
#
#         # 统计异常
#         failed = [i for i, r in enumerate(results) if isinstance(r, Exception)]
#         if failed:
#             logger.error(f"共 {len(failed)} 个爬虫执行异常: {[spider_classes[i].__name__ for i in failed]}")
#
#     @staticmethod
#     def _normalize_spiders(spiders) -> List[Type[Spider]]:
#         """标准化输入为爬虫类列表"""
#         if isinstance(spiders, type) and issubclass(spiders, Spider):
#             return [spiders]
#         elif isinstance(spiders, (list, tuple)):
#             return list(spiders)
#         else:
#             raise TypeError("spiders 必须是爬虫类或爬虫类列表/元组")
#
#     async def _run_spider_with_limit(self, spider_cls: Type[Spider], seq: int, total: int):
#         """
#         受信号量限制的爬虫运行函数，带进度日志
#         """
#         task = asyncio.current_task()
#         self._active_tasks.add(task)
#
#         try:
#             # 获取并发许可
#             await self.semaphore.acquire()
#
#             start_msg = f"[{seq}/{total}] 启动爬虫: {spider_cls.__name__}"
#             logger.info(start_msg)
#
#             # 创建并运行爬虫
#             crawler = self._create_crawler(spider_cls)
#             self.crawlers.add(crawler)
#             await crawler.crawl()
#
#             end_msg = f"[{seq}/{total}] 爬虫完成: {spider_cls.__name__}"
#             logger.info(end_msg)
#
#         except Exception as e:
#             logger.error(f"爬虫 {spider_cls.__name__} 执行失败: {e}", exc_info=True)
#             raise
#         finally:
#             if task in self._active_tasks:
#                 self._active_tasks.remove(task)
#             self.semaphore.release()  # 必须释放
#
#     def _create_crawler(self, spider_cls: Type[Spider]) -> Crawler:
#         """创建爬虫实例"""
#         if isinstance(spider_cls, str):
#             raise SpiderTypeError(f"不支持字符串形式的爬虫: {spider_cls}")
#         return Crawler(spider_cls, self.settings)
#
#     def _shutdown(self, _signum, _frame):
#         """优雅关闭信号处理"""
#         logger.warning("收到关闭信号，正在停止所有爬虫...")
#         for crawler in list(self.crawlers):
#             if crawler.engine:
#                 crawler.engine.running = False
#                 crawler.engine.normal = False
#         asyncio.create_task(self._wait_for_shutdown())
#
#     async def _wait_for_shutdown(self):
#         """等待所有活跃任务完成"""
#         pending = [t for t in self._active_tasks if not t.done()]
#         if pending:
#             logger.info(f"等待 {len(pending)} 个活跃任务完成...")
#             await asyncio.gather(*pending, return_exceptions=True)
#         logger.info("所有爬虫已优雅关闭")
#
#     @classmethod
#     def _get_default_settings(cls) -> SettingManager:
#         """加载默认配置"""
#         try:
#             return get_settings()
#         except Exception as e:
#             logger.warning(f"无法加载默认配置: {e}")
#             return SettingManager()