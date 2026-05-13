#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Scheduler — 请求调度器

负责请求队列管理、去重过滤、Redis/Memory 双模式自动切换。
"""
import asyncio
import traceback
from typing import Optional, Callable

from crawlo.logging import get_logger
from crawlo.project import common_call
from crawlo.utils.misc import load_object, safe_get_config
from crawlo.utils.request import set_request
from crawlo.utils.error_handler import ErrorHandler, ErrorContext
from crawlo.utils.request.request_serializer import RequestSerializer
from crawlo.queue.queue_manager import QueueManager
from crawlo.queue.config import QueueConfig
from crawlo.queue.queue_types import QueueType

# ---- 配置常量（统一管理，消除重复） ----
_DEFAULT_QUEUE_TYPE = 'memory'
_DEFAULT_FILTER_CLASS = 'crawlo.filters.memory_filter.MemoryFilter'
_DEFAULT_REDIS_FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'
_DEFAULT_DEDUP_MEMORY = 'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline'
_DEFAULT_DEDUP_REDIS = 'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline'
_DEFAULT_CONCURRENCY = 8
_DEFAULT_DELAY = 1.0
_DEFAULT_DEPTH_PRIORITY = 0


# ---- 配置映射：每种队列模式对应的过滤器、去重管道 ----
_MODE_CONFIG = {
    QueueType.REDIS: {
        'filter_class': _DEFAULT_REDIS_FILTER_CLASS,
        'dedup_pipeline': _DEFAULT_DEDUP_REDIS,
        'source_filter_patterns': ['memory_filter'],
        'source_dedup_pattern': 'memory_dedup_pipeline',
    },
    QueueType.MEMORY: {
        'filter_class': _DEFAULT_FILTER_CLASS,
        'dedup_pipeline': _DEFAULT_DEDUP_MEMORY,
        'source_filter_patterns': ['aioredis_filter', 'redis_filter'],
        'source_dedup_pattern': 'redis_dedup_pipeline',
    },
}


class Scheduler:
    def __init__(self, crawler, dupe_filter, stats, priority):
        self.crawler = crawler
        self.queue_manager: Optional[QueueManager] = None
        self.request_serializer = RequestSerializer()
        self.logger = get_logger(self.__class__.__name__)
        self.error_handler = ErrorHandler(self.__class__.__name__)
        self.stats = stats
        self.dupe_filter = dupe_filter
        self.priority = priority
        self._queue_not_full = asyncio.Condition()

    # ============================
    # Settings helpers (消除 settings 链式访问样板)
    # ============================

    def _get_setting(self, key, default=None):
        if self.crawler and self.crawler.settings is not None:
            try:
                return self.crawler.settings.get(key, default)
            except Exception:
                return default
        return default

    def _set_setting(self, key, value):
        if self.crawler and self.crawler.settings is not None:
            try:
                self.crawler.settings.set(key, value)
            except Exception:
                pass

    # ============================
    # 队列类型属性（消除对 QueueManager._queue_type 的直接访问）
    # ============================

    @property
    def queue_type(self) -> Optional[QueueType]:
        """安全获取当前队列类型"""
        if self.queue_manager and hasattr(self.queue_manager, '_queue_type'):
            return self.queue_manager._queue_type
        return None

    def _is_memory_queue(self) -> bool:
        return self.queue_type == QueueType.MEMORY

    def _is_redis_queue(self) -> bool:
        return self.queue_type == QueueType.REDIS

    # ============================
    # 工厂方法
    # ============================

    @classmethod
    def create_instance(cls, crawler):
        filter_class = safe_get_config(
            getattr(crawler, 'settings', None), 'FILTER_CLASS', _DEFAULT_FILTER_CLASS
        )
        priority = safe_get_config(
            getattr(crawler, 'settings', None), 'DEPTH_PRIORITY', _DEFAULT_DEPTH_PRIORITY
        )
        filter_cls = load_object(filter_class)
        return cls(
            crawler=crawler,
            dupe_filter=filter_cls.create_instance(crawler),
            stats=getattr(crawler, 'stats', None),
            priority=priority,
        )

    # ============================
    # 初始化
    # ============================

    async def open(self):
        """Initialize scheduler: create queue, resolve mode, apply config"""
        self.logger.debug("Starting scheduler initialization...")
        try:
            self._set_spider_name_on_config()

            # 1. 创建并初始化队列
            queue_config = QueueConfig.from_settings(self.crawler.settings)
            self.queue_manager = QueueManager(queue_config)
            needs_config_update = await self.queue_manager.initialize()

            # 2. 统一解析并应用配置模式
            queue_type_setting = self._get_setting('QUEUE_TYPE', _DEFAULT_QUEUE_TYPE)
            await self._resolve_and_apply_config(needs_config_update, queue_type_setting)

            # 3. 输出初始化摘要
            self._log_open_summary(queue_type_setting)
        except Exception as e:
            self.logger.error(f"Scheduler initialization failed: {e}")
            self.logger.debug(f"Detailed error:\n{traceback.format_exc()}")
            raise

    def _set_spider_name_on_config(self):
        """将 spider name 写入 settings 供 RedisKeyManager 使用"""
        if self.crawler.spider:
            spider_name = getattr(self.crawler.spider, 'name', None)
            if spider_name and hasattr(self.crawler.settings, 'set'):
                try:
                    self.crawler.settings.set('SPIDER_NAME', spider_name)
                except Exception:
                    pass

    # ============================
    # 配置模式解析（从 open() 中提取，消除 140 行长方法）
    # ============================

    async def _resolve_and_apply_config(self, needs_config_update: bool, queue_type_setting: str):
        """
        一次性完成模式检测和配置切换，替代原来分散的多个私有方法。

        逻辑：
        1. 检测是否需要模式切换（Redis ↔ Memory）
        2. 如果需要，切换过滤器 + 去重管道配置
        3. 重新创建过滤器实例
        """
        if not self.queue_manager:
            return

        # 检测过滤器和队列类型是否匹配
        current_filter = self._get_setting('FILTER_CLASS', '')
        need_switch = self._detect_mode_mismatch(current_filter)

        if not need_switch and not needs_config_update:
            return  # 配置正确，无需切换

        if needs_config_update:
            original_mode = "standalone" if 'memory_filter' in current_filter else "distributed"

        # 执行配置切换
        switched = self._switch_to_correct_mode(current_filter)

        # 重新创建过滤器实例（无论哪种原因触发切换都需要）
        new_filter_class = self._get_setting('FILTER_CLASS', _DEFAULT_FILTER_CLASS)
        filter_cls = load_object(new_filter_class)
        self.dupe_filter = filter_cls.create_instance(self.crawler)

        # 记录模式切换日志
        if needs_config_update and switched:
            new_mode = "distributed" if self._is_redis_queue() else "standalone"
            if original_mode != new_mode:
                self.logger.warning(
                    f"Runtime mode inconsistency detected: switched from {original_mode} to {new_mode} mode"
                )

    def _detect_mode_mismatch(self, current_filter: str) -> bool:
        """检测当前过滤器是否与队列类型匹配"""
        if not self.queue_manager:
            return False
        if self._is_redis_queue():
            return 'memory_filter' in current_filter
        elif self._is_memory_queue():
            return 'aioredis_filter' in current_filter or 'redis_filter' in current_filter
        return False

    def _switch_to_correct_mode(self, current_filter: str) -> bool:
        """
        切换到当前队列类型对应的正确模式。
        返回是否执行了切换。
        """
        if not self.queue_manager:
            return False

        if self._is_redis_queue():
            return self._apply_mode_config(QueueType.REDIS, current_filter)
        elif self._is_memory_queue():
            return self._apply_mode_config(QueueType.MEMORY, current_filter)
        return False

    def _apply_mode_config(self, target_type: QueueType, current_filter: str) -> bool:
        """
        应用指定模式的配置（过滤器 + 去重管道）。

        Returns:
            bool: 是否执行了任何切换
        """
        config = _MODE_CONFIG.get(target_type)
        if not config:
            return False

        switched = False

        # 切换过滤器
        if any(pattern in current_filter for pattern in config['source_filter_patterns']):
            self._set_setting('FILTER_CLASS', config['filter_class'])
            switched = True

        # 切换去重管道
        default_dedup = self._get_setting('DEFAULT_DEDUP_PIPELINE', '')
        if config['source_dedup_pattern'] in default_dedup:
            self._set_setting('DEFAULT_DEDUP_PIPELINE', config['dedup_pipeline'])
            self._swap_dedup_in_pipelines(default_dedup, config['dedup_pipeline'])
            switched = True

        if switched:
            self.logger.debug(f"Configuration updated -> {target_type.name} mode")

        return switched

    def _swap_dedup_in_pipelines(self, old_pipeline: str, new_pipeline: str):
        """在 PIPELINES 列表中替换去重管道"""
        pipelines = self._get_setting('PIPELINES', [])
        if isinstance(pipelines, list) and old_pipeline in pipelines:
            idx = pipelines.index(old_pipeline)
            pipelines[idx] = new_pipeline
            self._set_setting('PIPELINES', pipelines)
        elif isinstance(pipelines, dict) and old_pipeline in pipelines:
            priority = pipelines.pop(old_pipeline)
            pipelines[new_pipeline] = priority
            self._set_setting('PIPELINES', pipelines)

    def _log_open_summary(self, queue_type_setting: str):
        """输出调度器初始化完成摘要"""
        status = self.queue_manager.get_status() if self.queue_manager else {'type': 'unknown', 'health': 'unknown'}
        updated_filter = self._get_setting('FILTER_CLASS', _DEFAULT_FILTER_CLASS)
        self.logger.info(f"enabled filters: {updated_filter}")
        self.logger.debug(
            f"Scheduler initialized [Queue type: {status['type']}, Status: {status['health']}]"
        )

    # ---- 向后兼容别名（废弃，内部使用） ----
    def _check_filter_config(self):
        """[deprecated] kept for backward compatibility only"""
        return self._detect_mode_mismatch(self._get_setting('FILTER_CLASS', '')) if self.queue_manager else False

    async def _process_filter_updates(self, needs_config_update, updated_configs):
        """[deprecated] no-op, logic merged into _resolve_and_apply_config"""
        pass

    def _is_filter_matching_queue_type(self, current_filter_class):
        """[deprecated] use _detect_mode_mismatch instead"""
        return not self._detect_mode_mismatch(current_filter_class)

    def _switch_to_redis_config(self):
        """[deprecated] use _apply_mode_config(QueueType.REDIS) instead"""
        self._apply_mode_config(QueueType.REDIS, self._get_setting('FILTER_CLASS', ''))

    def _switch_to_memory_config(self):
        """[deprecated] use _apply_mode_config(QueueType.MEMORY) instead"""
        self._apply_mode_config(QueueType.MEMORY, self._get_setting('FILTER_CLASS', ''))

    def _switch_config(self, target_type: str):
        """[deprecated] use _apply_mode_config instead"""
        type_map = {'redis': QueueType.REDIS, 'memory': QueueType.MEMORY}
        if target_type in type_map:
            self._apply_mode_config(type_map[target_type], self._get_setting('FILTER_CLASS', ''))

    # ============================
    # 队列操作
    # ============================

    async def next_request(self):
        """Get next request from queue"""
        if not self.queue_manager:
            return None
        try:
            queue_size_before = await self.queue_manager.size()
            request = await self.queue_manager.get()
            # 通知等待入队的协程：队列有空间了
            async with self._queue_not_full:
                self._queue_not_full.notify_all()
            if request:
                try:
                    spider = getattr(self.crawler, 'spider', None)
                    request = self.request_serializer.restore_after_deserialization(request, spider)
                except Exception as deser_error:
                    self.logger.error(
                        f"[队列] 请求反序列化失败: {deser_error} | 请求数据: {repr(request)}"
                    )
                    return None
            return request
        except Exception as e:
            self.error_handler.handle_error(e, context=ErrorContext(context="Failed to get next request"), raise_error=False)
            return None

    async def enqueue_request(self, request):
        """Add request to queue with dedup check and backpressure wait"""
        # 去重检查
        if not request.dont_filter:
            if hasattr(self.dupe_filter, 'requested_async'):
                is_duplicate = await self.dupe_filter.requested_async(request)
            else:
                is_duplicate = await common_call(self.dupe_filter.requested, request)
            if is_duplicate:
                self.dupe_filter.log_stats(request)
                return False

        if not self.queue_manager:
            self.logger.error("Queue manager not initialized")
            return False

        set_request(request, self.priority)
        try:
            queue_size = await self.queue_manager.size()
            max_size = self.queue_manager.max_size
            retry_count = 0
            max_retries = 100

            # Condition 变量等待队列有空间
            while queue_size >= max_size:
                retry_count += 1
                if retry_count > max_retries:
                    self.logger.error(f"Queue full for too long ({max_retries} retries), dropping: {request.url}")
                    return False
                if retry_count == 1:
                    self.logger.warning(f"Queue full ({queue_size}/{max_size}), pausing...")
                async with self._queue_not_full:
                    current_size = await self.queue_manager.size()
                    if current_size >= max_size:
                        try:
                            await asyncio.wait_for(self._queue_not_full.wait(), timeout=0.5)
                        except asyncio.TimeoutError:
                            pass
                queue_size = await self.queue_manager.size()

            success = await self.queue_manager.put(request, priority=getattr(request, 'priority', 0))
            if success and retry_count > 0:
                self.logger.info(
                    f"Queue space available, resumed (waited {retry_count * 0.5:.1f}s, "
                    f"queue: {await self.queue_manager.size()}/{max_size})"
                )
            if success and hasattr(self.queue_manager, '_priority_calculator'):
                self.queue_manager._priority_calculator.update_crawl_frequency(request)
            return success
        except Exception as e:
            self.error_handler.handle_error(e, context=ErrorContext(context="Failed to enqueue request"), raise_error=False)
            return False

    # ============================
    # 空闲检查
    # ============================

    def idle(self) -> bool:
        """同步 idle 检查 — 内存队列精确，Redis 队列近似"""
        if not self.queue_manager:
            return True
        if self._is_memory_queue():
            return self.queue_manager.empty()
        # Redis 队列同步 empty 不可靠，返回 False 让调用方使用 async_idle
        return False

    async def async_idle(self) -> bool:
        """异步精确 idle 检查"""
        if not self.queue_manager:
            return True
        return await self.queue_manager.async_empty()

    # ============================
    # 大小获取
    # ============================

    async def async_size(self):
        """异步获取队列实际大小（推荐用于背压等精确场景）"""
        if not self.queue_manager:
            return 0
        return await self.queue_manager.size()

    def __len__(self):
        """
        同步近似大小 — 仅用于 idle() 判断和近似统计。

        内存队列可精确返回 qsize()；Redis 队列返回 0（实际大小请用 async_size()）。
        """
        if not self.queue_manager:
            return 0
        if self._is_memory_queue():
            # 内存队列可以直接获取同步大小
            inner = getattr(self.queue_manager, '_queue', None)
            if inner and hasattr(inner, 'qsize'):
                return inner.qsize()
        return 0

    # ============================
    # 生命周期
    # ============================

    async def close(self):
        """Close scheduler"""
        try:
            if isinstance(closed := getattr(self.dupe_filter, 'closed', None), Callable):
                await closed()
            if self.queue_manager:
                await self.queue_manager.close()
        except Exception as e:
            self.error_handler.handle_error(e, context=ErrorContext(context="Failed to close scheduler"), raise_error=False)

    async def ack_request(self, request):
        """确认请求处理完成（当前为空操作，任务出队时即认为完成）"""
        pass
