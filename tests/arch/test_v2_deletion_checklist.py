#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
v2.0 Breaking Change 删除清单守护测试
=====================================

目的
----
对 FRAMEWORK_REFACTOR_PLAN.md 中 13 条 v2.0 删除清单逐条做可执行断言，
确保所有 v2.0 标记删除的 facade / 同步 API / 兼容层已被物理移除。

每条测试对应删除清单中的一行，验收断言来自计划文档。

执行时机
--------
- v2.0 分支：所有测试应 pass
- develop 分支（v1.x）：这些测试会失败，因为 facade 仍存在
"""

import pytest


# ============================================================================
# 第 1 条（Phase 3.1 更新）：CrawlerProcess 已合并入 crawlo.crawler
# ============================================================================
class TestCrawlerProcessInCrawlerModule:
    """Phase 3.1 后：CrawlerProcess 类直接定义在 crawlo.crawler（不再通过 __getattr__ 反向导出）"""

    def test_crawler_process_defined_directly_in_crawler_module(self):
        """CrawlerProcess 是 crawlo.crawler 的真实成员（dir() 可见，不是 __getattr__ 转发）"""
        import crawlo.crawler
        assert 'CrawlerProcess' in dir(crawlo.crawler), (
            "Phase 3.1 后 CrawlerProcess 应直接定义在 crawlo.crawler，"
            "不再需要通过 crawlo.crawler_process 间接访问"
        )
        # 直接属性访问应成功
        assert crawlo.crawler.CrawlerProcess is not None

    def test_crawler_process_same_object_through_stub(self):
        """兼容存根 crawlo.crawler_process.CrawlerProcess 与 crawlo.crawler.CrawlerProcess 是同一个类"""
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', DeprecationWarning)
            from crawlo.crawler_process import CrawlerProcess as FromStub
        from crawlo.crawler import CrawlerProcess as FromCrawler
        # sys.modules 存根机制应返回同一对象
        assert FromStub is FromCrawler

    def test_crawler_process_importable_from_top_level(self):
        """from crawlo import CrawlerProcess 正常导入（PEP 562 顶层转发）"""
        from crawlo import CrawlerProcess
        assert CrawlerProcess is not None

    def test_crawlerprocess_class_is_real_implementation(self):
        """CrawlerProcess 应具备核心公开方法（crawl/get_metrics/get_spider_names 等）"""
        from crawlo.crawler import CrawlerProcess
        expected = ('crawl', 'get_metrics', 'get_spider_class', 'get_spider_names', 'is_spider_registered')
        for method in expected:
            assert hasattr(CrawlerProcess, method), (
                f"CrawlerProcess 应具备 {method}() 方法，合并操作不应丢失 API"
            )


# ============================================================================
# 第 2 条：scheduling.daemon.executor re-export 已物理删除
# ============================================================================
class TestSchedulingDaemonExecutorRemoved:
    """v2.0: crawlo.scheduling.daemon.executor 已物理删除"""

    def test_old_path_raises_module_not_found(self):
        """旧路径 import 抛 ModuleNotFoundError"""
        import importlib
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module('crawlo.scheduling.daemon.executor')


# ============================================================================
# 第 3 条：commands.job_executor 是实现文件（非 re-export facade）
# ============================================================================
class TestJobExecutorInCommands:
    """v2.0: JobExecutor 在 commands.job_executor 是实现文件"""

    def test_job_executor_importable_from_commands(self):
        """from crawlo.commands.job_executor import JobExecutor 正常导入"""
        from crawlo.commands.job_executor import JobExecutor
        assert JobExecutor is not None


# ============================================================================
# 第 4 条：core/scheduler.py re-export 已物理删除
# ============================================================================
class TestCoreSchedulerFacadeRemoved:
    """v2.0: crawlo.core.scheduler 已物理删除"""

    def test_old_path_raises_module_not_found(self):
        """旧路径 import 抛 ModuleNotFoundError"""
        import importlib
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module('crawlo.core.scheduler')


# ============================================================================
# 第 5/6/7 条：async_initialize_framework / bootstrap_framework / get_bootstrap_manager 已删除
# ============================================================================
class TestDeprecatedInitFunctionsRemoved:
    """v2.0: 三个废弃初始化函数已从 core/__init__.py 物理删除"""

    def test_async_initialize_framework_removed(self):
        """from crawlo.core import async_initialize_framework 抛 AttributeError"""
        import crawlo.core
        with pytest.raises(AttributeError):
            crawlo.core.async_initialize_framework

    def test_bootstrap_framework_removed(self):
        """from crawlo.core import bootstrap_framework 抛 AttributeError"""
        import crawlo.core
        with pytest.raises(AttributeError):
            crawlo.core.bootstrap_framework

    def test_get_bootstrap_manager_removed(self):
        """from crawlo.core import get_bootstrap_manager 抛 AttributeError"""
        import crawlo.core
        with pytest.raises(AttributeError):
            crawlo.core.get_bootstrap_manager

    def test_initialize_framework_still_available(self):
        """initialize_framework 仍然可用（非废弃）"""
        import crawlo.core
        # 通过 __getattr__ 延迟导入
        assert hasattr(crawlo.core, 'initialize_framework') or 'initialize_framework' in dir(crawlo.core)


# ============================================================================
# 第 8 条：ApplicationContext @property 委托已删除
# ============================================================================
class TestApplicationContextPropertyDelegatesRemoved:
    """v2.0: ApplicationContext 的 @property 委托方法已物理删除"""

    def test_no_property_delegates_for_channels(self):
        """ctx.dingtalk_channel 抛 AttributeError，必须用 ctx.notifications.dingtalk_channel"""
        from crawlo.core.application import ApplicationContext
        # 检查类定义中不存在 @property 委托
        import inspect
        for name, attr in vars(ApplicationContext).items():
            if isinstance(attr, property) and name.endswith('_channel'):
                pytest.fail(f"ApplicationContext.{name} 仍存在 @property 委托，应已删除")


# ============================================================================
# 第 9 条：ApplicationContext.rebind_to_container() 已删除
# ============================================================================
class TestRebindToContainerRemoved:
    """v2.0: ApplicationContext.rebind_to_container 已物理删除"""

    def test_rebind_to_container_removed(self):
        """ctx.rebind_to_container 抛 AttributeError"""
        from crawlo.core.application import ApplicationContext
        assert not hasattr(ApplicationContext, 'rebind_to_container')


# ============================================================================
# 第 10 条：utils 旧路径 re-export 已物理删除
# ============================================================================
class TestUtilsOldPathsRemoved:
    """v2.0: utils 下旧路径 facade 已物理删除"""

    @pytest.mark.parametrize("old_path", [
        'crawlo.utils.config_manager',
        'crawlo.utils.page_utils',
        'crawlo.utils.time_format',
        'crawlo.utils.encoding_detector',
    ])
    def test_old_utils_path_raises_module_not_found(self, old_path):
        """旧路径 import 抛 ModuleNotFoundError"""
        import importlib
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(old_path)


# ============================================================================
# 第 11 条：exceptions.py / interfaces.py 顶层 re-export 已物理删除
# ============================================================================
class TestTopLevelFacadesRemoved:
    """v2.0: crawlo.exceptions / crawlo.interfaces 顶层 facade 已物理删除"""

    @pytest.mark.parametrize("old_path", [
        'crawlo.exceptions',
        'crawlo.interfaces',
    ])
    def test_old_top_level_path_raises_module_not_found(self, old_path):
        """旧路径 import 抛 ModuleNotFoundError"""
        import importlib
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(old_path)


# ============================================================================
# 第 12 条：Scheduler.idle() / Processor.idle() / QueueManager.empty() sync 版本已删除
# ============================================================================
class TestSyncIdleEmptyRemoved:
    """v2.0: 同步 idle()/empty() 方法已物理删除"""

    def test_scheduler_idle_removed(self):
        """Scheduler.idle 不存在"""
        from crawlo.core.scheduling.task_scheduler import Scheduler
        assert not hasattr(Scheduler, 'idle')

    def test_processor_idle_removed(self):
        """Processor.idle 不存在"""
        from crawlo.core.processor import Processor
        assert not hasattr(Processor, 'idle')

    def test_queue_manager_empty_removed(self):
        """QueueManager.empty 不存在"""
        from crawlo.queue.queue_manager import QueueManager
        assert not hasattr(QueueManager, 'empty')

    def test_async_versions_exist(self):
        """异步版本仍然存在"""
        from crawlo.core.scheduling.task_scheduler import Scheduler
        from crawlo.core.processor import Processor
        from crawlo.queue.queue_manager import QueueManager
        assert hasattr(Scheduler, 'async_idle')
        assert hasattr(Processor, 'idle_async')
        assert hasattr(QueueManager, 'async_empty')


# ============================================================================
# 第 13 条：Scheduler.__len__ 已删除
# ============================================================================
class TestSchedulerLenRemoved:
    """v2.0: Scheduler.__len__ 已物理删除"""

    def test_scheduler_len_removed(self):
        """Scheduler.__len__ 不存在"""
        from crawlo.core.scheduling.task_scheduler import Scheduler
        assert not hasattr(Scheduler, '__len__')

    def test_async_size_exists(self):
        """async_size() 仍然存在"""
        from crawlo.core.scheduling.task_scheduler import Scheduler
        assert hasattr(Scheduler, 'async_size')


# ============================================================================
# 额外：get_framework_initializer fallback 已删除
# ============================================================================
class TestFrameworkInitializerFallbackRemoved:
    """v2.0: get_framework_initializer 不再回退到 SingletonMeta"""

    def test_fallback_raises_runtime_error(self):
        """ctx 未就绪时抛 RuntimeError，不回退到全局单例"""
        from crawlo.core import get_framework_initializer
        # 确保 ctx 未就绪时会抛 RuntimeError（而非 DeprecationWarning + 回退）
        import inspect
        source = inspect.getsource(get_framework_initializer)
        assert 'DeprecationWarning' not in source
        assert 'RuntimeError' in source


# ============================================================================
# 第 14 条：helpers / network / db / shell / backpressure 顶层兼容包已物理删除
# ============================================================================
class TestTopLevelCompatPackagesRemoved:
    """v2.0: Phase 3 清理 — 5 个顶层兼容包目录 + 子模块 sys.modules 存根已物理删除"""

    @pytest.mark.parametrize("path", [
        'crawlo.helpers',
        'crawlo.helpers.time_utils',
        'crawlo.helpers.text_cleaner',
        'crawlo.helpers.file_downloader',
        'crawlo.helpers.mysql_exists_checker',
        'crawlo.helpers.adaptive_selector',
        'crawlo.network',
        'crawlo.network.request',
        'crawlo.network.response',
        'crawlo.network.response_adaptive',
        'crawlo.network.exceptions',
        'crawlo.db',
        'crawlo.shell',
        'crawlo.backpressure',
        'crawlo.backpressure.strategies',
        'crawlo.backpressure.interfaces',
        'crawlo.backpressure.metrics_collector',
        'crawlo.backpressure.monitor',
        'crawlo.backpressure.intelligent_calculator',
    ])
    def test_old_compat_packages_unimportable(self, path):
        """5 个顶层兼容包 + 子模块 import 抛 ModuleNotFoundError"""
        import importlib
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(path)

    def test_equivalent_new_paths_still_work(self):
        """新路径（utils / http / queue.backpressure）仍然可用"""
        from crawlo.utils.time_utils import now, time_diff  # noqa: F401
        from crawlo.utils.text.cleaner import TextCleaner  # noqa: F401
        from crawlo.utils.db.mysql_exists_checker import MySQLExistsChecker  # noqa: F401
        from crawlo.utils.adaptive_selector import ElementFingerprint  # noqa: F401
        from crawlo.http.request import Request  # noqa: F401
        from crawlo.http.response import Response  # noqa: F401
        from crawlo.http.exceptions import DownloadError  # noqa: F401
        from crawlo.queue.backpressure import BackpressureController  # noqa: F401
        from crawlo.queue.backpressure.strategies import QueueSizeStrategy  # noqa: F401


# ============================================================================
# 第 15 条：core/ 下 13 个扁平兼容存根文件已物理删除
# ============================================================================
class TestCoreFlatCompatStubsRemoved:
    """v2.0: Phase 3 清理 — core/ 下 13 个 sys.modules 兼容存根已物理删除"""

    @pytest.mark.parametrize("path", [
        'crawlo.core.config_base',
        'crawlo.core.config_compat',
        'crawlo.core.config_factories',
        'crawlo.core.config_validator',
        'crawlo.core.engine_generation',
        'crawlo.core.engine_helpers',
        'crawlo.core.engine_cluster',
        'crawlo.core.error_types',
        'crawlo.core.exceptions',
        'crawlo.core.failure',
        'crawlo.core.task_manager',
        'crawlo.core.task_scheduler',
        # core/engine.py 存根文件已删除
        # Phase 3.2：engine 子包已合并为单文件 core/engine.py（含 Engine + Mixin + helpers）
    ])
    def test_old_core_flat_stubs_unimportable(self, path):
        """旧 core 扁平兼容 stub import 抛 ModuleNotFoundError"""
        import importlib
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(path)

    def test_equivalent_new_subpackages_still_work(self):
        """新路径（core/config、core/scheduling、core/engine 单文件、core.errors）仍然可用"""
        from crawlo.core.config.base import RunMode  # noqa: F401
        from crawlo.core.config.compat import validate_config  # noqa: F401
        from crawlo.core.scheduling.task_manager import TaskManager  # noqa: F401
        from crawlo.core.scheduling.task_scheduler import Scheduler  # noqa: F401
        from crawlo.core.engine import Engine  # noqa: F401
        from crawlo.core.errors import (  # noqa: F401
            CrawloException, Failure, ErrorClassifier, NotConfiguredError, PipelineInitError
        )


# ============================================================================
# 第 16 条：queue/ 下 4 个扁平后端兼容存根已物理删除
# ============================================================================
class TestQueueFlatBackendStubsRemoved:
    """v2.0: Phase 3 清理 — queue/ 下 4 个扁平 sys.modules 存根已物理删除"""

    @pytest.mark.parametrize("path", [
        'crawlo.queue.memory_queue',
        'crawlo.queue.disk_queue',
        'crawlo.queue.redis_priority_queue',
        'crawlo.queue.redis_stream_queue',
    ])
    def test_old_queue_flat_stubs_unimportable(self, path):
        """旧 queue 扁平后端 stub import 抛 ModuleNotFoundError"""
        import importlib
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(path)

    def test_equivalent_new_backends_still_work(self):
        """新路径 queue/backends/ 仍然可用"""
        from crawlo.queue.backends.memory import MemoryQueue, SpiderPriorityQueue  # noqa: F401
        from crawlo.queue.backends.disk import DiskQueue, DiskQueueConfig  # noqa: F401
        from crawlo.queue.backends.redis_priority import RedisPriorityQueue  # noqa: F401
        from crawlo.queue.backends.redis_stream import RedisStreamQueue  # noqa: F401
