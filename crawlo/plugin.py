#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo 插件注册表（P1-B1）
=========================

统一扩展点：middleware / pipeline / extension 三类插件。

双通道：
1. 注册表 API：``register_middleware('my_mw', MyMiddleware)`` 后，
   配置里可直接写短名称 ``MIDDLEWARES = ['my_mw']``；
2. 字符串路径：``MIDDLEWARES = ['my_pkg.middleware.MyMiddleware']``
   （保持与内置组件一致的加载方式，注册表未命中时回退到 import）。

解析优先级（load_object）：
    完整路径 import → 类型前缀（``middleware:my_mw``）→ 短名称注册表。
"""

from typing import Dict, Any, Optional

_logger = None


def _get_logger():
    """惰性获取 logger（避免 plugin ← logging ← 其他包 的循环导入）。"""
    global _logger
    if _logger is None:
        from crawlo.logging import get_logger
        _logger = get_logger(__name__)
    return _logger

# 类型前缀常量（配置中可用 ``middleware:name`` 形式显式指定类型）
PREFIX_MIDDLEWARE = "middleware"
PREFIX_PIPELINE = "pipeline"
PREFIX_EXTENSION = "extension"

# 三类注册表：短名称 → 类对象
_MIDDLEWARE_REGISTRY: Dict[str, Any] = {}
_PIPELINE_REGISTRY: Dict[str, Any] = {}
_EXTENSION_REGISTRY: Dict[str, Any] = {}


def _validate(name: str, cls: Any, kind: str) -> None:
    if not name or not isinstance(name, str):
        raise ValueError(f"{kind} 名称必须是非空字符串，got {name!r}")
    if cls is None:
        raise ValueError(f"{kind} 类不能为 None")
    if not isinstance(cls, type):
        raise ValueError(f"{kind} 必须是类对象，got {type(cls).__name__}")


def register_middleware(name: str, cls: type) -> None:
    """注册自定义中间件类，配置中可用短名称引用。"""
    _validate(name, cls, "中间件")
    _MIDDLEWARE_REGISTRY[name] = cls
    _get_logger().info(
        f"Registered middleware: {name} -> {cls.__module__}.{cls.__name__}"
    )


def unregister_middleware(name: str) -> bool:
    """注销中间件注册项。"""
    existed = name in _MIDDLEWARE_REGISTRY
    if existed:
        del _MIDDLEWARE_REGISTRY[name]
    return existed


def register_pipeline(name: str, cls: type) -> None:
    """注册自定义管道类，配置中可用短名称引用。"""
    _validate(name, cls, "管道")
    _PIPELINE_REGISTRY[name] = cls
    _get_logger().info(
        f"Registered pipeline: {name} -> {cls.__module__}.{cls.__name__}"
    )


def unregister_pipeline(name: str) -> bool:
    """注销管道注册项。"""
    existed = name in _PIPELINE_REGISTRY
    if existed:
        del _PIPELINE_REGISTRY[name]
    return existed


def register_extension(name: str, cls: type) -> None:
    """注册自定义扩展类，配置中可用短名称引用。"""
    _validate(name, cls, "扩展")
    _EXTENSION_REGISTRY[name] = cls
    _get_logger().info(
        f"Registered extension: {name} -> {cls.__module__}.{cls.__name__}"
    )


def unregister_extension(name: str) -> bool:
    """注销扩展注册项。"""
    existed = name in _EXTENSION_REGISTRY
    if existed:
        del _EXTENSION_REGISTRY[name]
    return existed


def resolve_plugin(name: str) -> Optional[Any]:
    """按名称解析已注册插件（load_object 的兜底通道）。

    支持两种格式：
    - 短名称：``my_mw``（依次查 middleware / pipeline / extension 注册表）
    - 类型前缀：``middleware:my_mw``（显式指定类型，避免跨类型重名）

    未命中返回 None，由调用方回退到字符串路径 import。
    """
    kind: Optional[str] = None
    short_name = name
    if ":" in name:
        kind, _, short_name = name.partition(":")

    if kind == PREFIX_MIDDLEWARE:
        return _MIDDLEWARE_REGISTRY.get(short_name)
    if kind == PREFIX_PIPELINE:
        return _PIPELINE_REGISTRY.get(short_name)
    if kind == PREFIX_EXTENSION:
        return _EXTENSION_REGISTRY.get(short_name)

    # 无前缀：依次查询（注册名通常全局唯一）
    if short_name in _MIDDLEWARE_REGISTRY:
        return _MIDDLEWARE_REGISTRY[short_name]
    if short_name in _PIPELINE_REGISTRY:
        return _PIPELINE_REGISTRY[short_name]
    if short_name in _EXTENSION_REGISTRY:
        return _EXTENSION_REGISTRY[short_name]
    return None


def get_registered_names() -> Dict[str, list]:
    """返回全部已注册插件名（供调试/文档使用）。"""
    return {
        "middleware": sorted(_MIDDLEWARE_REGISTRY),
        "pipeline": sorted(_PIPELINE_REGISTRY),
        "extension": sorted(_EXTENSION_REGISTRY),
    }


__all__ = [
    "register_middleware",
    "unregister_middleware",
    "register_pipeline",
    "unregister_pipeline",
    "register_extension",
    "unregister_extension",
    "resolve_plugin",
    "get_registered_names",
    "PREFIX_MIDDLEWARE",
    "PREFIX_PIPELINE",
    "PREFIX_EXTENSION",
]
