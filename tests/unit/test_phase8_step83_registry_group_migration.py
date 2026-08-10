"""
Phase 8 Step 8.3 验收：注册表组 + bot 组迁移（DI 容器优先模式 + ctx fallback 等价）
=====================================================================

断言：
1. 默认「懒初始化」路径：不依赖 get_global_context 前置 set_global_context 即可工作
   （所有 fallback 路径自动新构造并 rebind）
2. 容器优先路径：若 ctx 已创建（Phase 8.2 绑定了三大 Context + 常用 channel），模块级
   getter 返回的实例与 default_container.resolve(...) 返回同一引用
3. 子上下文属性：factories 的 components_registered 写入 RegistryContext；notifier /
   deduplicator reset 写入 NotificationContext 对应字段；config_loader 的
   bot_config_loaded 写入 NotificationContext。
4. 首次 getter 触发 rebind 后，后续 @inject 自动装配能拿到同一引用。
"""

from __future__ import annotations

from typing import Dict

import pytest

# 本文件是 bot/container 旧路径 → 新路径的迁移桥验收测试，旧路径是测试对象本身，
# 允许其 DeprecationWarning 出现（其余测试仍强制 error）。
pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


@pytest.fixture(autouse=True)
def _clean_default_container_and_global_ctx():
    from crawlo.container import default_container
    from crawlo.core import application as app_mod

    # Before
    app_mod.reset_global_context()
    default_container.clear()
    yield
    # After
    default_container.clear()
    app_mod.reset_global_context()


# ---------- 组 A：注册表三件套（ComponentRegistry / InitializerRegistry / JobRegistry） ----------

def test_component_registry_lazy_path_rebinds_to_container():
    """factories.get_component_registry() 在无全局 ctx 时懒创建并 rebind。"""
    from crawlo.container import default_container
    from crawlo.core.component_registry import ComponentRegistry, get_component_registry

    assert not default_container.is_registered(ComponentRegistry)
    reg = get_component_registry()
    assert isinstance(reg, ComponentRegistry)
    # fallback 路径会在 lazy 构造后 rebind，故现在容器里有注册
    assert default_container.is_registered(ComponentRegistry)
    assert default_container.resolve(ComponentRegistry) is reg


def test_initializer_registry_lazy_path_rebinds_to_container():
    """initialization.get_global_registry() lazy 创建 + rebind。"""
    from crawlo.container import default_container
    from crawlo.core.application import InitializerRegistry, get_global_registry

    reg = get_global_registry()
    assert isinstance(reg, InitializerRegistry)
    assert default_container.resolve(InitializerRegistry) is reg


def test_job_registry_lazy_path_rebinds_to_container():
    """scheduling.get_job_registry() lazy 创建 + rebind。"""
    from crawlo.container import default_container
    from crawlo.commands.registry import JobRegistry, get_job_registry

    reg = get_job_registry()
    assert isinstance(reg, JobRegistry)
    assert default_container.resolve(JobRegistry) is reg


def test_context_created_registry_served_from_container():
    """ApplicationContext 已提前构造并预填注册表后，getter 直接从容器解析、不再重复创建。"""
    from crawlo.container import default_container
    from crawlo.core.application import ApplicationContext
    from crawlo.core.component_registry import ComponentRegistry, get_component_registry
    from crawlo.core.application import InitializerRegistry, get_global_registry
    from crawlo.commands.registry import JobRegistry, get_job_registry

    ctx = ApplicationContext()
    ctx.registries.component_registry = ComponentRegistry()
    ctx.registries.initializer_registry = InitializerRegistry()
    ctx.registries.job_registry = JobRegistry()
    # 模拟 Phase 8.2 执行：rebind 这 3 个
    default_container.register_instance(ComponentRegistry, ctx.registries.component_registry)
    default_container.register_instance(InitializerRegistry, ctx.registries.initializer_registry)
    default_container.register_instance(JobRegistry, ctx.registries.job_registry)

    assert get_component_registry() is ctx.registries.component_registry
    assert get_global_registry() is ctx.registries.initializer_registry
    assert get_job_registry() is ctx.registries.job_registry
    # 且与容器 resolve 完全一致（即 DI 装配生效）
    assert default_container.resolve(ComponentRegistry) is ctx.registries.component_registry
    assert default_container.resolve(InitializerRegistry) is ctx.registries.initializer_registry
    assert default_container.resolve(JobRegistry) is ctx.registries.job_registry


