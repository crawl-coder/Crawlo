"""
Phase 8 Step 8.1 容器基础设施单元测试
====================================

覆盖：
1. Scope.SINGLETON（register_instance + register_singleton）
2. Scope.TRANSIENT — 每次 resolve 新建
3. Scope.REQUEST — 按 scope_id 隔离
4. @inject 自动装配（含调用方显式传值优先级更高）
5. 未注册类型抛 ContainerResolutionError（诊断信息完整）
6. clear 两种模式（全量 / 单 scope_id）
7. 线程安全（并发 resolve singleton 只建 1 次实例）
8. **架构守护**：import crawlo.container 后不触发 ApplicationContext 创建
   （通过子进程跑，隔离副作用）
"""

from __future__ import annotations

import subprocess
import sys
import threading
import textwrap
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

import pytest

from crawlo.core.application import (
    Container,
    ContainerResolutionError,
    Scope,
    default_container,
    inject,
)


# -------------------------------------------------------------------
# 1. SINGLETON
# -------------------------------------------------------------------
class _MyService:
    """测试用服务"""
    instance_counter: int = 0

    def __init__(self, value: int = 0) -> None:
        _MyService.instance_counter += 1
        self.value = value


def test_register_instance_and_resolve():
    container = Container()
    svc = _MyService(value=42)
    container.register_instance(_MyService, svc)
    got = container.resolve(_MyService)
    assert got is svc
    assert got.value == 42


def test_register_singleton_lazy_factory():
    container = Container()
    build_counter: List[int] = []

    def factory():
        build_counter.append(1)
        return _MyService(value=100)

    container.register_singleton(_MyService, factory)
    # 未 resolve 前不执行 factory
    assert len(build_counter) == 0
    a = container.resolve(_MyService)
    b = container.resolve(_MyService)
    assert a is b
    assert a.value == 100
    assert len(build_counter) == 1, f"factory 应只执行 1 次，实际 {len(build_counter)} 次"


def test_register_singleton_then_override_with_instance_works_correctly():
    """重复 register_* 以最后一次为准（没有保护，按需覆盖即覆盖）。"""
    container = Container()
    a = _MyService(value=1)
    b = _MyService(value=2)
    container.register_instance(_MyService, a)
    container.register_instance(_MyService, b)
    assert container.resolve(_MyService) is b


# -------------------------------------------------------------------
# 2. TRANSIENT
# -------------------------------------------------------------------
def test_register_transient_creates_new_each_resolve():
    container = Container()
    counter: List[int] = []

    def factory():
        counter.append(1)
        return _MyService(value=len(counter) * 10)

    container.register_transient(_MyService, factory)
    a = container.resolve(_MyService)
    b = container.resolve(_MyService)
    assert a is not b
    assert a.value == 10
    assert b.value == 20
    assert len(counter) == 2


# -------------------------------------------------------------------
# 3. REQUEST 作用域（按 scope_id 隔离）
# -------------------------------------------------------------------
def test_request_scope_isolated_per_scope_id():
    container = Container()
    counter: List[int] = []

    def factory():
        counter.append(1)
        return _MyService(value=len(counter))

    container.register_request_factory(_MyService, factory)

    a1 = container.resolve(_MyService, scope_id="ctx-a")
    a2 = container.resolve(_MyService, scope_id="ctx-a")
    b1 = container.resolve(_MyService, scope_id="ctx-b")
    assert a1 is a2
    assert a1 is not b1
    # 两个 scope_id，各 1 次 factory 调用
    assert len(counter) == 2


def test_request_scope_without_scope_id_raises_contextual_error():
    container = Container()
    container.register_request_factory(_MyService, lambda: _MyService(1))
    with pytest.raises(ContainerResolutionError) as excinfo:
        container.resolve(_MyService)
    cause = excinfo.value.__cause__
    assert cause is not None and "requires scope_id" in str(cause)


# -------------------------------------------------------------------
# 4. @inject 自动装配
# -------------------------------------------------------------------
class _INotifier:
    """依赖接口（占位类）"""


def test_inject_decorator_autowires_registered_type():
    c = Container()
    # 替换 default_container 为临时容器？——太侵入；用独立方法验证：
    from crawlo.core import application as app_mod
    old = app_mod.default_container
    app_mod.default_container = c
    try:
        notifier_inst = _INotifier()
        c.register_instance(_INotifier, notifier_inst)

        class DingTalk:
            @inject
            def __init__(self, notifier: _INotifier, name: str = "dt"):
                self.notifier = notifier
                self.name = name

        ch = DingTalk()  # 不传 notifier
        assert ch.notifier is notifier_inst
        assert ch.name == "dt"

        # 显式传值优先级更高
        another = _INotifier()
        ch2 = DingTalk(notifier=another, name="x")
        assert ch2.notifier is another
        assert ch2.name == "x"
    finally:
        app_mod.default_container = old


def test_inject_skips_unregistered_type_to_let_original_func_raise():
    """未注册的类型：@inject 不传参，由原函数抛 TypeError（用户可手动传）。"""
    c = Container()
    from crawlo.core import application as app_mod
    old = app_mod.default_container
    app_mod.default_container = c
    try:
        class Email:
            @inject
            def __init__(self, notifier: _INotifier):
                self.notifier = notifier

        with pytest.raises(TypeError):
            Email()  # 没注册、没传 → 原 __init__ 抛缺少参数 notifier

        notifier_inst = _INotifier()
        obj = Email(notifier=notifier_inst)  # 手动传 OK
        assert obj.notifier is notifier_inst
    finally:
        app_mod.default_container = old


