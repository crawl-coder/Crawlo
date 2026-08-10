#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Scheduler — 请求调度器

负责请求队列管理、去重过滤、Redis/Memory 双模式自动切换。
"""
import traceback
from typing import Optional, Callable

from crawlo.logging import get_logger
from crawlo.project import common_call
from crawlo.utils.misc import load_object, safe_get_config
from crawlo.utils.request import set_request
from crawlo.utils.errors import ErrorHandler, ErrorContext
from crawlo.utils.request.request_serializer import RequestSerializer
from crawlo.queue.queue_manager import QueueManager
from crawlo.queue.config import QueueConfig
from crawlo.queue.queue_types import QueueType
from crawlo.queue.task_tracker import TaskResult
from crawlo.queue.exceptions import QueueFullTimeout

# ---- 配置常量（统一管理，消除重复） ----
_DEFAULT_QUEUE_TYPE = 'memory'
_DEFAULT_FILTER_CLASS = 'crawlo.filters.MemoryFilter'
_DEFAULT_REDIS_FILTER_CLASS = 'crawlo.filters.AioRedisFilter'
_DEFAULT_DEDUP_MEMORY = 'crawlo.pipelines.MemoryDedupPipeline'
_DEFAULT_DEDUP_REDIS = 'crawlo.pipelines.RedisDedupPipeline'
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
    QueueType.REDIS_STREAM: {
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
        self._duplicate_filtered_count = 0

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
            except Exception as e:
                self.logger.debug("Suppressed exception: %s", e)

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
        return self.queue_type in (QueueType.REDIS, QueueType.REDIS_STREAM)

    def _is_stream_queue(self) -> bool:
        return self.queue_type == QueueType.REDIS_STREAM

    @property
    def pending_enqueue_count(self) -> int:
        """正在阻塞等待入队的请求数（委托给 QueueManager）。

        Engine idle 判定通过此属性感知是否有 put 在 block 等待。
        """
        if self.queue_manager and hasattr(self.queue_manager, 'pending_enqueue_count'):
            return self.queue_manager.pending_enqueue_count
        return 0

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
                except Exception as e:
                    self.logger.debug("Suppressed exception: %s", e)

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
        if self._is_redis_queue():  # includes REDIS and REDIS_STREAM
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
            self._swap_dedup_in_pipelines(default_dedup, str(config['dedup_pipeline']))
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
            request = await self.queue_manager.get()
            # notify 逻辑已下沉到 QueueManager.get（_notify_space_available）
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

    async def next_request_blocking(self, timeout: float = 30.0):
        """阻塞式获取下一个请求（分布式模式专用）"""
        if not self.queue_manager:
            return None
        try:
            # notify 逻辑已下沉到 QueueManager.get_blocking
            request = await self.queue_manager.get_blocking(timeout=timeout)
            return request
        except Exception as e:
            self.error_handler.handle_error(
                e, context=ErrorContext(context="阻塞获取请求失败"), raise_error=False
            )
            return None

    async def enqueue_request(self, request):
        """Add request to queue with dedup check.

        背压双层合并后，等待策略下沉到 ``QueueManager.put``。
        本方法只负责：去重 → 转发 put → 按 ``ENQUEUE_FULL_POLICY`` 处理 ``QueueFullTimeout``。

        策略说明（见 ``default_settings.py``）：
            - ``block``            : 无限等待（受 ``ENQUEUE_BLOCK_TIMEOUT`` 上限约束），超时按 drop 处理
            - ``drop_with_counter``: 超时丢弃并递增 ``scheduler/enqueue_dropped_count``（默认）
            - ``raise``            : 超时抛 ``QueueFullTimeout`` 给上层
        """
        # 去重检查
        if not request.dont_filter:
            if hasattr(self.dupe_filter, 'requested_async'):
                is_duplicate = await self.dupe_filter.requested_async(request)
            else:
                is_duplicate = await common_call(self.dupe_filter.requested, request)
            if is_duplicate:
                self.dupe_filter.log_stats(request)
                self._duplicate_filtered_count += 1
                self.logger.debug(f"Filtered duplicate request: {request.url}")
                return False

        if not self.queue_manager:
            self.logger.error("Queue manager not initialized")
            return False

        set_request(request, self.priority)

        # 根据 ENQUEUE_FULL_POLICY 决定 put 的 timeout
        policy = self._get_enqueue_full_policy()
        put_timeout = self._resolve_put_timeout(policy)

        try:
            success = await self.queue_manager.put(
                request, priority=getattr(request, 'priority', 0), timeout=put_timeout
            )
            if success and hasattr(self.queue_manager, '_priority_calculator'):
                self.queue_manager._priority_calculator.update_crawl_frequency(request)
            return success
        except QueueFullTimeout as e:
            return await self._handle_queue_full_timeout(e, request, policy)

    def _get_enqueue_full_policy(self) -> str:
        """读取入队满策略配置"""
        # 优先从 QueueConfig 读取（已注入），回退到 settings
        if self.queue_manager and hasattr(self.queue_manager, 'config'):
            cfg = self.queue_manager.config
            if hasattr(cfg, 'enqueue_full_policy'):
                return cfg.enqueue_full_policy
        return self._get_setting('ENQUEUE_FULL_POLICY', 'drop_with_counter')

    def _resolve_put_timeout(self, policy: str):
        """根据策略解析 put 的 timeout 参数。

        - ``block``            : ENQUEUE_BLOCK_TIMEOUT（默认 None=无限）
        - ``drop_with_counter``: ENQUEUE_DROP_TIMEOUT（默认 50.0s，匹配旧行为 100×0.5s）
        - ``raise``            : ENQUEUE_DROP_TIMEOUT（同上，需有限超时才有意义）
        """
        if self.queue_manager and hasattr(self.queue_manager, 'config'):
            cfg = self.queue_manager.config
            if policy == 'block':
                return getattr(cfg, 'enqueue_block_timeout', None)
            else:
                # drop_with_counter / raise
                return getattr(cfg, 'enqueue_drop_timeout', 50.0)
        # settings 回退
        if policy == 'block':
            return self._get_setting('ENQUEUE_BLOCK_TIMEOUT', None)
        return self._get_setting('ENQUEUE_DROP_TIMEOUT', 50.0)

    async def _handle_queue_full_timeout(self, error: QueueFullTimeout, request, policy: str) -> bool:
        """按 ENQUEUE_FULL_POLICY 处理队列满超时。

        - ``block``            : 理论上不应超时（除非 ENQUEUE_BLOCK_TIMEOUT 非 None），按 drop 兜底
        - ``drop_with_counter``: 记日志 + 递增统计 + return False
        - ``raise``            : 向上抛出
        """
        if policy == 'raise':
            # 不吞错，交给上层决策
            raise

        # block / drop_with_counter：记录并丢弃
        self.logger.error(
            f"Queue full timeout (waited {error.waited_seconds:.1f}s, "
            f"size={error.queue_size}/{error.max_size}), dropping request: {request.url}"
        )
        if self.stats is not None:
            try:
                self.stats.inc_value('scheduler/enqueue_dropped_count')
            except Exception as e:
                self.logger.debug("Suppressed exception: %s", e)
        return False

    # ============================
    # 空闲检查
    # ============================

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

    def __bool__(self) -> bool:
        """Scheduler 实例永远为真。"""
        return True

    # ============================
    # 生命周期
    # ============================

    async def close(self):
        """Close scheduler"""
        try:
            self.logger.info(
                f"Filtered {self._duplicate_filtered_count} duplicate request(s) in total"
            )
            if isinstance(closed := getattr(self.dupe_filter, 'closed', None), Callable):
                await closed()
            if self.queue_manager:
                await self.queue_manager.close()
        except Exception as e:
            self.error_handler.handle_error(e, context=ErrorContext(context="Failed to close scheduler"), raise_error=False)

    async def next_request_with_ack(self):
        """
        带 ACK 语义的出队（REDIS_STREAM 模式专用）。

        Returns:
            (request, receipt) 或 (None, None)
            receipt 用于后续 ack_request / nack_request 调用
        """
        if not self.queue_manager:
            return (None, None)

        # Stream 队列：使用带 receipt 的出队
        if self._is_stream_queue():
            if hasattr(self.queue_manager._queue, 'get_with_receipt'):
                result = await self.queue_manager._queue.get_with_receipt(timeout=30.0)
                if result:
                    request, message_id = result
                    if request:
                        try:
                            spider = getattr(self.crawler, 'spider', None)
                            request = self.request_serializer.restore_after_deserialization(request, spider)
                        except Exception as deser_error:
                            self.logger.error(
                                f"[队列] 请求反序列化失败: {deser_error}"
                            )
                            return (None, None)
                        return (request, message_id)
                return (None, None)

        # 非 Stream 队列：退化为普通出队，receipt = None
        request = await self.next_request()
        return (request, None)

    async def ack_request(self, request_or_receipt):
        """
        确认请求处理完成。

        REDIS_STREAM 模式：XACK 确认消息
        REDIS ZSET 模式：空操作（任务出队时即认为完成）
        Memory 模式：空操作
        """
        # Stream 队列：XACK
        if self._is_stream_queue():
            if isinstance(request_or_receipt, str) and request_or_receipt:
                # receipt = message_id
                if hasattr(self.queue_manager._queue, 'ack'):
                    await self.queue_manager._queue.ack(request_or_receipt)
            elif hasattr(request_or_receipt, 'url'):
                # 老式 Request 对象，尝试从 meta 获取 message_id
                message_id = getattr(request_or_receipt, 'meta', {}).get('__stream_message_id')
                if message_id and hasattr(self.queue_manager._queue, 'ack'):
                    await self.queue_manager._queue.ack(message_id)

    async def nack_request(self, receipt, reason: str = 'failed', result: TaskResult = TaskResult.RETRY):
        """
        确认请求处理失败。

        REDIS_STREAM 模式：根据 result 决定重试/死信/XACK
        其他模式：空操作
        """
        if not self._is_stream_queue():
            return

        if not receipt:
            return

        if not self.queue_manager:
            return

        if hasattr(self.queue_manager._queue, 'nack'):
            await self.queue_manager._queue.nack(receipt, error=reason, result=result)
        """确认请求处理完成（当前为空操作，任务出队时即认为完成）"""