def test_factories_ensure_components_registered_writes_to_registry_context():
    """factories._ensure_components_registered 改走容器的 RegistryContext 写入。

    这里只断言：RegistryContext.components_registered 先 False → 调用后 True。
    """
    from crawlo.container import default_container
    from crawlo.core.application import ApplicationContext
    from crawlo.core.factories import _ensure_components_registered

    ctx = ApplicationContext()
    # Phase 8.2 已在 __post_init__ 把 ctx.registries 注册进 default_container
    assert default_container.is_registered(type(ctx.registries))
    assert ctx.registries.components_registered is False

    _ensure_components_registered()

    assert ctx.registries.components_registered is True


# ---------- 组 B：bot 通知子系统 getter（5 channels + 2 managers + 1 handler + 1 deduplicator + 1 notifier） ----------

def test_all_five_channels_lazy_rebind_and_container_prefers():
    """5 个通知渠道 getter 都走「懒创建→rebind」；ApplicationContext 建后仍从容器拿同一引用。"""
    from crawlo.container import default_container
    from crawlo.bot.channels.dingtalk import DingTalkChannel, get_dingtalk_channel
    from crawlo.bot.channels.email import EmailChannel, get_email_channel
    from crawlo.bot.channels.feishu import FeishuChannel, get_feishu_channel
    from crawlo.bot.channels.sms import SmsChannel, get_sms_channel
    from crawlo.bot.channels.wecom import WeComChannel, get_wecom_channel

    chs = [
        (DingTalkChannel, get_dingtalk_channel()),
        (EmailChannel, get_email_channel()),
        (FeishuChannel, get_feishu_channel()),
        (SmsChannel, get_sms_channel()),
        (WeComChannel, get_wecom_channel()),
    ]
    for cls, inst in chs:
        assert isinstance(inst, cls)
        assert default_container.resolve(cls) is inst


def test_template_manager_and_resource_monitor_lazy_rebind():
    """templates.manager.get_template_manager + monitoring.templates.get_resource_monitor_manager。"""
    from crawlo.container import default_container
    from crawlo.bot.templates.manager import (
        MessageTemplateManager,
        get_template_manager,
    )
    from crawlo.bot.monitoring.templates import (
        ResourceMonitorTemplateManager,
        get_resource_monitor_manager,
    )

    m1 = get_template_manager(custom_templates={"a": 1})
    assert isinstance(m1, MessageTemplateManager)
    assert default_container.resolve(MessageTemplateManager) is m1

    m2 = get_resource_monitor_manager()
    assert isinstance(m2, ResourceMonitorTemplateManager)
    assert default_container.resolve(ResourceMonitorTemplateManager) is m2


def test_notification_handler_and_deduplicator_lazy_dcl_and_rebind():
    """handlers.get_notification_handler + deduplicator.get_deduplicator 懒创建 + rebind。"""
    from crawlo.container import default_container
    from crawlo.bot.core.handlers import CrawlerNotificationHandler, get_notification_handler
    from crawlo.bot.utils.deduplicator import MessageDeduplicator, get_deduplicator

    h = get_notification_handler()
    assert isinstance(h, CrawlerNotificationHandler)
    assert default_container.resolve(CrawlerNotificationHandler) is h

    d = get_deduplicator(time_window=10)
    assert isinstance(d, MessageDeduplicator)
    assert default_container.resolve(MessageDeduplicator) is d