# -------------------------------------------------------------------
# 5. ContainerResolutionError 诊断信息
# -------------------------------------------------------------------
def test_resolution_error_lists_registered_types_and_call_stack():
    container = Container()

    class _FakeNotifier:
        pass

    class _FakeQueue:
        pass

    container.register_instance(_FakeQueue, _FakeQueue())
    with pytest.raises(ContainerResolutionError) as excinfo:
        container.resolve(_FakeNotifier)

    msg = str(excinfo.value)
    assert "_FakeNotifier" in msg
    assert "_FakeQueue" in msg, "错误信息应包含已注册的类型，帮助定位"
    assert "Caller stack" in msg, "错误信息应包含裁剪过的调用栈"


# -------------------------------------------------------------------
# 6. clear
# -------------------------------------------------------------------
def test_clear_all_wipes_registry_and_request_buckets():
    c = Container()
    c.register_instance(_MyService, _MyService(1))
    c.register_request_factory(_INotifier, lambda: _INotifier())
    c.resolve(_INotifier, scope_id="ctx-1")
    assert c.is_registered(_MyService)
    c.clear()
    assert not c.is_registered(_MyService)
    assert c.registered_types() == []


def test_clear_scope_id_only_wipes_request_bucket_for_that_scope():
    c = Container()
    c.register_request_factory(_MyService, lambda: _MyService(0))
    a1 = c.resolve(_MyService, scope_id="ctx-a")
    b1 = c.resolve(_MyService, scope_id="ctx-b")

    c.clear(scope_id="ctx-a")

    # ctx-b 的缓存保留
    assert c.resolve(_MyService, scope_id="ctx-b") is b1
    # ctx-a 被清了 → 重新 factory → 新实例
    a2 = c.resolve(_MyService, scope_id="ctx-a")
    assert a1 is not a2


# -------------------------------------------------------------------
# 7. 线程安全：并发 resolve singleton 只构造 1 次
# -------------------------------------------------------------------
def test_concurrent_singleton_resolve_builds_once():
    N_WORKERS = 50
    N_ROUNDS = 5
    for _ in range(N_ROUNDS):
        container = Container()
        build_log: List[float] = []

        def factory():
            # 模拟有构造耗时的单例（放大竞态窗口）
            build_log.append(time.monotonic())
            time.sleep(0.002)
            return _MyService(1)

        container.register_singleton(_MyService, factory)
        results: List[_MyService] = []

        def worker():
            return container.resolve(_MyService)

        with ThreadPoolExecutor(max_workers=N_WORKERS) as pool:
            futs = [pool.submit(worker) for _ in range(N_WORKERS)]
            for f in as_completed(futs):
                results.append(f.result())

        # 所有线程拿到同一实例
        first = results[0]
        for r in results[1:]:
            assert r is first, "并发 resolve singleton 必须拿到同一对象"
        # factory 只执行 1 次
        assert len(build_log) == 1, f"factory 应只执行 1 次，实际 {len(build_log)}"


def test_container_isolated_instances_do_not_share_state():
    """两个独立 Container 实例不应互相污染（验证 default_container 是全局仅此一个）。"""
    a = Container()
    b = Container()
    a.register_instance(_MyService, _MyService(1))
    assert not b.is_registered(_MyService)
    with pytest.raises(ContainerResolutionError):
        b.resolve(_MyService)


# -------------------------------------------------------------------
# 8. 架构守护：import crawlo.container 不触发 ApplicationContext 创建
# -------------------------------------------------------------------
_CHECK_MODULES_CODE = textwrap.dedent(
    """
    import warnings
    # 废弃 shim 的薄壳性质是断言对象，DeprecationWarning 是预期行为
    warnings.simplefilter('ignore', DeprecationWarning)
    import crawlo.container as _c
    from crawlo.container import default_container, inject, Container, ContainerResolutionError, Scope
    # 只验证 container 模块本身被 import 后，ApplicationContext 仍是 None
    from crawlo.core import application as app_mod
    import sys
    # 显式查应用层的 _global_context 哨兵
    ctx_ptr = app_mod._global_context
    if ctx_ptr is not None:
        print(f"FAIL: ApplicationContext was created during import! ctx={ctx_ptr!r}",
              file=sys.stderr)
        sys.exit(1)
    # default_container 已创建但空
    if not isinstance(default_container, Container):
        print("FAIL: default_container not created", file=sys.stderr)
        sys.exit(2)
    print("OK: container imports lazy, no ApplicationContext side-effects")
    """
)


def _run_isolated_check(code: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_import_container_does_not_create_application_context():
    result = _run_isolated_check(_CHECK_MODULES_CODE)
    assert result.returncode == 0, (
        f"import crawlo.container 期间意外触发了 ApplicationContext 创建。\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "OK: container imports lazy" in result.stdout, (result.stdout, result.stderr)


# -------------------------------------------------------------------
# 9. 额外：Rlock 重入——在 factory 内部 resolve 另一类型时不产生死锁
# -------------------------------------------------------------------
def test_nested_resolve_inside_singleton_factory_does_not_deadlock():
    c = Container()

    class _Repo:
        pass

    class _Service:
        def __init__(self, repo: _Repo) -> None:
            self.repo = repo

    repo_inst = _Repo()
    c.register_instance(_Repo, repo_inst)

    def service_factory():
        # SINGLETON factory 内部再 resolve _Repo → 容器内部 RLock 可重入
        repo = c.resolve(_Repo)
        return _Service(repo=repo)

    c.register_singleton(_Service, service_factory)
    svc = c.resolve(_Service)
    assert isinstance(svc, _Service)
    assert svc.repo is repo_inst
