#!/usr/bin/python
# -*- coding:UTF-8 -*-

# Crawlo core modules
# Provides core components and initialization functionality of the framework

# NOTE: initialization imports are deferred to __getattr__ to avoid
# circular imports (initialization → utils.misc → crawlo.spider → ...).


def __getattr__(name):
    """PEP 562: lazily provide initialization symbols on first access.

    This prevents ``from ..initialization import ...`` at module level,
    which would trigger a heavy import chain (initialization → utils.misc
    → crawlo.spider) and cause circular imports when ``crawlo.core.exceptions``
    is imported during ``crawlo.spider`` initialization.
    """
    if name in ('initialize_framework', 'is_framework_ready'):
        from ..initialization import initialize_framework, is_framework_ready
        globals()['initialize_framework'] = initialize_framework
        globals()['is_framework_ready'] = is_framework_ready
        return globals()[name]
    raise AttributeError(f"module 'crawlo.core' has no attribute {name!r}")

# Phase 4 Step 3：facade 测试钩子（单元测试可注入 mock，避免触发 ctx 创建）
_FRAMEWORK_INITIALIZER_OVERRIDE = None


def _override_framework_initializer(initializer):
    """测试钩子：注入/清除 CoreInitializer mock。

    传 None 清除 override，恢复从 ctx / SingletonMeta 解析。
    非 None 时，``get_framework_initializer()`` 直接返回该实例，
    不访问 ctx，不触发 SingletonMeta。
    """
    global _FRAMEWORK_INITIALIZER_OVERRIDE
    _FRAMEWORK_INITIALIZER_OVERRIDE = initializer


def get_framework_initializer():
    """Lazy facade: 获取 CoreInitializer 实例。

    v2.0：ctx 为唯一数据源，不再回退到 SingletonMeta 全局单例。

    解析顺序：
    1. 测试 override（``_override_framework_initializer`` 注入的 mock）
    2. ctx 就绪且 ``ctx.runtime.initializer`` 已设置 → 返回之
    3. ctx 就绪但 initializer 未设置 → 创建，挂到 ctx，返回
    4. ctx 未就绪 → 抛 RuntimeError（v2.0 不再回退到全局单例）

    关键：本函数是 lazy 的，模块加载期不访问 ctx，调用时才解析——
    满足 Phase 4 验收点"import crawlo 不触发 ctx 创建"。
    """
    # 1. 测试 override
    if _FRAMEWORK_INITIALIZER_OVERRIDE is not None:
        return _FRAMEWORK_INITIALIZER_OVERRIDE

    # 2~3. ctx 就绪路径
    from crawlo.core.application import get_global_context
    ctx = get_global_context(create_if_missing=False)
    if ctx is not None:
        if ctx.runtime.initializer is None:
            from ..initialization.core import CoreInitializer
            ctx.runtime.initializer = CoreInitializer()
        return ctx.runtime.initializer

    # 4. ctx 未就绪：v2.0 不再回退到全局单例，直接报错
    raise RuntimeError(
        "get_framework_initializer() called before ApplicationContext is ready. "
        "Ensure ApplicationContext is initialized before calling this function."
    )


def get_framework_logger(name='crawlo.core'):
    """Get framework logger - compatibility function"""
    from ..logging import get_logger
    return get_logger(name)


__all__ = [
    'initialize_framework',
    'get_framework_initializer',
    'is_framework_ready',
    'get_framework_logger',
    # 测试钩子
    '_override_framework_initializer',
]