def test_notifier_built_lazy_dcl_registers_five_channels_and_rebinds():
    """notifier 懒构造时：注册 5 个 channels；自身 rebind 进容器。"""
    from crawlo.container import default_container
    from crawlo.bot.core.notifier import NotificationDispatcher, get_notifier
    from crawlo.bot.channels import (
        get_dingtalk_channel,
        get_feishu_channel,
        get_wecom_channel,
        get_email_channel,
        get_sms_channel,
    )

    dispatcher = get_notifier()
    assert isinstance(dispatcher, NotificationDispatcher)
    assert default_container.resolve(NotificationDispatcher) is dispatcher
    # NotificationDispatcher 通过 _channels: Dict[str, Channel] 存储；values() 即实例集
    expected = {
        get_dingtalk_channel(),
        get_feishu_channel(),
        get_wecom_channel(),
        get_email_channel(),
        get_sms_channel(),
    }
    actual = set(getattr(dispatcher, "_channels", {}).values())
    assert expected.issubset(actual)


def test_reset_notifier_and_deduplicator_via_notification_context():
    """reset_notifier / reset_deduplicator 通过 NotificationContext 属性写位。

    关键：必须把测试用 ctx ``set_global_context(ctx)``，否则 getter 的 fallback 分支
    会在 _Sentinel 里再造一个 ctx，导致「我写的」和「测试断言的」不是同一个对象。
    """
    from crawlo.core import application as app_mod
    from crawlo.core.application import ApplicationContext
    from crawlo.bot.core.notifier import get_notifier, reset_notifier
    from crawlo.bot.utils.deduplicator import get_deduplicator, reset_deduplicator

    ctx = ApplicationContext()
    app_mod.set_global_context(ctx)

    _ = get_notifier()
    _ = get_deduplicator(60)
    assert ctx.notifications.notifier is not None
    assert ctx.notifications.deduplicator is not None

    reset_notifier()
    reset_deduplicator()
    # 写位通过容器 NotificationContext，等价于 ctx.notifications.xxx
    assert ctx.notifications.notifier is None
    assert ctx.notifications.deduplicator is None


def test_config_loader_bot_config_loaded_writes_to_notification_context():
    """config_loader.ensure_config_loaded 通过 NotificationContext 读写 bot_config_loaded。"""
    from crawlo.core.application import ApplicationContext
    from crawlo.bot.utils.config_loader import ensure_config_loaded

    ctx = ApplicationContext()
    assert ctx.notifications.bot_config_loaded is False
    ensure_config_loaded()
    # bot_config_loaded 默认是 True（要么 dingtalk webhook 有设置早返回，要么 apply_settings_config 跑完）
    assert ctx.notifications.bot_config_loaded is True


# ---------- 组 C：@inject 前向兼容：容器里的注册表被 resolve 成功 ----------
#
# 注意：@inject 需要对顶层模块函数装饰才能解析 forward ref（嵌套 closure 里的局部 symbol
# 不在 func.__globals__，get_type_hints 会退化成 str）——容器的相关行为在
# tests/unit/test_container.py 已覆盖，这里只验证「三个 registry rebind 完成后，
# default_container.resolve() 拿到的与 getter 返回的是同一引用」，等价于 @inject
# 的实际效果。

def test_registry_resolve_after_lazy_getter_returns_same_reference():
    """get_*_registry() 触发 rebind 后，容器解析值与 getter 单例完全一致（等价 @inject）。"""
    from crawlo.container import default_container
    from crawlo.core.component_registry import ComponentRegistry, get_component_registry
    from crawlo.core.application import InitializerRegistry, get_global_registry
    from crawlo.commands.registry import JobRegistry, get_job_registry

    reg1 = get_component_registry()
    reg2 = get_global_registry()
    reg3 = get_job_registry()

    r1 = default_container.resolve(ComponentRegistry)
    r2 = default_container.resolve(InitializerRegistry)
    r3 = default_container.resolve(JobRegistry)
    assert r1 is reg1
    assert r2 is reg2
    assert r3 is reg3

    # 连续多次 resolve 仍一致（SINGLETON 语义：register_instance 行为）
    assert default_container.resolve(ComponentRegistry) is reg1
    assert default_container.resolve(InitializerRegistry) is reg2
    assert default_container.resolve(JobRegistry) is reg3
