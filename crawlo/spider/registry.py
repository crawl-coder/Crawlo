#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Spider 注册表模块（P2-6 拆分）
=============================
从 spider.py 拆分：全局爬虫注册表（ctx 单一数据源 + import 期 fallback）、
名称冲突追踪与注册辅助函数。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from crawlo.spider import Spider

from crawlo.spider.exceptions import AmbiguousSpiderError

# 冲突追踪表：name -> [候选类完整路径列表]
# SpiderMeta 不再在 import 阶段 raise，而是后注册覆盖先注册 + warning，
# 冲突的候选类记入此表，get_spider_by_name 解析时抛 AmbiguousSpiderError。
_SPIDER_CONFLICTS: Dict[str, List[str]] = {}

class _SpiderRegistryProxy:
    """``_DEFAULT_SPIDER_REGISTRY`` 的代理对象。

    设计目标
    --------
    1. **ctx 为唯一数据源**：所有运行期读写最终落到
       ``ctx.registries.spider_registry``，消除"模块级 dict 与 ctx 各持一份"
       的双数据源同步问题。
    2. **import 期零副作用**：SpiderMeta 在类定义时即写入注册表，此时
       ``ApplicationContext`` 可能尚未创建。proxy 在 ctx 未就绪时回退到
       进程级 ``_fallback`` dict，**不触发** ``get_global_context(create_if_missing=True)``，
       满足约束："import crawlo 不触发 ctx 自动创建"。
    3. **首次 ctx 就绪时自动同步**：proxy 检测到 ctx 已创建时，把
       ``_fallback`` 中累积的注册项合并到 ``ctx.spider_registry``（仅一次），
       之后所有访问直接转发到 ctx。

    对外暴露 dict 兼容接口（``__getitem__`` / ``__setitem__`` / ``__contains__``
    / ``get`` / ``keys`` / ``values`` / ``items`` / ``clear`` / ``update`` /
    ``copy`` / ``__iter__`` / ``__len__``），使旧代码无感知地继续工作。
    """

    __slots__ = ("_fallback", "_callback_registered")

    def __init__(self) -> None:
        object.__setattr__(self, "_fallback", {})
        object.__setattr__(self, "_callback_registered", False)

    def _ensure_callback_registered(self) -> None:
        """惰性注册 ctx 就绪回调（仅一次）。

        通过 ``register_context_ready_callback`` 把 ``_sync_to_ctx`` 挂到
        ctx 创建事件上，使得 ``get_global_context()`` / ``reset_global_context()``
        / ``set_global_context()`` 创建新 ctx 后，fallback 中的注册项自动同步
        到新 ctx——即使用户直接访问 ``ctx.registries.spider_registry`` 而非
        通过 proxy。
        """
        if self._callback_registered:
            return
        try:
            from crawlo.core.application import register_context_ready_callback

            register_context_ready_callback(self._sync_to_ctx)
            object.__setattr__(self, "_callback_registered", True)
        except Exception:
            # application 模块不可用（极少见），降级为纯 fallback 模式
            pass

    def _sync_to_ctx(self, ctx: Any) -> None:
        """ctx 就绪回调：把 fallback 中累积的注册项同步到 ctx.spider_registry。

        - 不覆盖 ctx 中已有的注册项（运行期显式注册优先于 import 期自动注册）
        - 同步完成后清空 fallback
        """
        fallback = self._fallback
        if not fallback:
            return
        target = ctx.registries.spider_registry
        for name, cls in fallback.items():
            target.setdefault(name, cls)
        fallback.clear()

    def _target(self) -> Dict[str, Type["Spider"]]:
        """返回当前应当读写的真实 dict。

        - ctx 已就绪 → 返回 ``ctx.registries.spider_registry``，并把
          ``_fallback`` 中尚未同步的注册项合并过去（仅当 _fallback 非空时）。
        - ctx 未就绪（import 期或测试隔离场景）→ 返回 ``_fallback``。
        """
        self._ensure_callback_registered()
        from crawlo.core.application import get_global_context

        ctx = get_global_context(create_if_missing=False)
        if ctx is None:
            return self._fallback
        target = ctx.registries.spider_registry
        fallback = self._fallback
        if fallback:
            # 兜底同步：正常情况下回调已同步，这里处理回调未触发的边界
            for name, cls in fallback.items():
                target.setdefault(name, cls)
            fallback.clear()
        return target

    # === dict 兼容接口 ===

    def __getitem__(self, key: str) -> Type["Spider"]:
        return self._target()[key]

    def __setitem__(self, key: str, value: Type["Spider"]) -> None:
        self._target()[key] = value

    def __delitem__(self, key: str) -> None:
        del self._target()[key]

    def __contains__(self, key: object) -> bool:
        return key in self._target()

    def __iter__(self):
        return iter(self._target())

    def __len__(self) -> int:
        return len(self._target())

    def __eq__(self, other: object) -> bool:
        return self._target() == other

    def __ne__(self, other: object) -> bool:
        return self._target() != other

    def __repr__(self) -> str:
        return f"_SpiderRegistryProxy({self._target()!r})"

    def get(self, name: str, default: Any = None) -> Optional[Type["Spider"]]:
        return self._target().get(name, default)

    def keys(self):
        return self._target().keys()

    def values(self):
        return self._target().values()

    def items(self):
        return self._target().items()

    def setdefault(self, key: str, default: Any = None) -> Type["Spider"]:
        return self._target().setdefault(key, default)

    def pop(self, key: str, *args) -> Optional[Type["Spider"]]:
        return self._target().pop(key, *args)

    def clear(self) -> None:
        self._target().clear()

    def update(self, *args, **kwargs) -> None:
        self._target().update(*args, **kwargs)

    def copy(self) -> Dict[str, Type["Spider"]]:
        return self._target().copy()


