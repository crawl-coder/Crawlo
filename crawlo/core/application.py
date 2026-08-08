#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
ApplicationContext — 框架全局状态统一容器
==========================================

通过 get_global_context() 访问单例上下文，替代分散的模块级全局变量。
reset_global_context() / set_global_context() 用于测试隔离和高级用例。

Phase 4 Step 1：将原 36 字段大杂烩容器拆分为三个内聚子上下文（组合）：
    - RegistryContext      核心注册表
    - NotificationContext  Bot 通知
    - RuntimeContext       框架管理器 + MCP/工具 + 通用

所有旧字段名通过 @property 委托到子上下文，保持 100% 向后兼容。

Phase 8 Step 8.2：ApplicationCotnext.__post_init__ 把三个子上下文 + 已非 None 的常用
单例注册进 crawlo.container.default_container，为后续 @inject 构造器注入做准备。
"""
from __future__ import annotations

import asyncio
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Type

from crawlo.logging import get_logger


@dataclass
class RegistryContext:
    """核心注册表子上下文。"""

    spider_registry: Dict[str, Type['Spider']] = field(default_factory=dict)
    component_registry: Optional['ComponentRegistry'] = None
    initializer_registry: Optional['InitializerRegistry'] = None
    job_registry: Optional['JobRegistry'] = None
    framework: Optional['CrawloFramework'] = None
    components_registered: bool = False


@dataclass
class NotificationContext:
    """Bot 通知子上下文。"""

    notifier: Optional['NotificationDispatcher'] = None
    notifier_lock: Any = field(default_factory=threading.Lock)
    notification_handler: Optional['CrawlerNotificationHandler'] = None
    notification_handler_lock: Any = field(default_factory=threading.Lock)
    template_manager: Optional['MessageTemplateManager'] = None
    resource_monitor_manager: Optional['ResourceMonitorTemplateManager'] = None
    deduplicator: Optional['MessageDeduplicator'] = None
    deduplicator_lock: Any = field(default_factory=threading.Lock)
    bot_config_loaded: bool = False
    dingtalk_channel: Optional['DingTalkChannel'] = None
    feishu_channel: Optional['FeishuChannel'] = None
    wecom_channel: Optional['WeComChannel'] = None
    email_channel: Optional['EmailChannel'] = None
    sms_channel: Optional['SmsChannel'] = None


@dataclass
class RuntimeContext:
    """框架管理器 + MCP/工具 + 通用子上下文。"""

    error_handler_instance: Optional['ErrorHandler'] = None
    performance_monitor: Optional['PerformanceMonitor'] = None
    resource_managers: Dict[str, Any] = field(default_factory=dict)
    _monitor_manager: Optional['MonitorManager'] = None
    quick_fetcher: Optional['QuickFetcher'] = None
    mcp_fetcher: Optional['QuickFetcher'] = None
    mcp_fetcher_lock: Any = field(default_factory=threading.Lock)
    redis_manager: Optional['GlobalRedisManager'] = None
    connection_pools: Dict[str, Any] = field(default_factory=dict)
    queue_error_handler: Optional['ErrorHandler'] = None
    resources: Set[Any] = field(default_factory=set)
    crawlers: Dict[str, Any] = field(default_factory=dict)
    # Phase 4 Step 3：CoreInitializer 实例挂 ctx（facade 走 ctx，SingletonMeta 兜底）
    initializer: Optional['CoreInitializer'] = None


@dataclass
class ApplicationContext:
    """框架全局状态容器，持有所有组件单例引用，支持上下文隔离。

    Phase 4 Step 1：组合三个内聚子上下文，旧字段名通过 @property 委托
    保持 100% 向后兼容（外部代码无需修改）。
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    registries: RegistryContext = field(default_factory=RegistryContext)
    notifications: NotificationContext = field(default_factory=NotificationContext)
    runtime: RuntimeContext = field(default_factory=RuntimeContext)

    def __post_init__(self) -> None:
        """Phase 8 Step 8.2：ApplicationContext 创建后，把子上下文挂进 DI 容器。

        这是 ``default_container`` 唯一的业务注册入口：之后 35 处 ``get_global_context()``
        调用点可逐步改造成构造器注入（``@inject`` + 类型注解）。
        """
        try:
            self._bind_to_container()
        except Exception as exc:  # pragma: no cover - 防御式：绑定失败不应影响 ctx 本身正常工作
            get_logger(__name__).warning(
                f"ApplicationContext._bind_to_container failed (continuing): {exc}", exc_info=True,
            )

    def _bind_to_container(self) -> None:
        """把三个子上下文实例 + 公共资源类型注册进 :data:`default_container`。

        注册分三层：
        1. 子上下文整体（RegistryContext / NotificationContext / RuntimeContext / ApplicationContext）
        2. 常用直接实例（非 None 的常用单例，如 notifications.notifier / runtime.redis_manager 等）
        3. 间接引用：当某实例被延迟创建后，可用 ``rebind_to_container(instance, cls)`` 追加
        """
        # 延迟导入：避免 crawlo.core.application 在 import 期反向依赖 crawlo.container
        from crawlo.container import default_container, Scope

        # 1. 子上下文整体（SINGLETON：进程内全局）
        default_container.register_instance(ApplicationContext, self)
        default_container.register_instance(RegistryContext, self.registries)
        default_container.register_instance(NotificationContext, self.notifications)
        default_container.register_instance(RuntimeContext, self.runtime)

        # 2. 直接实例（已存在时注册；延迟创建的组件后续通过 rebind_* 方法补充）
        n = self.notifications
        if n.notifier is not None:
            try:
                from crawlo.bot.core.notifier import NotificationDispatcher  # noqa: WPS433
                default_container.register_instance(NotificationDispatcher, n.notifier)
            except Exception:  # noqa: S110  Bot 模块未安装时跳过
                pass
        if n.template_manager is not None:
            try:
                from crawlo.bot.templates.manager import MessageTemplateManager  # noqa: WPS433
                default_container.register_instance(MessageTemplateManager, n.template_manager)
            except Exception:  # noqa: S110
                pass
        if n.deduplicator is not None:
            try:
                from crawlo.bot.utils.deduplicator import MessageDeduplicator  # noqa: WPS433
                default_container.register_instance(MessageDeduplicator, n.deduplicator)
            except Exception:  # noqa: S110
                pass
        # 5 个 channel 类非 None → 注册
        self._rebind_channel("dingtalk", n.dingtalk_channel)
        self._rebind_channel("feishu", n.feishu_channel)
        self._rebind_channel("wecom", n.wecom_channel)
        self._rebind_channel("email", n.email_channel)
        self._rebind_channel("sms", n.sms_channel)

        r = self.runtime
        if r.error_handler_instance is not None:
            try:
                from crawlo.utils.errors import ErrorHandler  # noqa: WPS433
                default_container.register_instance(ErrorHandler, r.error_handler_instance)
            except Exception:  # noqa: S110
                pass
        if r.performance_monitor is not None:
            try:
                from crawlo.extension.monitor.performance_monitor import PerformanceMonitor  # noqa: WPS433
                default_container.register_instance(PerformanceMonitor, r.performance_monitor)
            except Exception:  # noqa: S110
                pass
        if r._monitor_manager is not None:  # noqa: SLF001
            try:
                from crawlo.extension.monitor.monitor_manager import MonitorManager  # noqa: WPS433
                default_container.register_instance(MonitorManager, r._monitor_manager)  # type: ignore[arg-type]  # noqa: SLF001
            except Exception:  # noqa: S110
                pass
        if r.redis_manager is not None:
            try:
                from crawlo.utils.redis.pool import GlobalRedisManager  # noqa: WPS433
                default_container.register_instance(GlobalRedisManager, r.redis_manager)
            except Exception:  # noqa: S110
                pass
        if r.initializer is not None:
            try:
                from crawlo.initialization.core import CoreInitializer  # noqa: WPS433
                default_container.register_instance(CoreInitializer, r.initializer)
            except Exception:  # noqa: S110
                pass

        # registries 侧：已提前创建的核心注册表
        regs = self.registries
        if regs.component_registry is not None:
            try:
                from crawlo.factories.registry import ComponentRegistry  # noqa: WPS433
                default_container.register_instance(ComponentRegistry, regs.component_registry)
            except Exception:  # noqa: S110
                pass
        if regs.initializer_registry is not None:
            try:
                from crawlo.initialization.registry import InitializerRegistry  # noqa: WPS433
                default_container.register_instance(InitializerRegistry, regs.initializer_registry)
            except Exception:  # noqa: S110
                pass
        if regs.job_registry is not None:
            try:
                from crawlo.scheduling.registry import JobRegistry  # noqa: WPS433
                default_container.register_instance(JobRegistry, regs.job_registry)
            except Exception:  # noqa: S110
                pass

    # ------------------------------
    # 延迟组件的补充绑定 / 清理
    # ------------------------------

    def _rebind_channel(self, name: str, instance: Any) -> None:
        """把 notification 里的 5 个 channel 实例 rebind 进 container（type → import 动态找）。"""
        if instance is None:
            return
        mapping = {
            "dingtalk": ("crawlo.bot.channels.dingtalk", "DingTalkChannel"),
            "feishu": ("crawlo.bot.channels.feishu", "FeishuChannel"),
            "wecom": ("crawlo.bot.channels.wecom", "WeComChannel"),
            "email": ("crawlo.bot.channels.email", "EmailChannel"),
            "sms": ("crawlo.bot.channels.sms", "SmsChannel"),
        }
        mod_name, cls_name = mapping[name]
        try:
            import importlib as _il
            from crawlo.container import default_container
            mod = _il.import_module(mod_name)
            cls = getattr(mod, cls_name)
            default_container.register_instance(cls, instance)
        except Exception:  # noqa: S110 Bot 子模块缺失时静默跳过（Phase 8 允许渐进迁移）
            pass

    def _unbind_from_container(self) -> None:
        """ApplicationContext cleanup 后：从 default_container 移除以 self.id 为 scope_id 的 request bucket。"""
        from crawlo.container import default_container
        default_container.clear(scope_id=self.id)

    # === Spider 注册表方法 ===

    def register_spider(self, name: str, spider_cls: Type['Spider']):
        """注册爬虫"""
        if name in self.registries.spider_registry:
            raise ValueError(f"Spider '{name}' already registered")
        self.registries.spider_registry[name] = spider_cls

    def get_spider(self, name: str) -> Optional[Type['Spider']]:
        """获取爬虫类"""
        return self.registries.spider_registry.get(name)

    def unregister_spider(self, name: str) -> bool:
        """取消注册爬虫"""
        if name in self.registries.spider_registry:
            del self.registries.spider_registry[name]
            return True
        return False

    # === 资源追踪 ===

    def add_resource(self, resource: Any):
        """添加资源追踪"""
        self.runtime.resources.add(resource)

    def remove_resource(self, resource: Any) -> bool:
        """移除资源追踪"""
        if resource in self.runtime.resources:
            self.runtime.resources.discard(resource)
            return True
        return False

    async def cleanup(self):
        """清理上下文资源"""
        logger = get_logger(__name__)
        for resource in list(self.runtime.resources):
            try:
                if hasattr(resource, 'close'):
                    close_method = resource.close
                    if asyncio.iscoroutinefunction(close_method):
                        await close_method()
                    else:
                        close_method()
                elif hasattr(resource, 'cleanup'):
                    cleanup_method = resource.cleanup
                    if asyncio.iscoroutinefunction(cleanup_method):
                        await cleanup_method()
                    else:
                        cleanup_method()
            except asyncio.CancelledError:
                logger.warning(f"Resource cleanup cancelled for {type(resource).__name__}")
                break
            except Exception as e:
                logger.error(f"Error cleaning up resource {type(resource).__name__}: {e}", exc_info=True)

        self.runtime.resources.clear()
        self.registries.spider_registry.clear()
        self.runtime.crawlers.clear()

        # Phase 8 Step 8.2：上下文销毁后，清掉容器里 scope_id=self.id 的 REQUEST 作用域实例
        try:
            self._unbind_from_container()
        except Exception as exc:  # pragma: no cover - 防御式，不应影响清理主流程
            get_logger(__name__).warning(
                f"ApplicationContext._unbind_from_container failed: {exc}", exc_info=True,
            )


