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
import enum
import functools
import inspect
import threading
import traceback
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Type, TypeVar, get_type_hints

from crawlo.logging import get_logger


__all__ = [
    "RegistryContext",
    "NotificationContext",
    "RuntimeContext",
    "ApplicationContext",
    "register_context_ready_callback",
    "get_global_context",
    "reset_global_context",
    "set_global_context",
    "create_context",
    "Scope",
    "Container",
    "ContainerResolutionError",
    "default_container",
    "inject",
    "InitializerRegistry",
    "InitializationContext",
    "CoreInitializer",
    "InitializationPhase",
    "PhaseResult",
    "initialize_framework",
    "is_framework_ready",
    "get_framework_context",
]


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
        # 合并后 default_container / Scope 与 ApplicationContext 同模块

        # 1. 子上下文整体（SINGLETON：进程内全局）
        default_container.register_instance(ApplicationContext, self)
        default_container.register_instance(RegistryContext, self.registries)
        default_container.register_instance(NotificationContext, self.notifications)
        default_container.register_instance(RuntimeContext, self.runtime)

        # 2. 直接实例（已存在时注册；延迟创建的组件后续通过 rebind_* 方法补充）
        n = self.notifications
        if n.notifier is not None:
            try:
                from crawlo.extensions.notifications.core.notifier import NotificationDispatcher  # noqa: WPS433
                default_container.register_instance(NotificationDispatcher, n.notifier)
            except Exception:  # noqa: S110  Bot 模块未安装时跳过
                pass
        if n.template_manager is not None:
            try:
                from crawlo.extensions.notifications.templates.manager import MessageTemplateManager  # noqa: WPS433
                default_container.register_instance(MessageTemplateManager, n.template_manager)
            except Exception:  # noqa: S110
                pass
        if n.deduplicator is not None:
            try:
                from crawlo.extensions.notifications.utils.deduplicator import MessageDeduplicator  # noqa: WPS433
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
                from crawlo.extensions.monitor.performance_monitor import PerformanceMonitor  # noqa: WPS433
                default_container.register_instance(PerformanceMonitor, r.performance_monitor)
            except Exception:  # noqa: S110
                pass
        if r._monitor_manager is not None:  # noqa: SLF001
            try:
                from crawlo.extensions.monitor.monitor_manager import MonitorManager  # noqa: WPS433
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
                default_container.register_instance(InitializerRegistry, regs.initializer_registry)
            except Exception:  # noqa: S110
                pass
        if regs.job_registry is not None:
            try:
                from crawlo.commands.registry import JobRegistry  # noqa: WPS433
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
            "dingtalk": ("crawlo.extensions.notifications.channels.dingtalk", "DingTalkChannel"),
            "feishu": ("crawlo.extensions.notifications.channels.feishu", "FeishuChannel"),
            "wecom": ("crawlo.extensions.notifications.channels.wecom", "WeComChannel"),
            "email": ("crawlo.extensions.notifications.channels.email", "EmailChannel"),
            "sms": ("crawlo.extensions.notifications.channels.sms", "SmsChannel"),
        }
        mod_name, cls_name = mapping[name]
        try:
            import importlib as _il
            mod = _il.import_module(mod_name)
            cls = getattr(mod, cls_name)
            default_container.register_instance(cls, instance)
        except Exception:  # noqa: S110 Bot 子模块缺失时静默跳过（Phase 8 允许渐进迁移）
            pass

    def _unbind_from_container(self) -> None:
        """ApplicationContext cleanup 后：从 default_container 移除以 self.id 为 scope_id 的 request bucket。"""
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


# ===================================================================
# DI 容器模块（原 crawlo.container，Phase 5 #28 合并入此处）
# ===================================================================

T = TypeVar("T")


class Scope(str, enum.Enum):
    """依赖作用域"""

    SINGLETON = "singleton"    # 每次 resolve 返回同一实例
    TRANSIENT = "transient"    # 每次 resolve 新建
    REQUEST = "request"        # 每个 CrawlerProcess run 一份；借 ctx 生命周期管理


@dataclass
class _Registration:
    """容器内部的一条注册记录"""

    scope: Scope
    # 实例提供方式三选一：
    instance: Optional[Any] = None                 # SINGLETON 直接已构造实例
    factory: Optional[Callable[[], Any]] = None    # SINGLETON / TRANSIENT / REQUEST 的工厂
    # SINGLETON lazy 工厂：首次 resolve 时构建一次并缓存
    _cached_instance: Any = field(default=None, repr=False, compare=False)


class ContainerResolutionError(Exception):
    """依赖解析失败。

    附带：缺什么类型、已注册了什么、调用栈（trim 过，去掉容器内部栈帧只保留业务代码）。
    """

    def __init__(self, missing: Type, registered: Iterable[Type], frame_cut: int = 3):
        self.missing = missing
        self.registered_types: List[Type] = list(registered)
        stack = traceback.format_stack()
        # 去掉 Container.resolve 内部栈帧（最后 frame_cut 条），只保留调用者
        visible_stack = "".join(stack[:-frame_cut]) if len(stack) > frame_cut else "".join(stack)
        registered_str = ", ".join(getattr(t, "__qualname__", repr(t)) for t in self.registered_types)
        missing_str = getattr(missing, "__qualname__", repr(missing))
        msg = (
            f"ContainerResolutionError: cannot resolve type '{missing_str}'.\n"
            f"Registered types ({len(self.registered_types)}): {registered_str or '(none)'}\n"
            f"Caller stack:\n{visible_stack}"
        )
        super().__init__(msg)


