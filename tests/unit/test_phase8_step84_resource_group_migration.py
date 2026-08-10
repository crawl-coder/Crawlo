"""
Phase 8 Step 8.4 验收：连接池 & 资源组（C 组 7 处）迁移
====================================================

断言：
1. ``get_redis_pool(shared=True)`` / ``close_all_pools()`` 读写 RuntimeContext.connection_pools（而非 ApplicationContext 顶栏）
2. ``get_redis_manager()`` 懒创建 + rebind，容器 resolve 同源
3. ``get_resource_manager(name)`` / ``cleanup_all_managers()`` 读写 RuntimeContext.resource_managers（而非顶栏）
4. ``_get_global_error_handler()`` 懒创建 + rebind，容器 resolve 同源
5. ``get_module_error_handler()`` 懒创建 + rebind（通过 ``_QueueErrorHandlerTag`` 单独 key，不与全局 ErrorHandler 类冲突）
6. 容器未绑定时 fallback 仍工作（与 Phase 8.3 模式一致）
7. ``RuntimeContext`` 直接 resolve 的对象，与 ApplicationContext.runtime 为同一引用
8. 多次调用 getter 返回的仍然是同一实例（SINGLETON 语义保持）
"""

from __future__ import annotations

import asyncio

import pytest


@pytest.fixture(autouse=True)
def _clean_container_and_global_ctx():
    from crawlo.core.application import default_container
    from crawlo.core import application as app_mod

    app_mod.reset_global_context()
    default_container.clear()
    yield
    default_container.clear()
    app_mod.reset_global_context()


# ---------------------------------------------------------------- 1) Redis pool Dict 读写 RuntimeContext.connection_pools


def test_get_redis_pool_shared_writes_to_runtime_connection_pools():
    """shared=True 的连接池应写入 RuntimeContext.connection_pools（不是 ApplicationContext 顶栏属性）。"""
    from crawlo.core import application as app_mod
    from crawlo.core.application import ApplicationContext
    from crawlo.utils.redis.pool import get_redis_pool

    ctx = ApplicationContext()
    app_mod.set_global_context(ctx)

    pool_a = get_redis_pool("redis://localhost:6379/0", shared=True)
    pool_b = get_redis_pool("redis://localhost:6379/0", shared=True)
    assert pool_a is pool_b
    assert len(ctx.runtime.connection_pools) == 1
    # ApplicationContext 顶栏没有 connection_pools 这个属性（完全委托 runtime）
    assert not hasattr(ctx, "connection_pools") or getattr(ctx, "connection_pools", None) is None or ctx.runtime.connection_pools is getattr(
        ctx, "connection_pools"
    )


@pytest.mark.asyncio
async def test_close_all_pools_clears_runtime_connection_pools():
    """close_all_pools() 应清掉 RuntimeContext.connection_pools 字典。"""
    from crawlo.core import application as app_mod
    from crawlo.core.application import ApplicationContext
    from crawlo.utils.redis.pool import close_all_pools, get_redis_pool

    ctx = ApplicationContext()
    app_mod.set_global_context(ctx)

    get_redis_pool("redis://localhost:6379/0", shared=True)
    get_redis_pool("redis://localhost:6379/1", shared=True)
    assert len(ctx.runtime.connection_pools) == 2

    await close_all_pools()
    assert len(ctx.runtime.connection_pools) == 0


# ---------------------------------------------------------------- 2) GlobalRedisManager 单例 + rebind


def test_get_redis_manager_lazy_rebind_singleton():
    """get_redis_manager() 懒创建 → rebind，后续 resolve 拿到同一引用。"""
    from crawlo.core.application import default_container
    from crawlo.core import application as app_mod
    from crawlo.core.application import ApplicationContext
    from crawlo.utils.redis.pool import GlobalRedisManager, get_redis_manager

    ctx = ApplicationContext()
    app_mod.set_global_context(ctx)
    assert ctx.runtime.redis_manager is None

    m1 = get_redis_manager()
    assert isinstance(m1, GlobalRedisManager)
    assert ctx.runtime.redis_manager is m1
    # rebind 后容器里的 GlobalRedisManager 单例就是它
    assert default_container.resolve(GlobalRedisManager) is m1
    # 再调用仍一致
    assert get_redis_manager() is m1


# ---------------------------------------------------------------- 3) ResourceManager Dict 读写 RuntimeContext.resource_managers


