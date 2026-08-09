# -*- coding: utf-8 -*-
"""
共享资源作用域（ResourceScope）
================================

两个长期稳定场景的统一抽象：

  场景 1）同项目多爬虫并发：
      所有爬虫共享 MySQL/Redis/Mongo 等 pool；等「最后一个爬虫」退出，
      才通过 release_pool() 触发 ref_count 归 0 真正关闭。
      → 这里是 CrawlerProcess / Scheduler 内部的「并发组作用域」。

  场景 2）定时任务长期运行（月/年级别）：
      同一 CrawlerProcess / Scheduler 会反复跑一轮又一轮，每轮开始 acquire 共享
      pool、每轮结束 release（但 ref_count 不一定归零，因为下一轮 30s 后又要）。
      内存 / 对象 / 连接数不能随轮数线性增长：
        - 所有 Crawler / Pipeline 等必须在每轮末尾破环（=None），
          见 crawler/_crawler.py & pipelines/manager.py
        - 对象计数器（ObjectCounter）按类型上限报警 + 每轮打印趋势；
        - PoolGroup.stats 快照对比：某轮 baseline vs 当轮，超阈值 log ERROR；
        - 对不参与 ref_count 的「轻量持有引用」改 weakref（MonitorExtension
          settings/crawler 引用、MonitorManager 等），消除人忘记手动 =None 的风险。

对外最常用的两个 API：

  .. code-block:: python

      # 并发组作用域：多个爬虫共享资源，等所有爬虫结束统一释放
      async with shared_resource_scope("concurrent-group") as scope:
          results = await asyncio.gather(
              scope.crawl('a'),
              scope.crawl('b'),
              scope.crawl('c'),
          )
      # 退出时：scope 等所有 CrawlerProcess 的 crawler.close() 全部
      # 结束后再一次性对 PoolGroup 中仍有 ref_count > 0 的 pool 做
      # release_pool * N 次？不对：ref_count 是各 Crawler.Pipeline 的
      # acquire/release 配对，scope 只保证「最后一个爬虫结束后不再有
      # 新的 acquire，然后兜底 release 所有 RuntimeContext.connection_pools」。

      # 长期调度作用域：每轮结束自检泄漏
      scheduler_scope = get_scheduler_resource_scope()
      scheduler_scope.on_iteration_end_hook(print_leak_report)
"""

from __future__ import annotations

import asyncio
import gc
import logging
import threading
import weakref
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Deque,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
)

from crawlo.logging import get_logger

# ------------------------------------------------------------------
# 1. ObjectCounter — 长期运行下按 GC 类型累计计数 + 超阈值告警
# ------------------------------------------------------------------


class ObjectCounter:
    """按类型统计 gc.objects 中存活数，适合「每轮结束 vs baseline」对比。"""

    MAX_HISTORY = 30

    def __init__(self, watch_types: Iterable[str]) -> None:
        self.watch_types: Set[str] = set(watch_types)
        self._baseline: Dict[str, int] = {}
        self._history: Deque[Dict[str, int]] = deque(maxlen=self.MAX_HISTORY)

    def snapshot(self) -> Dict[str, int]:
        counts: Dict[str, int] = defaultdict(int)
        for obj in gc.get_objects():
            name = type(obj).__name__
            if name in self.watch_types:
                counts[name] += 1
        snap = dict(counts)
        self._history.append(snap)
        return snap

    def set_baseline(self) -> Dict[str, int]:
        self._baseline = self.snapshot()
        return dict(self._baseline)

    def delta(self) -> Dict[str, int]:
        cur = self.snapshot()
        keys = set(cur) | set(self._baseline)
        return {k: cur.get(k, 0) - self._baseline.get(k, 0) for k in keys}

    def linear_slopes(self) -> Dict[str, float]:
        """对历史 15 个以上点做最小二乘斜率"""
        slopes: Dict[str, float] = {}
        if len(self._history) < 4:
            return slopes
        hist = list(self._history)
        keys: Set[str] = set()
        for s in hist:
            keys.update(s.keys())
        n = len(hist)
        xs = list(range(n))
        mx = sum(xs) / n
        for k in keys:
            ys = [s.get(k, 0) for s in hist]
            my = sum(ys) / n
            num = 0.0
            den = 0.0
            for x, y in zip(xs, ys):
                num += (x - mx) * (y - my)
                den += (x - mx) ** 2
            slopes[k] = (num / den) if den else 0.0
        return slopes