# === 全局上下文访问（DCL 线程安全） ===

_global_context: Optional[ApplicationContext] = None
_context_lock = threading.Lock()

# ctx 就绪回调列表：供需要在 ctx 创建时感知的模块（如 _SpiderRegistryProxy）
# 注册同步逻辑。回调在 ctx 首次创建后被调用，接收 ctx 作为参数。
# 回调异常被吞掉并记日志，不影响 ctx 创建。
_context_ready_callbacks: List[Callable[[ApplicationContext], None]] = []


def register_context_ready_callback(callback: Callable[[ApplicationContext], None]) -> None:
    """注册 ctx 创建后的就绪回调。

    供需要感知 ctx 生命周期的模块使用（如 ``_SpiderRegistryProxy`` 把 import 期
    累积的 fallback 注册项同步到 ctx）。回调在 ctx 首次创建后被调用一次。

    若回调注册时 ctx 已存在，立即调用一次（避免错过注册窗口）。
    """
    ctx = _global_context
    if ctx is not None:
        # ctx 已存在，立即触发
        try:
            callback(ctx)
        except Exception as e:
            get_logger(__name__).warning(
                f"context_ready_callback {callback!r} failed: {e}", exc_info=True
            )
        return
    _context_ready_callbacks.append(callback)


def _notify_context_ready(ctx: ApplicationContext) -> None:
    """ctx 创建后调用所有注册的就绪回调（内部接口）。"""
    logger = get_logger(__name__)
    for cb in list(_context_ready_callbacks):
        try:
            cb(ctx)
        except Exception as e:
            logger.warning(f"context_ready_callback {cb!r} failed: {e}", exc_info=True)


