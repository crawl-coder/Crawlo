"""P3-4 Engine 组合可配置化测试"""

from unittest.mock import Mock

from crawlo.core.engine import Engine
from tests.fixtures.engine_components import DummyDispatcher, DummyDistributed


def _make_crawler():
    crawler = Mock()
    crawler.settings = Mock()
    crawler.settings.get = Mock(side_effect=lambda key, default=None: default)
    crawler.settings.get_int = Mock(side_effect=lambda key, default=0: default)
    crawler.settings.get_float = Mock(side_effect=lambda key, default=0.0: default)
    crawler.settings.get_bool = Mock(side_effect=lambda key, default=False: default)
    return crawler


def test_inject_instances():
    crawler = _make_crawler()
    dispatcher = DummyDispatcher(crawler)
    distributed = DummyDistributed(crawler)
    engine = Engine(crawler, dispatcher=dispatcher, distributed=distributed)
    assert engine._dispatcher is dispatcher
    assert engine._distributed is distributed


def test_inject_classes():
    crawler = _make_crawler()
    engine = Engine(
        crawler,
        dispatcher_cls=DummyDispatcher,
        distributed_cls=DummyDistributed,
    )
    assert isinstance(engine._dispatcher, DummyDispatcher)
    assert isinstance(engine._distributed, DummyDistributed)


def test_settings_class_path():
    crawler = _make_crawler()
    crawler.settings.get = Mock(
        side_effect=lambda key, default=None: {
            'ENGINE_DISPATCHER_CLASS': 'tests.fixtures.engine_components.DummyDispatcher',
            'ENGINE_DISTRIBUTED_CLASS': 'tests.fixtures.engine_components.DummyDistributed',
        }.get(key, default)
    )
    engine = Engine(crawler)
    assert isinstance(engine._dispatcher, DummyDispatcher)
    assert isinstance(engine._distributed, DummyDistributed)


def test_default_composition():
    crawler = _make_crawler()
    engine = Engine(crawler)
    from crawlo.core.engine_dispatch import RequestDispatcher
    from crawlo.core.engine_distributed import DistributedCoordinator
    assert isinstance(engine._dispatcher, RequestDispatcher)
    assert isinstance(engine._distributed, DistributedCoordinator)