# ------------------------------------------------------------------
# 2. PoolStats — 数据库/连接池级别快照
# ------------------------------------------------------------------


@dataclass
class PoolSnapshot:
    """pool_count 是管理器里的实例数；conns 是所有 pool 的 size 之和（活跃+空闲）。"""

    mysql_pools: int = 0
    mysql_conns: int = 0
    redis_pools: int = 0
    mongo_pools: int = 0
    mongo_clients: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)

    def __sub__(self, other: 'PoolSnapshot') -> 'PoolSnapshot':
        return PoolSnapshot(
            mysql_pools=self.mysql_pools - other.mysql_pools,
            mysql_conns=self.mysql_conns - other.mysql_conns,
            redis_pools=self.redis_pools - other.redis_pools,
            mongo_pools=self.mongo_pools - other.mongo_pools,
            mongo_clients=self.mongo_clients - other.mongo_clients,
            extra={k: self.extra.get(k) for k in set(self.extra) | set(other.extra)},
        )


def capture_pool_snapshot() -> PoolSnapshot:
    snap = PoolSnapshot()
    try:
        from crawlo.utils.db.mysql_connection_pool import MySQLConnectionPoolManager
        stats = MySQLConnectionPoolManager.get_pool_stats()
        snap.mysql_pools = stats.get('total_pools', 0)
        for info in stats.get('pools', {}).values():
            snap.mysql_conns += info.get('size', 0)
    except Exception:
        pass
    try:
        from crawlo.utils.redis.pool import _resolve_runtime_context
        ctx = _resolve_runtime_context()
        snap.redis_pools = len(ctx.connection_pools)
    except Exception:
        pass
    try:
        from crawlo.utils.db.mongo_connection_pool import MongoConnectionPoolManager
        m_stats = MongoConnectionPoolManager.get_pool_stats()
        snap.mongo_pools = m_stats.get('total_clients', 0)
        snap.mongo_clients = m_stats.get('total_clients', 0)
    except Exception:
        pass
    return snap


# ------------------------------------------------------------------
# 3. Memory RSS 捕获
# ------------------------------------------------------------------


def rss_mb(pid: Optional[int] = None) -> float:
    try:
        import psutil  # type: ignore
        return psutil.Process(pid or os.getpid()).memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0


import os  # noqa: E402  (rss_mb 需要，保证在 import 底部)


# ------------------------------------------------------------------
# 4. ResourceScope — 并发共享作用域 & 长期调度作用域
# ------------------------------------------------------------------


ScopeHook = Callable[['ResourceScope', str], Awaitable[None] | None]


