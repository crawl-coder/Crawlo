#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
P1-B1 插件注册表测试
===================

覆盖：
1. register_middleware / register_pipeline / register_extension 注册 + 注销；
2. load_object 双通道：短名称 / 类型前缀 / 完整路径 / module:attr；
3. 真实加载器集成：MiddlewareManager / PipelineManager / ExtensionManager
   通过 settings 短名称加载注册插件；
4. 未注册名称与非法输入的行为。
"""

import warnings

import pytest

from crawlo.plugin import (
    get_registered_names,
    register_extension,
    register_middleware,
    register_pipeline,
    resolve_plugin,
    unregister_extension,
    unregister_middleware,
    unregister_pipeline,
)
from crawlo.utils.misc import load_object


class FakeMiddleware:
    @classmethod
    def create_instance(cls, crawler):
        return cls()


class FakePipeline:
    @classmethod
    def from_crawler(cls, crawler):
        return cls()


class FakeExtension:
    @classmethod
    def create_instance(cls, crawler):
        return cls()


@pytest.fixture(autouse=True)
def _clean_registry():
    """每个测试后清理注册表，避免测试间污染。"""
    yield
    for name in list(get_registered_names()["middleware"]):
        unregister_middleware(name)
    for name in list(get_registered_names()["pipeline"]):
        unregister_pipeline(name)
    for name in list(get_registered_names()["extension"]):
        unregister_extension(name)


def test_register_and_resolve_middleware():
    register_middleware("fake_mw", FakeMiddleware)
    assert resolve_plugin("fake_mw") is FakeMiddleware
    assert resolve_plugin("middleware:fake_mw") is FakeMiddleware
    assert load_object("fake_mw") is FakeMiddleware
    assert unregister_middleware("fake_mw") is True
    assert resolve_plugin("fake_mw") is None


def test_register_and_resolve_pipeline():
    register_pipeline("fake_pipe", FakePipeline)
    assert resolve_plugin("pipeline:fake_pipe") is FakePipeline
    assert load_object("fake_pipe") is FakePipeline
    assert unregister_pipeline("fake_pipe") is True
    assert unregister_pipeline("fake_pipe") is False


def test_register_and_resolve_extension():
    register_extension("fake_ext", FakeExtension)
    assert resolve_plugin("extension:fake_ext") is FakeExtension
    assert load_object("fake_ext") is FakeExtension
    assert unregister_extension("fake_ext") is True


def test_load_object_priority_path_first():
    """完整路径优先于注册表（同名时路径胜出）。"""
    register_middleware("retry.RetryMiddleware", FakeMiddleware)
    # 'crawlo.middleware.retry.RetryMiddleware' 含点，走路径解析
    obj = load_object("crawlo.middleware.retry.RetryMiddleware")
    assert obj is not FakeMiddleware
    assert obj.__name__ == "RetryMiddleware"


def test_load_object_module_attr_format():
    assert load_object("crawlo.http.request:Request").__name__ == "Request"


def test_load_object_unknown_raises():
    with pytest.raises(ImportError):
        load_object("definitely_not_a_plugin")


def test_invalid_registration_inputs():
    with pytest.raises(ValueError):
        register_middleware("", FakeMiddleware)
    with pytest.raises(ValueError):
        register_middleware("x", None)
    with pytest.raises(ValueError):
        register_middleware("x", "not_a_class")


class _FakeSettings:
    def __init__(self, data):
        self._data = data

    def get(self, key, default=None):
        return self._data.get(key, default)

    def get_list(self, key):
        value = self._data.get(key, [])
        return value if isinstance(value, list) else [value]


class _FakeCrawler:
    def __init__(self, settings):
        self.settings = settings
        self.stats = _FakeStats()

    @property
    def spider(self):
        return "test_spider"


class _FakeStats:
    def inc_value(self, *args, **kwargs):
        pass


class _FakeSubscriber:
    def subscribe(self, *args, **kwargs):
        pass


def test_middleware_manager_loads_registered_plugin():
    """MiddlewareManager 通过 MIDDLEWARES 短名称加载注册中间件。"""
    from crawlo.middleware.middleware_manager import MiddlewareManager

    register_middleware("fake_mw", FakeMiddleware)
    settings = _FakeSettings({"MIDDLEWARES": {"fake_mw": 100}})
    crawler = _FakeCrawler(settings)
    manager = MiddlewareManager(crawler)
    assert any(isinstance(m, FakeMiddleware) for m in manager.middlewares)


def test_pipeline_manager_loads_registered_plugin():
    """PipelineManager 通过 PIPELINES 短名称加载注册管道。"""
    from crawlo.pipelines.manager import PipelineManager

    register_pipeline("fake_pipe", FakePipeline)
    settings = _FakeSettings({
        "PIPELINES": {"fake_pipe": 300},
        "DEFAULT_DEDUP_PIPELINE": None,
    })
    crawler = _FakeCrawler(settings)
    manager = PipelineManager(crawler)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import asyncio
        asyncio.run(manager._initialize())
    assert any(isinstance(p, FakePipeline) for p in manager.pipelines)


def test_extension_manager_loads_registered_plugin():
    """ExtensionManager 通过 EXTENSIONS 短名称加载注册扩展。"""
    from crawlo.extensions import ExtensionManager

    register_extension("fake_ext", FakeExtension)
    settings = _FakeSettings({"EXTENSIONS": ["fake_ext"]})
    crawler = _FakeCrawler(settings)
    crawler.subscriber = _FakeSubscriber()
    manager = ExtensionManager(crawler)
    assert any(isinstance(e, FakeExtension) for e in manager.extensions)


def test_registered_names_report():
    register_middleware("mw_a", FakeMiddleware)
    register_pipeline("pipe_a", FakePipeline)
    register_extension("ext_a", FakeExtension)
    names = get_registered_names()
    assert "mw_a" in names["middleware"]
    assert "pipe_a" in names["pipeline"]
    assert "ext_a" in names["extension"]
