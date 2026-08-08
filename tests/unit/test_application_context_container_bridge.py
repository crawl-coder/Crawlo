"""
Phase 8 Step 8.2 验收：ApplicationContext ↔ DI Container 桥接
==============================================================

断言：
1. 新建 ApplicationContext 后，default_container 中可解析 RegistryContext / NotificationContext /
   RuntimeContext / ApplicationContext 四个类型，解析结果即 ctx 对应实例。
2. default_container.register_instance() 可追加延迟创建的组件并被解析。
3. cleanup() 后，self.id 为 scope_id 的 REQUEST 作用域 bucket 被清（_unbind_from_container）。
4. reset_global_context() + 再新建 ctx，容器里仍是新 ctx（不冲突旧注册）。
"""

from __future__ import annotations

from typing import Dict

import pytest


@pytest.fixture(autouse=True)
def _restore_global_ctx(monkeypatch):
    """每个测试前后，保证 _global_context 哨兵不被遗留污染其他测试。

    方式：通过 application.reset_global_context() / set_global_context 维护。
    """
    from crawlo.core import application as app_mod
    # Before
    original = app_mod._global_context
    app_mod.reset_global_context()
    yield
    # After：清 default_container 非构造器状态
    from crawlo.container import default_container
    default_container.clear()
    # 恢复原来的全局 ctx 哨兵（若有）
    if original is None:
        app_mod.reset_global_context()
    else:
        app_mod.set_global_context(original)


def test_new_ctx_binds_three_contexts_to_default_container():
    """新建 ctx 后，4 个核心类型可从 default_container resolve，并返回同一引用。"""
    from crawlo.container import default_container
    from crawlo.core.application import (
        ApplicationContext,
        NotificationContext,
        RegistryContext,
        RuntimeContext,
    )

    ctx = ApplicationContext()

    # ApplicationContext 本身
    assert default_container.resolve(ApplicationContext) is ctx
    # 三个子上下文
    assert default_container.resolve(RegistryContext) is ctx.registries
    assert default_container.resolve(NotificationContext) is ctx.notifications
    assert default_container.resolve(RuntimeContext) is ctx.runtime


def test_rebind_to_container_for_lazy_component():
    """default_container.register_instance(cls, inst) 后，新类型可解析为同一引用。"""
    from crawlo.container import default_container
    from crawlo.core.application import ApplicationContext

    ctx = ApplicationContext()

    class _FakeNotifier:
        def __init__(self, value: int) -> None:
            self.value = value

    inst = _FakeNotifier(777)
    default_container.register_instance(_FakeNotifier, inst)
    assert default_container.resolve(_FakeNotifier) is inst


@pytest.mark.asyncio
async def test_cleanup_unbinds_request_scope_bucket():
    """cleanup() 后，容器内以 self.id 为 scope_id 的 REQUEST 缓存被清。"""
    from crawlo.container import default_container
    from crawlo.core.application import ApplicationContext

    ctx = ApplicationContext()

    class _Worker:
        instances = 0

        def __init__(self) -> None:
            _Worker.instances += 1

    # 先塞一个以 ctx.id 为 scope_id 的 REQUEST 作用域对象
    default_container.register_request_factory(_Worker, lambda: _Worker())
    w1 = default_container.resolve(_Worker, scope_id=ctx.id)

    await ctx.cleanup()

    # 清理后再 resolve 会构造新实例（旧 bucket 被清）
    w2 = default_container.resolve(_Worker, scope_id=ctx.id)
    assert w1 is not w2
    assert _Worker.instances == 2


def test_recreate_ctx_does_not_conflict():
    """reset_global_context() → 再新建 ctx，容器里仍是新 ctx 的引用。"""
    from crawlo.container import default_container
    from crawlo.core.application import (
        ApplicationContext,
    )
    from crawlo.core import application as app_mod

    ctx_a = ApplicationContext()
    assert default_container.resolve(ApplicationContext) is ctx_a
    app_mod.set_global_context(ctx_a)

    app_mod.reset_global_context()
    ctx_b = ApplicationContext()
    # default_container 里现在指向 ctx_b（后创建）
    assert default_container.resolve(ApplicationContext) is ctx_b
    assert ctx_a is not ctx_b
    assert ctx_a.id != ctx_b.id


def test_application_context_id_is_unique():
    """ApplicationContext.id 应唯一（uuid4 默认生成）。"""
    from crawlo.core.application import ApplicationContext

    ids = {ApplicationContext().id for _ in range(32)}
    assert len(ids) == 32


def test_bind_to_container_errors_do_not_break_ctx():
    """_bind_to_container 抛异常时 ApplicationContext 仍然可用（防御性）。

    通过 monkeypatch default_container.register_instance 抛异常验证。
    """
    from crawlo.core.application import ApplicationContext, RegistryContext
    from crawlo import container as container_mod

    real = container_mod.default_container
    old_register = real.register_instance

    def flaky_register(cls, instance):
        # 第一次（ApplicationContext 自身注册）抛异常
        if cls is ApplicationContext:
            raise RuntimeError("fake binding failure")
        return old_register(cls, instance)

    real.register_instance = flaky_register  # type: ignore[assignment]
    try:
        ctx = ApplicationContext()
        # ctx 本身正常工作（registries.notifications.runtime 属性都能访问）
        assert isinstance(ctx.registries, RegistryContext)
    finally:
        real.register_instance = old_register  # type: ignore[assignment]
