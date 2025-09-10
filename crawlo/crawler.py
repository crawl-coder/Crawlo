#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo Crawler Module
====================
提供爬虫进程管理和运行时核心功能。

核心组件:
- Crawler: 单个爬虫运行实例，管理Spider与引擎的生命周期
- CrawlerProcess: 爬虫进程管理器，支持多爬虫并发调度和资源管理

功能特性:
- 智能并发控制和资源管理
- 优雅关闭和信号处理
- 统计监控和性能追踪
- 自动模块发现和注册
- 错误恢复和重试机制
- 大规模爬虫优化支持

示例用法:
    # 单个爬虫运行
    crawler = Crawler(MySpider, settings)
    await crawler.crawl()
    
    # 多爬虫并发管理
    process = CrawlerProcess()
    await process.crawl([Spider1, Spider2])
"""
from __future__ import annotations
import asyncio
import signal
import time
import threading
from typing import Type, Optional, Set, List, Union, Dict, Any
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


class CrawlerContext:
    """
    爬虫上下文管理器
    提供共享状态和资源管理
    """
    
    def __init__(self):
        self.start_time = time.time()
        self.total_crawlers = 0
        self.active_crawlers = 0
        self.completed_crawlers = 0
        self.failed_crawlers = 0
        self.error_log = []
        self._lock = threading.RLock()
        
    def increment_total(self):
        with self._lock:
            self.total_crawlers += 1
            
    def increment_active(self):
        with self._lock:
            self.active_crawlers += 1
            
    def decrement_active(self):
        with self._lock:
            self.active_crawlers -= 1
            
    def increment_completed(self):
        with self._lock:
            self.completed_crawlers += 1
            
    def increment_failed(self, error: str):
        with self._lock:
            self.failed_crawlers += 1
            self.error_log.append({
                'timestamp': time.time(),
                'error': error
            })
            
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            duration = time.time() - self.start_time
            return {
                'total_crawlers': self.total_crawlers,
                'active_crawlers': self.active_crawlers,
                'completed_crawlers': self.completed_crawlers,
                'failed_crawlers': self.failed_crawlers,
                'success_rate': (self.completed_crawlers / max(1, self.total_crawlers)) * 100,
                'duration_seconds': round(duration, 2),
                'error_count': len(self.error_log)
            }


class Crawler:
    """
    单个爬虫运行实例，管理 Spider 与引擎的生命周期
    
    提供功能:
    - Spider 生命周期管理（初始化、运行、关闭）
    - 引擎组件的协调管理
    - 配置合并和验证
    - 统计数据收集
    - 扩展管理
    - 异常处理和清理
    """

    def __init__(self, spider_cls: Type[Spider], settings: SettingManager, context: Optional[CrawlerContext] = None):
        self.spider_cls = spider_cls
        self.spider: Optional[Spider] = None
        self.engine: Optional[Engine] = None
        self.stats: Optional[StatsCollector] = None
        self.subscriber: Optional[Subscriber] = None
        self.extension: Optional[ExtensionManager] = None
        self.settings: SettingManager = settings.copy()
        self.context = context or CrawlerContext()
        
        # 状态管理
        self._closed = False
        self._close_lock = asyncio.Lock()
        self._start_time = None
        self._end_time = None
        
        # 性能监控
        self._performance_metrics = {
            'initialization_time': 0,
            'crawl_duration': 0,
            'memory_peak': 0,
            'request_count': 0,
            'error_count': 0
        }

    async def crawl(self):
        """
        启动爬虫核心流程
        
        包含以下阶段:
        1. 初始化阶段: 创建所有组件
        2. 验证阶段: 检查配置和状态
        3. 运行阶段: 启动爬虫引擎
        4. 清理阶段: 资源释放
        """
        init_start = time.time()
        self._start_time = init_start
        
        try:
            # 更新上下文状态
            self.context.increment_active()
            
            # 阶段 1: 初始化组件
            self.subscriber = self._create_subscriber()
            self.spider = self._create_spider()
            self.engine = self._create_engine() 
            self.stats = self._create_stats()
            self.extension = self._create_extension()
            
            # 记录初始化时间
            self._performance_metrics['initialization_time'] = time.time() - init_start
            
            # 阶段 2: 验证状态
            self._validate_crawler_state()
            
            # 阶段 3: 启动爬虫
            crawl_start = time.time()
            await self.engine.start_spider(self.spider)
            
            # 记录爬取时间
            self._performance_metrics['crawl_duration'] = time.time() - crawl_start
            self._end_time = time.time()
            
            # 更新上下文状态
            self.context.increment_completed()
            
            logger.info(f"爬虫 {self.spider.name} 完成，耗时 {self._get_total_duration():.2f}秒")
            
        except Exception as e:
            self._performance_metrics['error_count'] += 1
            self.context.increment_failed(str(e))
            logger.error(f"爬虫 {getattr(self.spider, 'name', 'Unknown')} 运行失败: {e}", exc_info=True)
            raise
        finally:
            self.context.decrement_active()
            # 确保资源清理
            await self._ensure_cleanup()

    def _validate_crawler_state(self):
        """
        验证爬虫状态和配置
        确保所有必要组件都已正确初始化
        """
        if not self.spider:
            raise RuntimeError("爬虫实例未初始化")
        if not self.engine:
            raise RuntimeError("引擎未初始化")
        if not self.stats:
            raise RuntimeError("统计收集器未初始化")
        if not self.subscriber:
            raise RuntimeError("事件订阅器未初始化")
        
        # 检查关键配置
        if not self.spider.name:
            raise ValueError("爬虫名称不能为空")
            
        logger.debug(f"爬虫 {self.spider.name} 状态验证通过")
    
    def _get_total_duration(self) -> float:
        """获取总运行时间"""
        if self._start_time and self._end_time:
            return self._end_time - self._start_time
        return 0.0
    
    async def _ensure_cleanup(self):
        """确保资源清理"""
        try:
            if not self._closed:
                await self.close()
        except Exception as e:
            logger.warning(f"清理资源时发生错误: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        metrics = self._performance_metrics.copy()
        metrics['total_duration'] = self._get_total_duration()
        if self.stats:
            # 添加统计数据
            stats_data = getattr(self.stats, 'get_stats', lambda: {})()
            metrics.update(stats_data)
        return metrics
    @staticmethod
    def _create_subscriber() -> Subscriber:
        """创建事件订阅器"""
        return Subscriber()

    def _create_spider(self) -> Spider:
        """
        创建并验证爬虫实例（增强版）
        
        执行以下验证:
        - 爬虫名称必须存在
        - start_requests 方法必须可调用
        - start_urls 不能是字符串
        - parse 方法建议存在
        """
        spider = self.spider_cls.create_instance(self)

        # 必要属性检查
        if not getattr(spider, 'name', None):
            raise AttributeError(
                f"爬虫类 '{self.spider_cls.__name__}' 必须定义 'name' 属性。\n"
                f"示例: name = 'my_spider'"
            )

        if not callable(getattr(spider, 'start_requests', None)):
            raise AttributeError(
                f"爬虫 '{spider.name}' 必须实现可调用的 'start_requests' 方法。\n"
                f"示例: def start_requests(self): yield Request(url='...')"
            )

        # start_urls 类型检查
        start_urls = getattr(spider, 'start_urls', [])
        if isinstance(start_urls, str):
            raise TypeError(
                f"爬虫 '{spider.name}' 的 'start_urls' 必须是列表或元组，不能是字符串。\n"
                f"正确写法: start_urls = ['http://example.com']\n"
                f"错误写法: start_urls = 'http://example.com'"
            )

        # parse 方法检查（警告而非错误）
        if not callable(getattr(spider, 'parse', None)):
            logger.warning(
                f"爬虫 '{spider.name}' 未定义 'parse' 方法。\n"
                f"请确保所有 Request 都指定了回调函数，否则响应将被忽略。"
            )
        
        # 设置爬虫配置
        self._set_spider(spider)
        
        logger.debug(f"爬虫 '{spider.name}' 初始化完成")
        return spider

    def _create_engine(self) -> Engine:
        """创建并初始化引擎"""
        engine = Engine(self)
        engine.engine_start()
        logger.debug(f"引擎初始化完成，爬虫: {getattr(self.spider, 'name', 'Unknown')}")
        return engine

    def _create_stats(self) -> StatsCollector:
        """创建统计收集器"""
        stats = StatsCollector(self)
        logger.debug(f"统计收集器初始化完成，爬虫: {getattr(self.spider, 'name', 'Unknown')}")
        return stats

    def _create_extension(self) -> ExtensionManager:
        """创建扩展管理器"""
        extension = ExtensionManager.create_instance(self)
        logger.debug(f"扩展管理器初始化完成，爬虫: {getattr(self.spider, 'name', 'Unknown')}")
        return extension

    def _set_spider(self, spider: Spider):
        """
        设置爬虫配置和事件订阅
        将爬虫的生命周期事件与订阅器绑定
        """
        # 订阅爬虫生命周期事件
        self.subscriber.subscribe(spider.spider_opened, event=spider_opened)
        self.subscriber.subscribe(spider.spider_closed, event=spider_closed)
        
        # 合并爬虫自定义配置
        merge_settings(spider, self.settings)
        
        logger.debug(f"爬虫 '{spider.name}' 配置合并完成")

    async def close(self, reason='finished') -> None:
        """
        关闭爬虫并清理资源（增强版）
        
        确保只关闭一次，并处理所有清理操作
        """
        async with self._close_lock:
            if self._closed:
                return
            
            self._closed = True
            self._end_time = time.time()
            
            try:
                # 通知爬虫关闭事件
                if self.subscriber:
                    await self.subscriber.notify(spider_closed)
                
                # 统计数据收集
                if self.stats and self.spider:
                    self.stats.close_spider(spider=self.spider, reason=reason)
                    # 记录统计数据
                    try:
                        from crawlo.commands.stats import record_stats
                        record_stats(self)
                    except ImportError:
                        logger.debug("统计记录模块不存在，跳过统计记录")
                
                logger.info(
                    f"爬虫 '{getattr(self.spider, 'name', 'Unknown')}' 已关闭，"
                    f"原因: {reason}，耗时: {self._get_total_duration():.2f}秒"
                )
                
            except Exception as e:
                logger.error(f"关闭爬虫时发生错误: {e}", exc_info=True)
            finally:
                # 确保资源清理
                await self._cleanup_resources()
    
    async def _cleanup_resources(self):
        """清理所有资源"""
        cleanup_tasks = []
        
        # 引擎清理
        if self.engine:
            try:
                cleanup_tasks.append(self.engine.close())
            except AttributeError:
                pass  # 引擎没有close方法
        
        # 扩展清理
        if self.extension:
            try:
                cleanup_tasks.append(self.extension.close())
            except AttributeError:
                pass
        
        # 统计收集器清理
        if self.stats:
            try:
                cleanup_tasks.append(self.stats.close())
            except AttributeError:
                pass
        
        # 并发执行清理任务
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
        logger.debug("资源清理完成")


class CrawlerProcess:
    """
    爬虫进程管理器
    
    支持功能:
    - 多爬虫并发调度和资源管理
    - 自动模块发现和爬虫注册
    - 智能并发控制和负载均衡
    - 优雅关闭和信号处理
    - 实时状态监控和统计
    - 错误恢复和重试机制
    - 大规模爬虫优化支持
    
    使用示例:
        # 基本用法
        process = CrawlerProcess()
        await process.crawl(MySpider)
        
        # 多爬虫并发
        await process.crawl([Spider1, Spider2, 'spider_name'])
        
        # 自定义并发数
        process = CrawlerProcess(max_concurrency=8)
    """

    def __init__(
        self,
        settings: Optional[SettingManager] = None,
        max_concurrency: Optional[int] = None,
        spider_modules: Optional[List[str]] = None,
        enable_monitoring: bool = True
    ):
        # 基础配置
        self.settings: SettingManager = settings or self._get_default_settings()
        self.crawlers: Set[Crawler] = set()
        self._active_tasks: Set[asyncio.Task] = set()
        
        # 上下文管理器
        self.context = CrawlerContext()
        
        # 并发控制配置
        self.max_concurrency: int = (
            max_concurrency
            or self.settings.get('MAX_RUNNING_SPIDERS')
            or self.settings.get('CONCURRENCY', 3)
        )
        self.semaphore = asyncio.Semaphore(self.max_concurrency)
        
        # 监控配置
        self.enable_monitoring = enable_monitoring
        self._monitoring_task = None
        self._shutdown_event = asyncio.Event()
        
        # 自动发现并导入爬虫模块
        if spider_modules:
            self.auto_discover(spider_modules)

        # 使用全局注册表的快照（避免后续导入影响）
        self._spider_registry: Dict[str, Type[Spider]] = get_global_spider_registry()
        
        # 性能监控
        self._performance_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'memory_usage_mb': 0,
            'cpu_usage_percent': 0
        }

        # 注册信号量
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)
        
        logger.info(
            f"CrawlerProcess 初始化完成\n"
            f"  - 最大并行爬虫数: {self.max_concurrency}\n"
            f"  - 已注册爬虫数: {len(self._spider_registry)}\n"
            f"  - 监控启用: {self.enable_monitoring}"
        )

    async def start_monitoring(self):
        """启动监控任务"""
        if not self.enable_monitoring:
            return
            
        self._monitoring_task = asyncio.create_task(self._monitor_loop())
        logger.debug("监控任务已启动")
    
    async def stop_monitoring(self):
        """停止监控任务"""
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            logger.debug("监控任务已停止")
    
    async def _monitor_loop(self):
        """监控循环，定期收集和报告状态"""
        try:
            while not self._shutdown_event.is_set():
                await self._collect_performance_stats()
                
                # 每30秒输出一次状态
                stats = self.context.get_stats()
                if stats['active_crawlers'] > 0:
                    logger.info(
                        f"爬虫状态: 活跃 {stats['active_crawlers']}, "
                        f"完成 {stats['completed_crawlers']}, "
                        f"失败 {stats['failed_crawlers']}, "
                        f"成功率 {stats['success_rate']:.1f}%"
                    )
                
                await asyncio.sleep(30)  # 30秒间隔
                
        except asyncio.CancelledError:
            logger.debug("监控循环被取消")
        except Exception as e:
            logger.error(f"监控循环错误: {e}", exc_info=True)
    
    async def _collect_performance_stats(self):
        """收集性能统计数据"""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            self._performance_stats.update({
                'memory_usage_mb': round(memory_info.rss / 1024 / 1024, 2),
                'cpu_usage_percent': round(process.cpu_percent(), 2)
            })
            
        except ImportError:
            # psutil 不存在时跳过性能监控
            pass
        except Exception as e:
            logger.debug(f"收集性能统计失败: {e}")
    @staticmethod
    def auto_discover(modules: List[str]):
        """
        自动导入模块，触发 Spider 类定义和注册（增强版）
        
        支持递归扫描和错误恢复
        """
        import importlib
        import pkgutil
        
        discovered_count = 0
        error_count = 0
        
        for module_name in modules:
            try:
                module = importlib.import_module(module_name)
                
                if hasattr(module, '__path__'):
                    # 包模块，递归扫描
                    for _, name, _ in pkgutil.walk_packages(module.__path__, module.__name__ + "."):
                        try:
                            importlib.import_module(name)
                            discovered_count += 1
                        except Exception as sub_e:
                            error_count += 1
                            logger.warning(f"导入子模块 {name} 失败: {sub_e}")
                else:
                    # 单个模块
                    importlib.import_module(module_name)
                    discovered_count += 1
                    
                logger.debug(f"已扫描模块: {module_name}")
                
            except Exception as e:
                error_count += 1
                logger.error(f"扫描模块 {module_name} 失败: {e}", exc_info=True)
        
        logger.info(
            f"模块发现完成: 成功 {discovered_count} 个，失败 {error_count} 个"
        )

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
        """
        启动一个或多个爬虫
        
        增强功能:
        - 智能并发控制
        - 实时监控和统计
        - 错误恢复和重试
        - 优雅关闭处理
        """
        # 阶段 1: 预处理和验证
        spider_classes_to_run = self._resolve_spiders_to_run(spiders)
        total = len(spider_classes_to_run)

        if total == 0:
            raise ValueError("至少需要提供一个爬虫类或名称")

        # 阶段 2: 初始化上下文和监控
        for _ in range(total):
            self.context.increment_total()
        
        # 启动监控任务
        await self.start_monitoring()
        
        try:
            # 阶段 3: 按类名排序，保证启动顺序可预测
            spider_classes_to_run.sort(key=lambda cls: cls.__name__.lower())
            
            logger.info(
                f"开始启动 {total} 个爬虫\n"
                f"  - 最大并发数: {self.max_concurrency}\n"
                f"  - 爬虫列表: {[cls.__name__ for cls in spider_classes_to_run]}"
            )

            # 阶段 4: 流式启动所有爬虫任务
            tasks = [
                asyncio.create_task(
                    self._run_spider_with_limit(spider_cls, index + 1, total),
                    name=f"spider-{spider_cls.__name__}-{index+1}"
                )
                for index, spider_cls in enumerate(spider_classes_to_run)
            ]

            # 阶段 5: 等待所有任务完成（失败不中断）
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 阶段 6: 统计异常和结果
            failed = [i for i, r in enumerate(results) if isinstance(r, Exception)]
            successful = total - len(failed)
            
            if failed:
                failed_spiders = [spider_classes_to_run[i].__name__ for i in failed]
                logger.error(
                    f"爬虫执行结果: 成功 {successful}/{total}，失败 {len(failed)}/{total}\n"
                    f"  - 失败爬虫: {failed_spiders}"
                )
                
                # 记录详细错误信息
                for i in failed:
                    error = results[i]
                    logger.error(f"爬虫 {spider_classes_to_run[i].__name__} 错误详情: {error}")
            else:
                logger.info(f"所有 {total} 个爬虫均成功完成! 🎉")
            
            # 返回统计结果
            return {
                'total': total,
                'successful': successful,
                'failed': len(failed),
                'success_rate': (successful / total) * 100 if total > 0 else 0,
                'context_stats': self.context.get_stats()
            }
            
        finally:
            # 阶段 7: 清理和关闭
            await self.stop_monitoring()
            await self._cleanup_process()

    async def _cleanup_process(self):
        """清理进程资源"""
        try:
            # 等待所有活跃爬虫完成
            if self.crawlers:
                close_tasks = [crawler.close() for crawler in self.crawlers]
                await asyncio.gather(*close_tasks, return_exceptions=True)
                self.crawlers.clear()
            
            # 清理活跃任务
            if self._active_tasks:
                for task in list(self._active_tasks):
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*self._active_tasks, return_exceptions=True)
                self._active_tasks.clear()
            
            logger.debug("进程资源清理完成")
            
        except Exception as e:
            logger.error(f"清理进程资源时发生错误: {e}", exc_info=True)
    
    def get_process_stats(self) -> Dict[str, Any]:
        """获取进程统计信息"""
        context_stats = self.context.get_stats()
        
        return {
            'context': context_stats,
            'performance': self._performance_stats.copy(),
            'crawlers': {
                'total_registered': len(self._spider_registry),
                'active_crawlers': len(self.crawlers),
                'max_concurrency': self.max_concurrency
            },
            'registry': {
                'spider_names': list(self._spider_registry.keys()),
                'spider_classes': [cls.__name__ for cls in self._spider_registry.values()]
            }
        }
    def _resolve_spiders_to_run(
        self,
        spiders_input: Union[Type[Spider], str, List[Union[Type[Spider], str]]]
    ) -> List[Type[Spider]]:
        """
        解析输入为爬虫类列表
        
        支持各种输入格式并验证唯一性
        """
        inputs = self._normalize_inputs(spiders_input)
        seen_spider_names: Set[str] = set()
        spider_classes: List[Type[Spider]] = []
        
        for item in inputs:
            try:
                spider_cls = self._resolve_spider_class(item)
                spider_name = getattr(spider_cls, 'name', None)
                
                if not spider_name:
                    raise ValueError(f"爬虫类 {spider_cls.__name__} 缺少 'name' 属性")

                if spider_name in seen_spider_names:
                    raise ValueError(
                        f"本次运行中爬虫名称 '{spider_name}' 重复。\n"
                        f"请确保每个爬虫的 name 属性在本次运行中唯一。"
                    )

                seen_spider_names.add(spider_name)
                spider_classes.append(spider_cls)
                
                logger.debug(f"解析爬虫成功: {item} -> {spider_cls.__name__} (name='{spider_name}')")
                
            except Exception as e:
                logger.error(f"解析爬虫失败: {item} - {e}")
                raise

        return spider_classes

    @staticmethod
    def _normalize_inputs(spiders_input) -> List[Union[Type[Spider], str]]:
        """
        标准化输入为列表
        
        支持更多输入类型并提供更好的错误信息
        """
        if isinstance(spiders_input, (type, str)):
            return [spiders_input]
        elif isinstance(spiders_input, (list, tuple, set)):
            spider_list = list(spiders_input)
            if not spider_list:
                raise ValueError("爬虫列表不能为空")
            return spider_list
        else:
            raise TypeError(
                f"spiders 参数类型不支持: {type(spiders_input)}\n"
                f"支持的类型: Spider类、name字符串，或它们的列表/元组/集合"
            )

    def _resolve_spider_class(self, item: Union[Type[Spider], str]) -> Type[Spider]:
        """
        解析单个输入项为爬虫类
        
        提供更好的错误提示和调试信息
        """
        if isinstance(item, type) and issubclass(item, Spider):
            # 直接是 Spider 类
            return item
        elif isinstance(item, str):
            # 是字符串名称，需要查找注册表
            spider_cls = self._spider_registry.get(item)
            if not spider_cls:
                available_spiders = list(self._spider_registry.keys())
                raise ValueError(
                    f"未找到名为 '{item}' 的爬虫。\n"
                    f"已注册的爬虫: {available_spiders}\n"
                    f"请检查爬虫名称是否正确，或者确保爬虫已被正确导入和注册。"
                )
            return spider_cls
        else:
            raise TypeError(
                f"无效类型 {type(item)}: {item}\n"
                f"必须是 Spider 类或字符串 name。\n"
                f"示例: MySpider 或 'my_spider'"
            )

    async def _run_spider_with_limit(self, spider_cls: Type[Spider], seq: int, total: int):
        """
        受信号量限制的爬虫运行函数
        
        包含增强的错误处理和监控功能
        """
        task = asyncio.current_task()
        crawler = None
        
        try:
            # 注册任务
            if task:
                self._active_tasks.add(task)
            
            # 获取并发许可
            await self.semaphore.acquire()
            
            start_msg = f"[{seq}/{total}] 启动爬虫: {spider_cls.__name__}"
            logger.info(start_msg)
            
            # 创建并运行爬虫
            crawler = Crawler(spider_cls, self.settings, self.context)
            self.crawlers.add(crawler)
            
            # 记录启动时间
            start_time = time.time()
            
            # 运行爬虫
            await crawler.crawl()
            
            # 计算运行时间
            duration = time.time() - start_time
            
            end_msg = (
                f"[{seq}/{total}] 爬虫完成: {spider_cls.__name__}, "
                f"耗时: {duration:.2f}秒"
            )
            logger.info(end_msg)
            
            # 记录成功统计
            self._performance_stats['successful_requests'] += 1
            
        except Exception as e:
            # 记录失败统计
            self._performance_stats['failed_requests'] += 1
            
            error_msg = f"爬虫 {spider_cls.__name__} 执行失败: {e}"
            logger.error(error_msg, exc_info=True)
            
            # 将错误信息记录到上下文
            if hasattr(self, 'context'):
                self.context.increment_failed(error_msg)
            
            raise
        finally:
            # 清理资源
            try:
                if crawler and crawler in self.crawlers:
                    self.crawlers.remove(crawler)
                    
                if task and task in self._active_tasks:
                    self._active_tasks.remove(task)
                    
                self.semaphore.release()
                
            except Exception as cleanup_error:
                logger.warning(f"清理资源时发生错误: {cleanup_error}")

    def _shutdown(self, _signum, _frame):
        """
        优雅关闭信号处理
        
        提供更好的关闭体验和资源清理
        """
        signal_name = {signal.SIGINT: 'SIGINT', signal.SIGTERM: 'SIGTERM'}.get(_signum, str(_signum))
        logger.warning(f"收到关闭信号 {signal_name}，正在停止所有爬虫...")
        
        # 设置关闭事件
        if hasattr(self, '_shutdown_event'):
            self._shutdown_event.set()
        
        # 停止所有爬虫引擎
        for crawler in list(self.crawlers):
            if crawler.engine:
                crawler.engine.running = False
                crawler.engine.normal = False
                logger.debug(f"已停止爬虫引擎: {getattr(crawler.spider, 'name', 'Unknown')}")
        
        # 创建关闭任务
        asyncio.create_task(self._wait_for_shutdown())
        
        logger.info("关闭指令已发送，等待爬虫完成当前任务...")

    async def _wait_for_shutdown(self):
        """
        等待所有活跃任务完成
        
        提供更好的关闭时间控制和进度反馈
        """
        try:
            # 停止监控任务
            await self.stop_monitoring()
            
            # 等待活跃任务完成
            pending = [t for t in self._active_tasks if not t.done()]
            
            if pending:
                logger.info(
                    f"等待 {len(pending)} 个活跃任务完成..."
                    f"(最大等待时间: 30秒)"
                )
                
                # 设置超时时间
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*pending, return_exceptions=True),
                        timeout=30.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("部分任务超时，强制取消中...")
                    
                    # 强制取消超时任务
                    for task in pending:
                        if not task.done():
                            task.cancel()
                    
                    # 等待取消完成
                    await asyncio.gather(*pending, return_exceptions=True)
            
            # 最终清理
            await self._cleanup_process()
            
            # 输出最终统计
            final_stats = self.context.get_stats()
            logger.info(
                f"所有爬虫已优雅关闭 👋\n"
                f"  - 总计爬虫: {final_stats['total_crawlers']}\n"
                f"  - 成功完成: {final_stats['completed_crawlers']}\n"
                f"  - 失败数量: {final_stats['failed_crawlers']}\n"
                f"  - 成功率: {final_stats['success_rate']:.1f}%\n"
                f"  - 总运行时间: {final_stats['duration_seconds']}秒"
            )
            
        except Exception as e:
            logger.error(f"关闭过程中发生错误: {e}", exc_info=True)

    @classmethod
    def _get_default_settings(cls) -> SettingManager:
        """
        加载默认配置
        
        提供更好的错误处理和降级策略
        """
        try:
            settings = get_settings()
            logger.debug("成功加载默认配置")
            return settings
        except Exception as e:
            logger.warning(f"无法加载默认配置: {e}，使用空配置")
            return SettingManager()


# === 工具函数 ===

def create_crawler_with_optimizations(
    spider_cls: Type[Spider],
    settings: Optional[SettingManager] = None,
    **optimization_kwargs
) -> Crawler:
    """
    创建优化的爬虫实例
    
    :param spider_cls: 爬虫类
    :param settings: 设置管理器
    :param optimization_kwargs: 优化参数
    :return: 爬虫实例
    """
    if settings is None:
        settings = SettingManager()
    
    # 应用优化配置
    for key, value in optimization_kwargs.items():
        settings.set(key, value)
    
    context = CrawlerContext()
    return Crawler(spider_cls, settings, context)


def create_process_with_large_scale_config(
    config_type: str = 'balanced',
    concurrency: int = 16,
    **kwargs
) -> CrawlerProcess:
    """
    创建支持大规模优化的进程管理器
    
    :param config_type: 配置类型 ('conservative', 'balanced', 'aggressive', 'memory_optimized')
    :param concurrency: 并发数
    :param kwargs: 其他参数
    :return: 进程管理器
    """
    try:
        from crawlo.utils.large_scale_config import LargeScaleConfig
        
        # 获取优化配置
        config_methods = {
            'conservative': LargeScaleConfig.conservative_config,
            'balanced': LargeScaleConfig.balanced_config,
            'aggressive': LargeScaleConfig.aggressive_config,
            'memory_optimized': LargeScaleConfig.memory_optimized_config
        }
        
        if config_type not in config_methods:
            logger.warning(f"未知的配置类型: {config_type}，使用默认配置")
            settings = SettingManager()
        else:
            config = config_methods[config_type](concurrency)
            settings = SettingManager()
            settings.update(config)
        
        return CrawlerProcess(
            settings=settings,
            max_concurrency=concurrency,
            **kwargs
        )
        
    except ImportError:
        logger.warning("大规模配置模块不存在，使用默认配置")
        return CrawlerProcess(max_concurrency=concurrency, **kwargs)


# === 导出接口 ===

__all__ = [
    'Crawler',
    'CrawlerProcess', 
    'CrawlerContext',
    'create_crawler_with_optimizations',
    'create_process_with_large_scale_config'
]