class ResourceScope:
    """
    共享资源生命周期容器。

    Usage (并发组)::

        scope = ResourceScope(mode='concurrent', name='batch-1')
        await scope.acquire_all()  # (预连接，可选)
        try:
            await asyncio.gather(
                CrawlerProcess().crawl('a'),
                CrawlerProcess().crawl('b'),
            )
        finally:
            await scope.release_all()

    Usage (长期调度器模式 - 推荐 hook 在每轮结束)::

        scope = ResourceScope(mode='scheduler', name='daily-import',
                              watch_types={'Crawler','PipelineManager','AioHttpDownloader'},
                              iteration_warn_slope={'Crawler': 0.3})
        for round in range(10_000):
            await CrawlerProcess().crawl('a')
            # 每轮末尾：破环 + 计 snapshot + 斜率报警
            await scope.on_iteration_end(f"R{round}")
        await scope.close()
    """

    def __init__(
        self,
        mode: str = 'concurrent',
        name: str = 'default',
        watch_types: Optional[Iterable[str]] = None,
        iteration_warn_slope: Optional[Dict[str, float]] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        assert mode in ('concurrent', 'scheduler'), "mode ∈ {'concurrent','scheduler'}"
        self.mode = mode
        self.name = name
        self._closed = False
        self.logger = logger or get_logger(f'ResourceScope.{mode}.{name}')

        self._hooks_after_iteration: List[ScopeHook] = []
        self._iteration_count = 0

        # ObjectCounter baseline (scheduler 模式每轮会更新快照)
        default_watch = {
            'Crawler', 'CrawlerProcess', 'PipelineManager',
            'MySQLPipeline', 'AioHttpDownloader', 'AioRedisFilter',
            'SchedulerDaemon', 'MySQLExistsChecker', 'BaseMonitorExtension',
            'EventloopLagProbe', 'HealthCheckExtension',
        }
        if watch_types:
            default_watch |= set(watch_types)
        self.counter = ObjectCounter(default_watch)
        self._iteration_warn_slope = dict(iteration_warn_slope or {})
        # 默认合理斜率阈值：每个关键对象不应该随轮数线性 +1
        for t in default_watch:
            self._iteration_warn_slope.setdefault(t, 0.2)

        self._pool_baseline: Optional[PoolSnapshot] = None
        self._rss_baseline_mb: float = 0.0

    # ----- hooks -----

    def on_iteration_end_hook(self, fn: ScopeHook) -> None:
        self._hooks_after_iteration.append(fn)

    # ----- concurrent 模式 API -----

    async def acquire_all(self) -> None:
        """提前初始化共享资源（通常不需要，懒加载也 OK）。"""
        self._pool_baseline = capture_pool_snapshot()
        self._rss_baseline_mb = rss_mb()
        self.logger.debug(
            f"acquire_all baseline pools={self._pool_baseline} rss={self._rss_baseline_mb:.1f}MB"
        )

    async def release_all(self, force_close_pools: bool = False) -> None:
        """并发组所有爬虫结束后调用。

        Args:
            force_close_pools: 当 mode='concurrent' 且程序准备退出时传 True，
                绕过 ref_count 直接 close_all_pools，保证进程无残留连接。
                scheduler 长期运行模式禁止传 True（会关掉下一轮要用的共享池）。
        """
        if self._closed:
            return
        gc.collect()
        gc.collect()
        after = capture_pool_snapshot()
        rss_now = rss_mb()
        base = self._pool_baseline or PoolSnapshot()
        delta = after - base
        self.logger.info(
            f"release_all({self.mode}/{self.name}): "
            f"MySQLP={after.mysql_pools}(Δ{delta.mysql_pools:+}) MySQLC={after.mysql_conns}(Δ{delta.mysql_conns:+}) "
            f"RedisP={after.redis_pools}(Δ{delta.redis_pools:+}) "
            f"RSS={rss_now:.0f}MB(Δ{rss_now-self._rss_baseline_mb:+.0f}MB)"
        )
        if force_close_pools:
            await self._force_close_all_pools()
        self._closed = True

    @staticmethod
    async def _force_close_all_pools() -> None:
        errors: list[str] = []
        try:
            from crawlo.utils.db.mysql_connection_pool import close_all_mysql_pools
            await close_all_mysql_pools()
        except Exception as e:
            errors.append(f"mysql: {e}")
        try:
            from crawlo.utils.redis import close_all_pools
            await close_all_pools()
        except Exception as e:
            errors.append(f"redis: {e}")
        try:
            from crawlo.utils.db.mongo_connection_pool import close_all_mongo_clients
            await close_all_mongo_clients()
        except Exception as e:
            # pymongo/pyopenssl 版本不兼容（例如 cryptography 42+ vs pyopenssl<23.2 导致
            # AttributeError: module 'lib' has no attribute 'GEN_EMAIL'）。进程马上退出，mongo
            # 连接不阻塞退出，记 warning 即可，不要 raise 影响正常收尾。
            errors.append(f"mongo: {e}")
            import logging as _logging
            _logging.getLogger('ResourceScope').warning(
                f"force_close_all_pools: mongo skipped: {e}"
            )
        if errors:
            # 其它模块错误也记 warning。force_close 语义是「尽最大努力释放」，它的异常
            # 不应该影响上层。
            import logging as _logging2
            _logging2.getLogger('ResourceScope').warning(
                f"force_close_all_pools: {errors}"
            )

    # ----- scheduler 长期运行模式 API -----

    def start(self) -> None:
        """调度器启动时拍 baseline。"""
        self.counter.set_baseline()
        self._pool_baseline = capture_pool_snapshot()
        self._rss_baseline_mb = rss_mb()
        self.logger.info(
            f"scheduler scope started baseline: pools_baseline={self._pool_baseline} "
            f"rss_baseline={self._rss_baseline_mb:.0f}MB"
        )

    async def on_iteration_end(self, tag: str = '') -> Dict[str, Any]:
        """每一轮调度结束后调用（破环 gc、拍快照、斜率告警）。"""
        self._iteration_count += 1
        # 破环：先推进事件循环让 asyncio 的 Task done callbacks 被执行完毕
        # （完成的 Task 仍然持有 result/coro frame 引用，会延迟 Crawler GC）
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        # 再跨两代 GC（含老年代 full collection）
        gc.collect(2)
        gc.collect()
        gc.collect()
        # 再推一轮 loop：让 any 延迟的 finalizer / weakref callback 执行完毕
        await asyncio.sleep(0.01)
        gc.collect(2)

        counts = self.counter.snapshot()
        deltas = self.counter.delta()
        slopes = self.counter.linear_slopes()
        pool_now = capture_pool_snapshot()
        pool_delta = (
            pool_now - self._pool_baseline if self._pool_baseline else PoolSnapshot()
        )
        rss_now = rss_mb()

        warn_msgs: List[str] = []
        for t, threshold in self._iteration_warn_slope.items():
            s = slopes.get(t, 0.0)
            d = deltas.get(t, 0)
            if s > threshold or d > max(5, threshold * 10):
                warn_msgs.append(
                    f"{t}: slope={s:+.3f}/轮(阈值 {threshold}) Δ={d:+}"
                )
        # pool 增量告警
        if pool_delta.mysql_pools > 2:
            warn_msgs.append(f"MySQL pools Δ={pool_delta.mysql_pools:+} (>2)")
        if pool_delta.mysql_conns > 20:
            warn_msgs.append(f"MySQL conns Δ={pool_delta.mysql_conns:+} (>20)")
        # RSS 每百轮斜率告警（粗粒度）
        if (
            self._rss_baseline_mb
            and self._iteration_count >= 5
            and (rss_now - self._rss_baseline_mb) / self._iteration_count > 3.0
        ):
            warn_msgs.append(
                f"RSS 平均增长 {(rss_now-self._rss_baseline_mb)/self._iteration_count:+.1f}MB/轮 (>3MB)"
            )

        report: Dict[str, Any] = {
            'scope': f"{self.mode}/{self.name}",
            'iter': self._iteration_count,
            'tag': tag,
            'counts': counts,
            'delta_baseline': deltas,
            'slopes_per_iter': slopes,
            'pools_now': {
                'mysql_pools': pool_now.mysql_pools, 'mysql_conns': pool_now.mysql_conns,
                'redis_pools': pool_now.redis_pools, 'mongo_clients': pool_now.mongo_clients,
            },
            'pools_delta_baseline': {
                'mysql_pools': pool_delta.mysql_pools, 'mysql_conns': pool_delta.mysql_conns,
                'redis_pools': pool_delta.redis_pools, 'mongo_clients': pool_delta.mongo_clients,
            },
            'rss_now_mb': round(rss_now, 1),
            'rss_delta_baseline_mb': round(rss_now - self._rss_baseline_mb, 1),
            'warnings': warn_msgs,
        }
        if warn_msgs:
            self.logger.error(
                f"[{tag}] ⚠️ 疑似资源泄漏！warnings={warn_msgs}\n  report={report}"
            )
        else:
            self.logger.info(
                f"[{tag or f'R{self._iteration_count}'}] OK "
                f"RssΔ={report['rss_delta_baseline_mb']:+}MB "
                f"MySQLC={report['pools_now']['mysql_conns']} "
                f"(Δ{report['pools_delta_baseline']['mysql_conns']:+}) "
                f"CrawlerΔ={deltas.get('Crawler',0):+} PipeMgrΔ={deltas.get('PipelineManager',0):+}"
            )
        # 调用自定义 hooks
        for fn in list(self._hooks_after_iteration):
            try:
                r = fn(self, tag)
                if hasattr(r, '__await__'):
                    await r
            except Exception as e:
                self.logger.warning(f"iteration hook {fn!r} failed: {e}")
        return report

    async def close(self) -> None:
        """进程退出前 cleanup：scheduler 模式 force close pools。"""
        if self.mode == 'scheduler':
            await self.release_all(force_close_pools=True)
        else:
            await self.release_all(force_close_pools=True)
        self._closed = True


# ------------------------------------------------------------------
# 5. WeakBound — weakref 改造的「持有 crawler/settings 不阻 GC」包装
#    （用于 BaseMonitorExtension 等长期存活对象）
# ------------------------------------------------------------------


class WeakBound:
    """
    弱引用包装 crawler/settings，避免「MonitorExtension 禁用副本」「暂停中 monitor」
    持有旧 Crawler 导致无法 GC。属性访问时若 referent 已释放返回 None。

    Usage::

        class BaseMonitorExtension:
            def __init__(self, crawler):
                b = WeakBound(crawler)
                self._bound = b
            @property
            def crawler(self): return self._bound.crawler
            @property
            def settings(self): return self._bound.settings
    """

    __slots__ = ('_crawler_ref', '_settings_ref')

    def __init__(self, crawler: Any) -> None:
        self._crawler_ref = weakref.ref(crawler, self._finalize)
        self._settings_ref = weakref.ref(getattr(crawler, 'settings', None) or (lambda: None))

    @staticmethod
    def _finalize(_ref: weakref.ReferenceType) -> None:
        # weakref callback 不做事（仅方便将来加日志），保持空
        return None

    @property
    def crawler(self) -> Any:
        r = self._crawler_ref()
        return r if r is not None else None

    @property
    def settings(self) -> Any:
        s = self._settings_ref()
        return s() if callable(s) else s


# ------------------------------------------------------------------
# 6. 模块级便捷入口
# ------------------------------------------------------------------


@asynccontextmanager
async def shared_resource_scope(
    name: str = 'batch',
    **kw: Any,
) -> AsyncGenerator[ResourceScope, None]:
    """
    最推荐的并发 API：async with 保证 release 兜底。

    ::

        async with shared_resource_scope('3-spiders-batch') as scope:
            cp = CrawlerProcess()
            await asyncio.gather(cp.crawl('a'), cp.crawl('b'), cp.crawl('c'))
    """
    scope = ResourceScope(mode='concurrent', name=name, **kw)
    await scope.acquire_all()
    try:
        yield scope
    finally:
        await scope.release_all(force_close_pools=False)


_scheduler_scope_lock = threading.Lock()
_global_scheduler_scope: Optional[ResourceScope] = None


def get_scheduler_resource_scope(
    name: str = 'scheduler',
    **kw: Any,
) -> ResourceScope | None:
    """调度器内全局作用域单例（每轮结束都调 on_iteration_end）。"""
    global _global_scheduler_scope
    with _scheduler_scope_lock:
        if _global_scheduler_scope is None:
            _global_scheduler_scope = ResourceScope(mode='scheduler', name=name, **kw)
            _global_scheduler_scope.start()
    return _global_scheduler_scope


__all__ = [
    'ObjectCounter',
    'PoolSnapshot',
    'capture_pool_snapshot',
    'rss_mb',
    'ResourceScope',
    'WeakBound',
    'shared_resource_scope',
    'get_scheduler_resource_scope',
]