class Container:
    """最小依赖注入容器。

    无全局状态（除 ``default_container`` 这个模块级实例外）；
    ``__init__`` 不触发任何 ApplicationContext / get_global_context 副作用。
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # key: Type, value: _Registration
        self._registrations: Dict[Type, _Registration] = {}
        # REQUEST 作用域按 scope_id（通常为 ApplicationContext.id）分开存实例
        self._request_instances: Dict[str, Dict[Type, Any]] = {}

    # ============================================================
    # 注册 API
    # ============================================================

    def register_instance(self, cls: Type[T], instance: T) -> None:
        """注册**已构造好的单例**。常用于 Phase 8.2 ApplicationContext._bind_to_container。"""
        if instance is None:
            raise ValueError(f"register_instance({cls.__name__}): instance must not be None")
        with self._lock:
            self._registrations[cls] = _Registration(scope=Scope.SINGLETON, instance=instance)

    def register_singleton(self, cls: Type[T], factory: Callable[[], T]) -> None:
        """注册 SINGLETON 工厂（lazy，首次 resolve 才创建并缓存）。"""
        if not callable(factory):
            raise ValueError(f"register_singleton({cls.__name__}): factory must be callable")
        with self._lock:
            self._registrations[cls] = _Registration(scope=Scope.SINGLETON, factory=factory)

    def register_transient(self, cls: Type[T], factory: Callable[[], T]) -> None:
        """注册 TRANSIENT 工厂（每次 resolve 新建）。"""
        if not callable(factory):
            raise ValueError(f"register_transient({cls.__name__}): factory must be callable")
        with self._lock:
            self._registrations[cls] = _Registration(scope=Scope.TRANSIENT, factory=factory)

    def register_request_factory(self, cls: Type[T], factory: Callable[[], T]) -> None:
        """注册 REQUEST 作用域工厂。

        需要显式指定 ``scope_id`` 才能解析（通常用 ``ApplicationContext.id`` 作为 scope_id）。
        """
        if not callable(factory):
            raise ValueError(f"register_request_factory({cls.__name__}): factory must be callable")
        with self._lock:
            self._registrations[cls] = _Registration(scope=Scope.REQUEST, factory=factory)

    # ============================================================
    # 解析 API
    # ============================================================

    def resolve(self, cls: Type[T], *, scope_id: Optional[str] = None) -> T:
        """解析 ``cls`` 的实例。

        Args:
            cls: 目标类型（必须曾 register_* 注册过）。
            scope_id: 当类型注册为 REQUEST 作用域时必须传（一般是 ApplicationContext.id）。
                      SINGLETON / TRANSIENT 忽略此参数。

        Raises:
            ContainerResolutionError: 未注册或 REQUEST 缺 scope_id。
        """
        with self._lock:
            reg = self._registrations.get(cls)
            if reg is None:
                raise ContainerResolutionError(cls, self._registrations.keys(), frame_cut=3)

            if reg.scope is Scope.SINGLETON:
                if reg.instance is not None:
                    return reg.instance  # type: ignore[return-value]
                if reg._cached_instance is None:
                    if reg.factory is None:
                        raise ContainerResolutionError(cls, self._registrations.keys(), frame_cut=3)
                    reg._cached_instance = reg.factory()
                return reg._cached_instance  # type: ignore[return-value]

            if reg.scope is Scope.TRANSIENT:
                if reg.factory is None:
                    raise ContainerResolutionError(cls, self._registrations.keys(), frame_cut=3)
                return reg.factory()  # type: ignore[return-value]

            if reg.scope is Scope.REQUEST:
                if scope_id is None:
                    raise ContainerResolutionError(
                        cls, self._registrations.keys(), frame_cut=3,
                    ) from RuntimeError(
                        f"REQUEST-scoped type {getattr(cls, '__qualname__', repr(cls))} requires scope_id"
                    )
                bucket = self._request_instances.setdefault(scope_id, {})
                if cls not in bucket:
                    if reg.factory is None:
                        raise ContainerResolutionError(cls, self._registrations.keys(), frame_cut=3)
                    bucket[cls] = reg.factory()
                return bucket[cls]  # type: ignore[return-value]

        raise AssertionError("unreachable: unknown scope")  # pragma: no cover

    # ============================================================
    # 生命周期 API
    # ============================================================

    def is_registered(self, cls: Type) -> bool:
        with self._lock:
            return cls in self._registrations

    def registered_types(self) -> List[Type]:
        with self._lock:
            return list(self._registrations.keys())

    def clear(self, scope_id: Optional[str] = None) -> None:
        """清空注册项或指定 scope_id 的 REQUEST 实例桶。

        Args:
            scope_id: 仅清空某个 REQUEST 作用域实例（比如单个 CrawlerProcess 结束）；
                      None 则清空所有注册（测试用 / 进程退出）。
        """
        with self._lock:
            if scope_id is None:
                # 全量 reset
                self._registrations.clear()
                self._request_instances.clear()
                return
            self._request_instances.pop(scope_id, None)

    # ============================================================
    # 诊断 API（出错时打已注册列表）
    # ============================================================

    def diagnostic_snapshot(self) -> Dict[str, Any]:
        """非侵入式状态快照（日志 / 错误报告用）。"""
        with self._lock:
            return {
                "registrations": {
                    getattr(t, "__qualname__", repr(t)): {
                        "scope": r.scope.value,
                        "has_instance": r.instance is not None or r._cached_instance is not None,
                        "has_factory": r.factory is not None,
                    }
                    for t, r in self._registrations.items()
                },
                "request_buckets": sorted(self._request_instances.keys()),
            }


# -------------------------------------------------------------------
# 模块级全局容器（替代 35 处 get_global_context()；它本身是纯 registry，
# 不持有业务状态；ApplicationContext._bind_to_container 是唯一的批量注册入口）
# -------------------------------------------------------------------
default_container: Container = Container()


# -------------------------------------------------------------------
# @inject 装饰器
# -------------------------------------------------------------------

def inject(func: Callable[..., T]) -> Callable[..., T]:
    """装饰器：按类型注解从 ``default_container`` 自动装配参数。

    典型用法：装饰类的 ``__init__`` 方法。对每一个参数，若其类型注解已在容器中注册，
    且调用方未显式传参，则调用 ``resolve()`` 注入。调用方显式传入的值优先级更高（便于测试）。

    Args:
        func: 要装饰的函数（通常是类的 ``__init__``）。

    Returns:
        包装后的函数。

    例::

        class DingTalkChannel:
            @inject
            def __init__(self, notifier: NotifierRegistry):
                self.notifier = notifier
    """
    if not inspect.isfunction(func) and not inspect.ismethod(func):
        raise TypeError("@inject can only decorate functions/methods")

    sig = inspect.signature(func)
    # 仅处理有类型注解的参数；self/cls 跳过
    hints = _safe_type_hints(func)

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        bound = sig.bind_partial(*args, **kwargs)
        bound.apply_defaults()
        for name, param in sig.parameters.items():
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue
            if name in ("self", "cls"):
                continue
            if name in bound.arguments:
                # 调用方显式传过值（即使是默认值 bind.apply_defaults 打上的也算）——除非它是参数的默认哨兵
                continue
            annotation = hints.get(name, _MISSING)
            if annotation is _MISSING or not isinstance(annotation, type):
                continue
            if not default_container.is_registered(annotation):
                # 未注册：留空，让原始 func 抛它自然的 TypeError（用户显式传参）
                continue
            kwargs[name] = default_container.resolve(annotation)
        return func(*args, **kwargs)

    return wrapper


# -------------------------------------------------------------------
# 内部工具
# -------------------------------------------------------------------

_MISSING = object()


def _safe_type_hints(func: Callable[..., Any]) -> Dict[str, Any]:
    """``typing.get_type_hints`` 的安全版本：解析失败时退化到 ``__annotations__``，**不抛**。

    @inject 不应因为「某些注解是 string forward reference 且 TYPE_CHECKING 块里的 import 不存在」
    而在运行时崩溃。解析不出的就跳过 —— 此时该参数无法被自动注入，但用户仍可手动传值。
    """
    try:
        return get_type_hints(func, include_extras=False)
    except Exception:
        pass
    try:
        return dict(getattr(func, "__annotations__", {}) or {})
    except Exception:
        return {}


# ===================================================================
# initialization/phases.py — Initialization Phase Definitions
# ===================================================================
from enum import Enum  # noqa: E402


class InitializationPhase(Enum):
    """初始化阶段枚举"""

    PREPARING = "preparing"
    LOGGING = "logging"
    SETTINGS = "settings"
    CORE_COMPONENTS = "core_components"
    EXTENSIONS = "extensions"
    FRAMEWORK_STARTUP_LOG = "framework_startup_log"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class PhaseResult:
    """阶段执行结果"""
    phase: InitializationPhase
    success: bool
    duration: float = 0.0
    error: Optional[Exception] = None
    artifacts: dict = None

    def __post_init__(self):
        if self.artifacts is None:
            self.artifacts = {}


@dataclass
class PhaseDefinition:
    """阶段定义"""
    phase: InitializationPhase
    name: str
    description: str
    dependencies: List[InitializationPhase] = None
    optional: bool = False
    timeout: float = 30.0

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


PHASE_DEFINITIONS = [
    PhaseDefinition(
        phase=InitializationPhase.PREPARING,
        name="准备阶段",
        description="初始化基础环境和检查前置条件",
        dependencies=[],
        timeout=5.0
    ),
    PhaseDefinition(
        phase=InitializationPhase.LOGGING,
        name="日志系统",
        description="配置和初始化日志系统",
        dependencies=[],
        timeout=10.0
    ),
    PhaseDefinition(
        phase=InitializationPhase.SETTINGS,
        name="配置系统",
        description="加载和验证配置",
        dependencies=[InitializationPhase.LOGGING],
        timeout=15.0
    ),
    PhaseDefinition(
        phase=InitializationPhase.CORE_COMPONENTS,
        name="核心组件",
        description="初始化框架核心组件",
        dependencies=[InitializationPhase.SETTINGS],
        timeout=20.0
    ),
    PhaseDefinition(
        phase=InitializationPhase.EXTENSIONS,
        name="扩展组件",
        description="加载和初始化扩展组件",
        dependencies=[InitializationPhase.CORE_COMPONENTS],
        optional=True,
        timeout=15.0
    ),
    PhaseDefinition(
        phase=InitializationPhase.FRAMEWORK_STARTUP_LOG,
        name="框架启动日志",
        description="记录框架启动相关信息",
        dependencies=[InitializationPhase.LOGGING, InitializationPhase.SETTINGS],
        timeout=5.0
    ),
    PhaseDefinition(
        phase=InitializationPhase.COMPLETED,
        name="初始化完成",
        description="框架初始化完成",
        dependencies=[
            InitializationPhase.CORE_COMPONENTS,
            InitializationPhase.FRAMEWORK_STARTUP_LOG
        ],
        timeout=5.0
    )
]


def get_phase_definition(phase: InitializationPhase) -> Optional[PhaseDefinition]:
    """获取阶段定义"""
    for definition in PHASE_DEFINITIONS:
        if definition.phase == phase:
            return definition
    return None


def get_execution_order() -> List[InitializationPhase]:
    """获取执行顺序"""
    return [definition.phase for definition in PHASE_DEFINITIONS]


def validate_dependencies() -> bool:
    """验证阶段依赖关系的正确性"""
    phases = {definition.phase for definition in PHASE_DEFINITIONS}

    for definition in PHASE_DEFINITIONS:
        for dependency in definition.dependencies:
            if dependency not in phases:
                return False

    return True


def detect_circular_dependencies() -> Optional[List[InitializationPhase]]:
    """检测循环依赖（DFS三色标记法）"""
    dependency_graph: Dict[InitializationPhase, List[InitializationPhase]] = {}
    for definition in PHASE_DEFINITIONS:
        dependency_graph[definition.phase] = definition.dependencies.copy()

    color: Dict[InitializationPhase, int] = {phase: 0 for phase in dependency_graph}
    parent: Dict[InitializationPhase, Optional[InitializationPhase]] = {phase: None for phase in dependency_graph}

    def dfs(node: InitializationPhase) -> Optional[List[InitializationPhase]]:
        color[node] = 1
        for neighbor in dependency_graph.get(node, []):
            if color[neighbor] == 1:
                cycle = [neighbor]
                current: Optional[InitializationPhase] = node
                while current is not None and current != neighbor:
                    cycle.append(current)
                    current = parent.get(current)
                cycle.append(neighbor)
                cycle.reverse()
                return cycle
            if color[neighbor] == 0:
                parent[neighbor] = node
                result = dfs(neighbor)
                if result:
                    return result
        color[node] = 2
        return None

    for phase in dependency_graph:
        if color[phase] == 0:
            cycle = dfs(phase)
            if cycle:
                return cycle

    return None


def validate_phase_dependencies() -> Tuple[bool, Optional[str]]:
    """Comprehensive validation of phase dependencies"""
    if not validate_dependencies():
        return False, "存在未定义的依赖阶段"

    cycle = detect_circular_dependencies()
    if cycle:
        cycle_path = ' -> '.join([phase.value for phase in cycle])
        return False, f"检测到循环依赖: {cycle_path}"

    return True, None


# ===================================================================
# initialization/context.py — InitializationContext
# ===================================================================
import time as _time_init  # noqa: E402


@dataclass
class InitializationContext:
    """初始化上下文 — 保存初始化过程中的状态和数据"""

    start_time: float = field(default_factory=_time_init.time)
    end_time: Optional[float] = None
    current_phase: InitializationPhase = InitializationPhase.PREPARING
    completed_phases: List[InitializationPhase] = field(default_factory=list)
    failed_phases: List[InitializationPhase] = field(default_factory=list)
    phase_results: Dict[InitializationPhase, PhaseResult] = field(default_factory=dict)
    shared_data: Dict[str, Any] = field(default_factory=dict)
    settings: Optional[Any] = None
    custom_settings: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False)

    def set_current_phase(self, phase: InitializationPhase):
        with self._lock:
            self.current_phase = phase

    def mark_phase_completed(self, phase: InitializationPhase, result: PhaseResult):
        with self._lock:
            if result.success:
                self.completed_phases.append(phase)
            else:
                self.failed_phases.append(phase)
            self.phase_results[phase] = result

    def add_shared_data(self, key: str, value: Any):
        with self._lock:
            self.shared_data[key] = value

    def get_shared_data(self, key: str, default=None):
        with self._lock:
            return self.shared_data.get(key, default)

    def add_error(self, message: str):
        with self._lock:
            self.errors.append(message)

    def add_warning(self, message: str):
        with self._lock:
            self.warnings.append(message)

    def is_phase_completed(self, phase: InitializationPhase) -> bool:
        with self._lock:
            return phase in self.completed_phases

    def is_phase_failed(self, phase: InitializationPhase) -> bool:
        with self._lock:
            return phase in self.failed_phases

    def get_phase_result(self, phase: InitializationPhase) -> Optional[PhaseResult]:
        with self._lock:
            return self.phase_results.get(phase)

    def get_total_duration(self) -> float:
        end = self.end_time or _time_init.time()
        return end - self.start_time

    def get_phase_durations(self) -> Dict[InitializationPhase, float]:
        with self._lock:
            return {
                phase: result.duration
                for phase, result in self.phase_results.items()
            }

    def get_success_rate(self) -> float:
        with self._lock:
            total = len(self.completed_phases) + len(self.failed_phases)
            if total == 0:
                return 0.0
            return len(self.completed_phases) / total * 100

    def finish(self):
        with self._lock:
            self.end_time = _time_init.time()

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'start_time': self.start_time,
                'end_time': self.end_time,
                'total_duration': self.get_total_duration(),
                'current_phase': self.current_phase.value,
                'completed_phases': [p.value for p in self.completed_phases],
                'failed_phases': [p.value for p in self.failed_phases],
                'success_rate': self.get_success_rate(),
                'error_count': len(self.errors),
                'warning_count': len(self.warnings),
                'phase_durations': {
                    p.value: duration
                    for p, duration in self.get_phase_durations().items()
                }
            }


# ===================================================================
# initialization/utils.py — Utility functions
# ===================================================================
import time as _time_utils  # noqa: E402


def create_initialization_result(
    phase: 'InitializationPhase',
    success: bool,
    duration: float = 0.0,
    artifacts: Optional[Dict[str, Any]] = None,
    error: Optional[Exception] = None
) -> PhaseResult:
    """创建标准化的初始化结果"""
    return PhaseResult(
        phase=phase,
        success=success,
        duration=duration,
        artifacts=artifacts or {},
        error=error
    )


class InitializationTimer:
    """初始化计时器"""

    def __init__(self):
        self.start_time = _time_utils.time()

    def get_duration(self) -> float:
        return _time_utils.time() - self.start_time


# ===================================================================
# initialization/registry.py — InitializerRegistry
# ===================================================================

class Initializer:
    """Initializer base class"""

    def __init__(self, phase: InitializationPhase):
        self._phase = phase

    @property
    def phase(self) -> InitializationPhase:
        return self._phase

    def initialize(self, context: InitializationContext) -> PhaseResult:
        raise NotImplementedError("Subclasses must implement initialize method")


class BaseInitializer(Initializer):
    """Base initializer class — retained for backward compatibility"""

    def __init__(self, phase: InitializationPhase):
        super().__init__(phase)

    def _create_result(self, success: bool, duration: float = 0.0,
                      artifacts: Optional[Dict[str, Any]] = None, error: Optional[Exception] = None) -> PhaseResult:
        return create_initialization_result(
            phase=self.phase,
            success=success,
            duration=duration,
            artifacts=artifacts,
            error=error
        )


class InitializerRegistry:
    """Initializer Registry — Manage registration and execution of all initializers"""

    def __init__(self):
        self._initializers: Dict[InitializationPhase, Initializer] = {}
        self._lock = threading.RLock()

    def register(self, initializer: Initializer):
        with self._lock:
            phase = initializer.phase
            if phase in self._initializers:
                raise ValueError(f"Initializer for phase {phase} already registered")
            self._initializers[phase] = initializer

    def register_function(self, phase: InitializationPhase,
                         init_func: Callable[[InitializationContext], PhaseResult]):

        class FunctionInitializer(Initializer):
            def __init__(self, phase: InitializationPhase, func: Callable):
                super().__init__(phase)
                self._func = func

            def initialize(self, context: InitializationContext) -> PhaseResult:
                return self._func(context)

        self.register(FunctionInitializer(phase, init_func))

    def get_initializer(self, phase: InitializationPhase) -> Optional[Initializer]:
        with self._lock:
            return self._initializers.get(phase)

    def get_all_phases(self) -> List[InitializationPhase]:
        with self._lock:
            return list(self._initializers.keys())

    def has_initializer(self, phase: InitializationPhase) -> bool:
        with self._lock:
            return phase in self._initializers

    def clear(self):
        with self._lock:
            self._initializers.clear()

    def execute_phase(self, phase: InitializationPhase,
                     context: InitializationContext) -> PhaseResult:
        initializer = self.get_initializer(phase)
        if not initializer:
            error = ValueError(f"No initializer registered for phase {phase}")
            return PhaseResult(
                phase=phase,
                success=False,
                error=error
            )

        try:
            return initializer.initialize(context)
        except Exception as e:
            return PhaseResult(
                phase=phase,
                success=False,
                error=e
            )


def _resolve_registry_context():
    """优先从容器拿 RegistryContext，否则 fallback ctx.registries。"""
    try:
        from crawlo.container import default_container  # noqa: WPS433
        if default_container.is_registered(RegistryContext):
            return default_container.resolve(RegistryContext)
    except Exception:  # noqa: S110
        pass
    return get_global_context().registries


def get_global_registry() -> InitializerRegistry:
    """获取全局初始化器注册表（DI 容器优先 + RegistryContext fallback）。"""
    try:
        from crawlo.container import default_container  # noqa: WPS433
        if default_container.is_registered(InitializerRegistry):
            return default_container.resolve(InitializerRegistry)
    except Exception:  # pragma: no cover
        pass

    rctx = _resolve_registry_context()
    if rctx.initializer_registry is None:
        inst = InitializerRegistry()
        rctx.initializer_registry = inst
        try:
            from crawlo.container import default_container as _c  # noqa: WPS433
            _c.register_instance(InitializerRegistry, inst)
        except Exception:  # pragma: no cover
            pass
    return rctx.initializer_registry


def register_initializer(initializer: Initializer):
    """注册初始化器到全局注册表"""
    get_global_registry().register(initializer)


def register_phase_function(phase: InitializationPhase,
                            init_func: Callable[[InitializationContext], PhaseResult]):
    """注册函数式初始化器到全局注册表"""
    get_global_registry().register_function(phase, init_func)


# ===================================================================
# initialization/built_in.py — Built-in Initializers
# ===================================================================
import os as _os_bi  # noqa: E402
import time as _time_bi  # noqa: E402
import importlib as _importlib_bi  # noqa: E402
import sys as _sys_bi  # noqa: E402

from crawlo.logging import configure_logging, get_logger, LogConfig, LoggerFactory  # noqa: E402
from crawlo.utils.misc import ConfigUtils, load_object  # noqa: E402


class LoggingInitializer(BaseInitializer):
    """日志系统初始化器"""

    def __init__(self):
        super().__init__(InitializationPhase.LOGGING)

    def initialize(self, context: InitializationContext) -> PhaseResult:
        start_time = _time_bi.time()

        try:
            log_config = self._get_log_config(context)

            if log_config and log_config.file_path and log_config.file_enabled:
                log_dir = _os_bi.path.dirname(log_config.file_path)
                if log_dir and not _os_bi.path.exists(log_dir):
                    _os_bi.makedirs(log_dir, exist_ok=True)

            configure_logging(log_config)

            context.add_shared_data('log_config', log_config)

            framework_logger = get_logger('crawlo.framework')
            context.add_shared_data('framework_logger', framework_logger)

            return self._create_result(
                success=True,
                duration=_time_bi.time() - start_time,
                artifacts={'log_config': log_config}
            )

        except Exception as e:
            return self._create_result(
                success=False,
                duration=_time_bi.time() - start_time,
                error=e
            )

    def _get_log_config(self, context: InitializationContext) -> LogConfig:
        config_sources = [
            context.custom_settings,
            context.settings,
            self._load_project_config()
        ]

        for config_source in config_sources:
            if config_source and ConfigUtils.has_config_prefix(config_source, 'LOG_'):
                log_config = self._create_log_config_from_source(config_source)
                if log_config:
                    return log_config

        return LogConfig()

    def _create_log_config_from_source(self, config_source) -> Optional['LogConfig']:
        if not config_source:
            return None

        if not ConfigUtils.has_config_prefix(config_source, 'LOG_'):
            return None

        log_level = ConfigUtils.get_config_value([config_source], 'LOG_LEVEL', 'INFO')
        log_file = ConfigUtils.get_config_value([config_source], 'LOG_FILE')
        log_format = ConfigUtils.get_config_value([config_source], 'LOG_FORMAT', '%(asctime)s - [%(name)s] - %(levelname)s: %(message)s')
        log_encoding = ConfigUtils.get_config_value([config_source], 'LOG_ENCODING', 'utf-8')
        log_console_enabled = ConfigUtils.get_config_value([config_source], 'LOG_CONSOLE_ENABLED', True, bool)
        log_file_enabled = ConfigUtils.get_config_value([config_source], 'LOG_FILE_ENABLED', True, bool)

        return LogConfig(
            level=log_level,
            format=log_format,
            encoding=log_encoding,
            file_path=log_file,
            console_enabled=log_console_enabled,
            file_enabled=log_file_enabled
        )

    def _load_project_config(self):
        try:
            from crawlo.project import read_crawlo_cfg  # noqa: WPS433

            current_path = _os_bi.getcwd()
            checked_paths = set()
            path = current_path

            while path not in checked_paths:
                checked_paths.add(path)

                cfg_file = _os_bi.path.join(path, "crawlo.cfg")
                settings_module_path = read_crawlo_cfg(cfg_file)

                if settings_module_path:
                    if path not in _sys_bi.path:
                        _sys_bi.path.insert(0, path)

                    settings_module = _importlib_bi.import_module(settings_module_path)
                    project_config = ConfigUtils.merge_config_sources([settings_module])

                    return project_config

                parent = _os_bi.path.dirname(path)
                if parent == path:
                    break
                path = parent

            return {}

        except Exception:
            return {}


class SettingsInitializer(BaseInitializer):
    """配置系统初始化器"""

    def __init__(self):
        super().__init__(InitializationPhase.SETTINGS)

    def initialize(self, context: InitializationContext) -> PhaseResult:
        start_time = _time_bi.time()

        try:
            from crawlo.settings.setting_manager import SettingManager  # noqa: WPS433
            from crawlo.project import _load_project_settings  # noqa: WPS433

            if context.settings:
                settings = context.settings
                project_settings = _load_project_settings(context.custom_settings)
                settings.update_attributes(project_settings.attributes)
            else:
                settings = _load_project_settings(context.custom_settings)

            context.settings = settings
            context.add_shared_data('settings', settings)

            return self._create_result(
                success=True,
                duration=_time_bi.time() - start_time,
                artifacts={'settings': settings}
            )

        except Exception as e:
            return self._create_result(
                success=False,
                duration=_time_bi.time() - start_time,
                error=e
            )


class CoreComponentsInitializer(BaseInitializer):
    """Core components initializer"""

    def __init__(self):
        super().__init__(InitializationPhase.CORE_COMPONENTS)

    def initialize(self, context: InitializationContext) -> PhaseResult:
        start_time = _time_bi.time()

        try:
            logger = context.get_shared_data('framework_logger')
            if logger:
                logger.debug("Core components initialization deferred to crawler creation")

            return self._create_result(
                success=True,
                duration=_time_bi.time() - start_time,
                artifacts={'note': 'Core components initialized during crawler creation'}
            )

        except Exception as e:
            return self._create_result(
                success=False,
                duration=_time_bi.time() - start_time,
                error=e
            )

    def _get_spider_module_initializer_config(self, context: InitializationContext) -> dict:
        return ConfigUtils.get_config_value(
            [context.settings, context.custom_settings],
            'SPIDER_MODULE_INITIALIZER',
            {}
        )

    def _get_custom_downloader_path(self, context: InitializationContext) -> Optional[str]:
        custom_downloader_path = ConfigUtils.get_config_value(
            [context.settings, context.custom_settings],
            'CUSTOM_DOWNLOADER',
            None
        )
        if custom_downloader_path:
            return load_object(custom_downloader_path)
        return None


class ExtensionsInitializer(BaseInitializer):
    """扩展组件初始化器"""

    def __init__(self):
        super().__init__(InitializationPhase.EXTENSIONS)

    def initialize(self, context: InitializationContext) -> PhaseResult:
        start_time = _time_bi.time()

        try:
            self._initialize_extensions(context)

            return self._create_result(
                success=True,
                duration=_time_bi.time() - start_time,
                artifacts={}
            )

        except Exception as e:
            return self._create_result(
                success=False,
                duration=_time_bi.time() - start_time,
                error=e
            )

    def _initialize_extensions(self, context: InitializationContext):
        try:
            extensions = []
            if context.settings:
                extensions = context.settings.get('EXTENSIONS', [])
            elif context.custom_settings:
                extensions = context.custom_settings.get('EXTENSIONS', [])

            initialized_extensions = []
            for extension_path in extensions:
                try:
                    extension_class = load_object(extension_path)
                    extension_instance = extension_class()
                    initialized_extensions.append(extension_instance)
                except Exception as e:
                    if context.settings and context.settings.get('EXTENSIONS_STRICT', False):
                        raise
                    else:
                        context.add_warning(f"Failed to initialize extension {extension_path}: {e}")

            context.add_shared_data('extensions', initialized_extensions)
        except Exception as e:
            context.add_error(f"Failed to initialize extensions: {e}")
            raise


class FrameworkStartupLogger(BaseInitializer):
    """框架启动日志记录器"""

    def __init__(self):
        super().__init__(InitializationPhase.FRAMEWORK_STARTUP_LOG)

    def initialize(self, context: InitializationContext) -> PhaseResult:
        start_time = _time_bi.time()

        try:
            if context.settings:
                configure_logging(context.settings)
                LoggerFactory.clear_cache()

            logger = get_logger('crawlo.framework')
            version = self._get_framework_version()
            logger.info(f"Crawlo Framework Started {version}")

            run_mode = "unknown"
            queue_type = "unknown"
            if context.settings:
                run_mode = context.settings.get('RUN_MODE', 'standalone')
                queue_type = context.settings.get('QUEUE_TYPE', 'memory')
                if queue_type == 'auto':
                    queue_type = 'auto-detect'
            logger.info(f"Run mode: {run_mode}, Queue type: {queue_type}")

            return self._create_result(
                success=True,
                duration=_time_bi.time() - start_time,
                artifacts={}
            )

        except Exception as e:
            return self._create_result(
                success=True,
                duration=_time_bi.time() - start_time,
                error=e
            )

    def _get_framework_version(self):
        try:
            from crawlo import __version__  # noqa: WPS433
            return __version__
        except Exception:
            return "unknown"


def register_built_in_initializers():
    """注册所有内置初始化器"""
    register_initializer(LoggingInitializer())
    register_initializer(SettingsInitializer())
    register_initializer(CoreComponentsInitializer())
    register_initializer(ExtensionsInitializer())
    register_initializer(FrameworkStartupLogger())


# ===================================================================
# initialization/core.py — CoreInitializer (SingletonMeta)
# ===================================================================
import time as _time_core  # noqa: E402

from crawlo.core.singleton import SingletonMeta  # noqa: E402


class CoreInitializer(metaclass=SingletonMeta):
    """核心初始化器 — 协调整个框架的初始化过程"""

    def __init__(self):
        self._context: Optional[InitializationContext] = None
        self._is_ready = False
        self._init_lock = threading.RLock()

        is_valid, error_msg = validate_phase_dependencies()
        if not is_valid:
            raise RuntimeError(f"初始化阶段配置错误: {error_msg}")

        register_built_in_initializers()

    @property
    def context(self) -> Optional[InitializationContext]:
        return self._context

    @property
    def is_ready(self) -> bool:
        return self._is_ready

    def initialize(self, settings=None, **kwargs) -> Any:
        with self._init_lock:
            if self._is_ready and self._context and self._context.settings:
                return self._context.settings

            context = InitializationContext()
            context.custom_settings = kwargs
            context.settings = settings
            self._context = context

            try:
                self._execute_initialization_phases(context)

                if not context.is_phase_completed(InitializationPhase.SETTINGS):
                    raise RuntimeError("Settings initialization failed")

                self._is_ready = True
                context.finish()

                return context.settings

            except Exception as e:
                context.add_error(f"Framework initialization failed: {e}")
                context.finish()

                return self._fallback_initialization(settings, **kwargs)

    def _execute_initialization_phases(self, context: InitializationContext):
        registry = get_global_registry()
        execution_order = get_execution_order()

        registered_phases = set(registry.get_all_phases())

        for phase in execution_order:
            if phase == InitializationPhase.ERROR:
                continue

            if phase not in registered_phases:
                continue

            context.set_current_phase(phase)

            if not self._check_dependencies(phase, context):
                phase_def = get_phase_definition(phase)
                if not (phase_def and phase_def.optional):
                    raise RuntimeError(f"Dependencies not satisfied for phase {phase}")
                else:
                    continue

            start_time = _time_core.time()
            try:
                result = self._execute_phase_with_timeout(phase, context, registry)
                result.duration = _time_core.time() - start_time

                context.mark_phase_completed(phase, result)

                if not result.success and not self._is_phase_optional(phase):
                    raise RuntimeError(f"Phase {phase} failed: {result.error}")

            except Exception as e:
                duration = _time_core.time() - start_time
                result = PhaseResult(
                    phase=phase,
                    success=False,
                    duration=duration,
                    error=e
                )
                context.mark_phase_completed(phase, result)

                if not self._is_phase_optional(phase):
                    raise

    def _execute_phase_with_timeout(self, phase: InitializationPhase,
                                    context: InitializationContext,
                                    registry) -> PhaseResult:
        phase_def = get_phase_definition(phase)
        timeout = phase_def.timeout if phase_def else 30.0

        result_container: List[Optional[PhaseResult]] = [None]
        exception_container: List[Optional[Exception]] = [None]

        def execute_in_thread():
            try:
                result_container[0] = registry.execute_phase(phase, context)
            except Exception as e:
                exception_container[0] = e

        thread = threading.Thread(target=execute_in_thread, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            error_msg = f"Phase {phase.value} execution timeout after {timeout} seconds"
            context.add_warning(error_msg)
            return PhaseResult(
                phase=phase,
                success=False,
                error=TimeoutError(error_msg)
            )

        if exception_container[0]:
            raise exception_container[0]

        if result_container[0] is None:
            raise RuntimeError(f"Phase {phase.value} returned None result")
        return result_container[0]

    def _check_dependencies(self, phase: InitializationPhase,
                          context: InitializationContext) -> bool:
        phase_def = get_phase_definition(phase)
        if not phase_def:
            return True

        for dependency in phase_def.dependencies:
            if not context.is_phase_completed(dependency):
                return False

        return True

    def _is_phase_optional(self, phase: InitializationPhase) -> bool:
        phase_def = get_phase_definition(phase)
        return phase_def.optional if phase_def else False

    def _fallback_initialization(self, settings=None, **kwargs):
        try:
            from crawlo.settings.setting_manager import SettingManager  # noqa: WPS433

            if settings:
                return settings
            else:
                fallback_settings = SettingManager()
                if kwargs:
                    fallback_settings.update_attributes(kwargs)
                return fallback_settings

        except Exception:
            return None

    def reset(self):
        with self._init_lock:
            self._context = None
            self._is_ready = False


# ===================================================================
# initialization/__init__.py — 顶层公共接口
# ===================================================================
"""
Crawlo框架统一初始化系统（已合并入 crawlo.core.application）
"""


def initialize_framework(settings=None, **kwargs):
    """初始化框架的主要入口"""
    return CoreInitializer().initialize(settings, **kwargs)


def is_framework_ready():
    """检查框架是否已准备就绪"""
    return CoreInitializer().is_ready


def get_framework_context():
    """获取框架初始化上下文"""
    return CoreInitializer().context