def get_global_context(create_if_missing: bool = True) -> Optional[ApplicationContext]:
    """
    获取全局上下文（DCL 模式，线程安全，首次惰性创建）。

    DCL (Double-Checked Locking) 保证多线程并发首次调用时只创建一个实例：
    - 第一次检查（无锁）：99%+ 调用走此快速路径
    - 第二次检查（持锁）：确保只有一个线程创建实例

    Args:
        create_if_missing: 若为 False，则当上下文尚未创建时返回 None，
            不会触发惰性创建。供 import 期需要探测 ctx 是否就绪的代码
            使用（如 `_SpiderRegistryProxy`），避免 import crawlo 触发
            ApplicationContext 自动创建（Phase 4 验收点）。
    """
    global _global_context
    if _global_context is None and create_if_missing:
        with _context_lock:
            if _global_context is None:
                ctx = ApplicationContext()
                _global_context = ctx
                # 通知注册的回调：ctx 已就绪（如 _SpiderRegistryProxy 同步 fallback）
                _notify_context_ready(ctx)
    return _global_context


def reset_global_context() -> None:
    """
    重置全局上下文（线程安全，仅用于测试隔离）。

    生产环境不应调用。新 ctx 创建后会触发就绪回调，让 proxy 把 fallback
    同步到新 ctx（避免 reset 后丢失 import 期注册项）。
    """
    global _global_context
    with _context_lock:
        ctx = ApplicationContext()
        _global_context = ctx
    # 锁外触发回调，避免回调中再次获取锁导致死锁
    _notify_context_ready(ctx)


def set_global_context(ctx: ApplicationContext) -> None:
    """设置指定上下文（线程安全，高级用例）"""
    global _global_context
    with _context_lock:
        _global_context = ctx
    # 触发回调，让 proxy 同步 fallback 到新 ctx
    _notify_context_ready(ctx)


async def create_context() -> ApplicationContext:
    """创建新的隔离上下文"""
    ctx = ApplicationContext()
    set_global_context(ctx)
    return ctx
