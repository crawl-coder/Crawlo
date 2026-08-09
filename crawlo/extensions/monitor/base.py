"""
Base Monitor Extension
======================
提供所有监控扩展的通用逻辑：配置检查、MonitorManager 注册、事件订阅、生命周期管理。
"""
import asyncio
import logging
from typing import Any, Optional, List, Tuple

from crawlo.event import CrawlerEvent
from crawlo.core.errors import NotConfigured
from crawlo.logging import get_logger
from crawlo.core.resource_scope import WeakBound
from .monitor_manager import get_monitor_manager


class BaseMonitorExtension:
    """
    监控扩展基类。

    子类只需覆盖以下类属性即可获得完整的 create_instance / spider_opened / spider_closed 逻辑：

        monitor_id: str          – MonitorManager 中的唯一标识（必填）
        config_key: str          – 启用开关的 settings key（必填）
        default_enabled: bool    – 默认是否启用（默认 False）
        extra_events: list       – 额外事件订阅 [(method_name, event), ...]

    子类还需要实现：
        _monitor_loop()          – 监控主循环协程
        _on_spider_closed_cleanup() – 关闭时的子类定制清理（可选）

    关键设计：crawler / settings 内部用 :class:`WeakBound` 弱引用包装，
    保证：即便 MonitorManager 在调度器模式下长期持有 monitor 实例，
    也不会因保留旧 Crawler 的强引用而导致内存泄漏。旧轮次的 Crawler
    被正常销毁后，self.crawler / self.settings 会自动返回 None。

    使用示例::

        class MyMonitor(BaseMonitorExtension):
            monitor_id = 'my_monitor'
            config_key = 'MY_MONITOR_ENABLED'

            async def _monitor_loop(self):
                while True:
                    # ... 监控逻辑 ...
                    await asyncio.sleep(self.interval)
    """

    # ---- 子类必须覆盖 ----
    monitor_id: str = ''
    config_key: str = ''
    default_enabled: bool = False

    # ---- 子类可选覆盖 ----
    extra_events: List[Tuple[str, CrawlerEvent]] = []

    def __init__(self, crawler: Any):
        # crawler / settings 改走弱引用 property，禁止子类直接写同名实例属性
        # （如果覆盖 property，要通过 self._bound = WeakBound(xxx) 重设）
        self._bound: Optional[WeakBound] = WeakBound(crawler)
        self.logger: logging.Logger = get_logger(self.__class__.__name__)
        self.task: Optional[asyncio.Task] = None
        self.enabled: bool = True

    # ---- crawler / settings 弱引用访问（property，referent GC 后自动返回 None） ----
    @property  # type: ignore[override]
    def crawler(self) -> Any:
        return self._bound.crawler if self._bound else None

    @crawler.setter
    def crawler(self, value: Any) -> None:
        if value is None:
            self._bound = None
        else:
            self._bound = WeakBound(value)

    @property
    def settings(self) -> Any:
        return self._bound.settings if self._bound else None

    @settings.setter
    def settings(self, value: Any) -> None:
        # settings setter 兼容：若子类需要单独覆盖 settings，构造一个伪 weakref
        # 这里保持极简：当且仅当已有 crawler 可推 settings 时忽略；否则直接构造一个
        # 不会阻止 GC 的空 bound（调度器场景无意义，主要兼容旧外部代码写 None 的情况）。
        if value is None:
            # 主动释放 → 把 bound 整个释放
            self._bound = None

    # ============================
    # 工厂方法
    # ============================

    @classmethod
    def create_instance(cls, crawler: Any) -> 'BaseMonitorExtension':
        """
        统一工厂方法：
        1. 检查配置开关
        2. 检测 MonitorManager 中是否已有实例
        3. 注册新实例并订阅事件
        """
        if not crawler.settings.get_bool(cls.config_key, cls.default_enabled):
            raise NotConfigured(f"{cls.__name__}: {cls.config_key} is not enabled")

        mm = get_monitor_manager()
        existing = mm.get_monitor(cls.monitor_id)
        if existing is not None:
            # 已有实例运行中，返回一个禁用的副本：
            # WeakBound 天然不持有 crawler/settings 强引用，不需要手动置 None
            instance = cls(crawler)
            instance.enabled = False
            return instance

        instance = cls(crawler)
        registered = mm.register_monitor(cls.monitor_id, instance)
        if registered:
            cls._subscribe_events(crawler, instance)
        return instance

    @classmethod
    def _subscribe_events(cls, crawler: Any, instance: 'BaseMonitorExtension') -> None:
        """订阅 opener / closer 及子类声明的额外事件"""
        crawler.subscriber.subscribe(instance.spider_opened, event=CrawlerEvent.SPIDER_OPENED)
        crawler.subscriber.subscribe(instance.spider_closed, event=CrawlerEvent.SPIDER_CLOSED)
        for method_name, event in cls.extra_events:
            if hasattr(instance, method_name):
                crawler.subscriber.subscribe(getattr(instance, method_name), event=event)

    # ============================
    # 生命周期
    # ============================

    async def spider_opened(self) -> None:
        """爬虫启动：非主实例或已禁用则跳过，否则启动监控循环"""
        if not self.enabled or get_monitor_manager().get_monitor(self.monitor_id) != self:
            return
        self.task = asyncio.create_task(self._monitor_loop())
        self.logger.info(f"{self.__class__.__name__} started (id={id(self)}).")

    async def spider_closed(self, **kwargs) -> None:
        """爬虫关闭：取消任务 → 子类自定义清理 → (调度器模式下保持注册, 普通模式注销)。

        WeakBound 已经保证 crawler/settings 不会阻 GC，这里仍主动释放 bound
        作为显式破环的二次兜底 + 让 self.logger 引用也能释放（logging 也有
        少量引用链）。
        """
        mm = get_monitor_manager()
        is_main_instance = (mm.get_monitor(self.monitor_id) == self)

        if is_main_instance:
            self._cancel_task()
            self._on_spider_closed_cleanup()

            if self._unregister_on_spider_closed:
                mm.unregister_monitor(self.monitor_id)
                self.logger.debug(f"{self.__class__.__name__} stopped and unregistered.")
            else:
                self.logger.info(f"{self.__class__.__name__} paused (scheduler mode, kept registered).")

        # 二次兜底破环
        self._bound = None
        self.logger = None  # type: ignore[assignment]

    def _cancel_task(self) -> None:
        """安全取消监控循环任务"""
        if self.task:
            self.task.cancel()
            # 在 spider_closed 回调中不能 await，这里做 best-effort
            self.task = None

    def _on_spider_closed_cleanup(self) -> None:
        """
        子类定制清理钩子，在任务取消后、注销前调用。
        例如：清除趋势历史、重置基准线等。
        """

    # ============================
    # 抽象监控循环
    # ============================

    async def _monitor_loop(self) -> None:
        """监控循环（子类必须实现）"""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _monitor_loop()"
        )

    # ============================
    # 工具方法
    # ============================

    @property
    def is_scheduler_mode(self) -> bool:
        """检测是否在调度器模式下运行（设置不存在时返回 False）。"""
        settings = self.settings
        return bool(settings and settings.get_bool('_INTERNAL_SCHEDULER_TASK', False))

    @property
    def _unregister_on_spider_closed(self) -> bool:
        """调度器模式下保持注册以跨 job 复用；普通模式注销释放资源"""
        return not self.is_scheduler_mode