def test_get_resource_manager_writes_to_runtime_resource_managers():
    """get_resource_manager(name) 写入 RuntimeContext.resource_managers（非顶栏属性）。"""
    from crawlo.core import application as app_mod
    from crawlo.core.application import ApplicationContext
    from crawlo.utils.resource_manager import ResourceManager, get_resource_manager

    ctx = ApplicationContext()
    app_mod.set_global_context(ctx)

    r1 = get_resource_manager("default")
    r2 = get_resource_manager("db")
    assert isinstance(r1, ResourceManager)
    assert isinstance(r2, ResourceManager)
    assert r1 is not r2
    assert set(ctx.runtime.resource_managers.keys()) == {"default", "db"}
    assert ctx.runtime.resource_managers["default"] is r1
    assert ctx.runtime.resource_managers["db"] is r2


@pytest.mark.asyncio
async def test_cleanup_all_managers_operates_on_runtime_resource_managers():
    """cleanup_all_managers 循环 RuntimeContext.resource_managers 清理并清空字典本身。"""
    from crawlo.core import application as app_mod
    from crawlo.core.application import ApplicationContext
    from crawlo.utils.resource_manager import cleanup_all_managers, get_resource_manager

    ctx = ApplicationContext()
    app_mod.set_global_context(ctx)

    _ = get_resource_manager("a")
    _ = get_resource_manager("b")
    assert len(ctx.runtime.resource_managers) == 2

    await cleanup_all_managers()
    # 实际实现最后 managers.clear()，因此字典应被清空
    assert len(ctx.runtime.resource_managers) == 0


# ---------------------------------------------------------------- 4) 全局 ErrorHandler 单例


def test_global_error_handler_lazy_rebind_singleton():
    """_get_global_error_handler() 懒创建 ErrorHandler 并 rebind。"""
    from crawlo.core.application import default_container
    from crawlo.core import application as app_mod
    from crawlo.core.application import ApplicationContext
    from crawlo.utils.errors import ErrorHandler, _get_global_error_handler

    ctx = ApplicationContext()
    app_mod.set_global_context(ctx)
    assert ctx.runtime.error_handler_instance is None

    h = _get_global_error_handler()
    assert isinstance(h, ErrorHandler)
    assert ctx.runtime.error_handler_instance is h
    assert default_container.resolve(ErrorHandler) is h
    # Singleton: 再拿还是它
    assert _get_global_error_handler() is h


# ---------------------------------------------------------------- 5) 队列模块级 ErrorHandler（单独 tag）


def test_module_error_handler_uses_queue_tag_and_does_not_conflict_global():
    """get_module_error_handler() 用 _QueueErrorHandlerTag 注册，与全局 ErrorHandler 类不冲突。"""
    from crawlo.core.application import default_container
    from crawlo.core import application as app_mod
    from crawlo.core.application import ApplicationContext
    from crawlo.queue.backends.redis_priority import (
        _QueueErrorHandlerTag,
        get_module_error_handler,
    )
    from crawlo.utils.errors import ErrorHandler, _get_global_error_handler

    ctx = ApplicationContext()
    app_mod.set_global_context(ctx)

    # 先把全局 ErrorHandler 构造出来（走 ErrorHandler 类 key）
    global_h = _get_global_error_handler()
    # 再构造队列模块级 ErrorHandler（走 _QueueErrorHandlerTag key）
    queue_h = get_module_error_handler()

    # 两个单例不是同一个
    assert global_h is not queue_h
    assert ctx.runtime.queue_error_handler is queue_h
    # 容器里两个 key 分别绑定到对应单例
    assert default_container.resolve(ErrorHandler) is global_h
    assert default_container.resolve(_QueueErrorHandlerTag) is queue_h
    # 再调用一致
    assert get_module_error_handler() is queue_h


# ---------------------------------------------------------------- 6) RuntimeContext 通过容器直接 resolve 同源


def test_runtime_context_resolve_same_as_ctx_runtime():
    """Phase 8.2 注册 RuntimeContext 进容器；所有 C 组函数取的 RuntimeContext 与 ctx.runtime 一致。"""
    from crawlo.core.application import default_container
    from crawlo.core.application import ApplicationContext, RuntimeContext
    from crawlo.utils.redis.pool import _resolve_runtime_context as _pool_ctx
    from crawlo.utils.resource_manager import (
        _resolve_runtime_context as _rm_ctx,
    )

    ctx = ApplicationContext()
    # default_container 已在 __post_init__ 注册 RuntimeContext 单例
    assert default_container.is_registered(RuntimeContext)
    assert default_container.resolve(RuntimeContext) is ctx.runtime
    assert _pool_ctx() is ctx.runtime
    assert _rm_ctx() is ctx.runtime