# 全局爬虫注册表（proxy 转发到 ctx.registries.spider_registry，
# import 期回退到进程级 _fallback，避免触发 ctx 创建）

# 全局爬虫注册表（proxy 转发到 ctx.registries.spider_registry，
# import 期回退到进程级 _fallback，避免触发 ctx 创建）
_DEFAULT_SPIDER_REGISTRY: _SpiderRegistryProxy = _SpiderRegistryProxy()

def get_global_spider_registry() -> Dict[str, Type[Spider]]:
    """
    获取全局爬虫注册表（返回副本）。

    ctx 为唯一数据源，``_DEFAULT_SPIDER_REGISTRY`` 为
    proxy 转发到 ``ctx.registries.spider_registry``。本函数首次调用会触发
    ctx 创建（与旧行为一致），import 期的注册项通过 proxy 的 fallback
    自动同步到 ctx。

    返回副本以保持向后兼容（调用方修改副本不影响注册表）。
    """
    from crawlo.core.application import get_global_context
    ctx = get_global_context()
    # 访问 _DEFAULT_SPIDER_REGISTRY 触发 fallback → ctx 同步（如有）
    _DEFAULT_SPIDER_REGISTRY._target()  # noqa: B018  # 触发同步副作用
    return ctx.registries.spider_registry.copy()


def get_spider_by_name(name: str) -> Optional[Type[Spider]]:
    """
    根据名称获取爬虫类

    如果该 name 存在多个候选类（注册冲突），抛出 AmbiguousSpiderError，
    错误信息列出所有候选类的完整模块路径。

    Args:
        name: 爬虫名称

    Returns:
        Optional[Type[Spider]]: 爬虫类或None

    Raises:
        AmbiguousSpiderError: 当该 name 有多个候选类时
    """
    if name in _SPIDER_CONFLICTS:
        raise AmbiguousSpiderError(name, _SPIDER_CONFLICTS[name])
    return _DEFAULT_SPIDER_REGISTRY.get(name)


def get_all_spider_classes() -> List[Type[Spider]]:
    """
    获取所有注册的爬虫类
    
    Returns:
        List[Type[Spider]]: 爬虫类列表
    """
    return list(set(_DEFAULT_SPIDER_REGISTRY.values()))


def get_spider_names() -> List[str]:
    """
    获取所有爬虫名称
    
    Returns:
        List[str]: 爬虫名称列表
    """
    return list(_DEFAULT_SPIDER_REGISTRY.keys())


def is_spider_registered(name: str) -> bool:
    """
    检查爬虫是否已注册
    
    Args:
        name: 爬虫名称
        
    Returns:
        bool: 是否已注册
    """
    return name in _DEFAULT_SPIDER_REGISTRY


def unregister_spider(name: str) -> bool:
    """
    取消注册爬虫（仅用于测试）

    Args:
        name: 爬虫名称

    Returns:
        bool: 是否成功取消注册
    """
    existed = name in _DEFAULT_SPIDER_REGISTRY
    if existed:
        del _DEFAULT_SPIDER_REGISTRY[name]
    _SPIDER_CONFLICTS.pop(name, None)
    return existed


def register_spider(name: str, cls: Type[Spider], override: bool = True) -> None:
    """
    显式注册爬虫，用于消除名称歧义。

    当多个爬虫类注册了相同 name 导致 AmbiguousSpiderError 时，
    使用此函数显式指定要使用的爬虫类，清除冲突记录。

    Args:
        name: 爬虫名称
        cls: 爬虫类
        override: 是否覆盖已注册的同名爬虫（默认 True）
    """
    if not override and name in _DEFAULT_SPIDER_REGISTRY:
        raise ValueError(f"爬虫名称 '{name}' 已注册，设置 override=True 以覆盖。")
    _DEFAULT_SPIDER_REGISTRY[name] = cls
    # 清除冲突记录——用户已显式指定
    _SPIDER_CONFLICTS.pop(name, None)


def reset_spider_registry():
    """
    重置爬虫注册表（用于测试隔离）

    警告：此函数会清空所有已注册的爬虫，仅在测试中使用
    """
    _DEFAULT_SPIDER_REGISTRY.clear()
    _SPIDER_CONFLICTS.clear()

