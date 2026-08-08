"""
Crawlo 最小依赖注入容器（Phase 8 Step 8.1）

设计目标：
- 替代 35 处 ``get_global_context()`` 全局服务定位器，让依赖显式进构造器
- 纯 registry、零外部依赖（只依赖 typing），import 本模块 **不得** 触发 ApplicationContext 创建
- 单文件 ~300 行，不引入第三方 DI 库

用法：

    # 1. 注册资源（Phase 8 Step 8.2 会在 ApplicationContext.__init__ 末尾集中注册）
    from crawlo.container import default_container
    default_container.register_instance(NotifierRegistry, notifier_reg)

    # 2. 自动装配（@inject 按类型从 default_container 解析）
    from crawlo.container import inject
    class DingTalkChannel:
        @inject
        def __init__(self, notifier: NotifierRegistry):
            self.notifier = notifier

    # 3. 显式 resolve
    reg = default_container.resolve(NotifierRegistry)

作用域（Scope）：
    SINGLETON  每次 resolve 返回同一实例（类级全局）
    TRANSIENT  每次 resolve 新建
    REQUEST    每个 CrawlerProcess run 作用域（借 ApplicationContext 生命周期）

线程安全：Container 内部用 RLock，resolve / register / clear 可并发。
未注册类型抛出 :class:`ContainerResolutionError`，附带「已注册的类型列表 + 调用栈」便于诊断。
"""

from __future__ import annotations

import enum
import functools
import inspect
import threading
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Type, TypeVar, get_type_hints


__all__ = [
    "Scope",
    "Container",
    "ContainerResolutionError",
    "default_container",
    "inject",
]


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
