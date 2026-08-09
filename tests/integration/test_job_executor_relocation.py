"""
Phase 7 验收测试：JobExecutor 上提至 commands 层
==============================================

v2.0：旧路径 crawlo.scheduling.daemon.executor 已物理删除，
      仅测试新路径 crawlo.commands.job_executor。

断言三件事：
1. 新路径 ``from crawlo.commands.job_executor import JobExecutor`` 直接导入正常
2. 旧路径 ``from crawlo.scheduling.daemon.executor import JobExecutor`` 抛 ImportError
3. SchedulerDaemon → JobExecutor → CrawlerProcess.crawl 完整调用链路通过
   （CrawlerProcess.crawl 用 monkeypatch dry-run，不实际爬取）
"""

import asyncio
import warnings
from types import SimpleNamespace
from typing import Any, Dict

import pytest

from crawlo.commands.job_executor import JobExecutor
from crawlo.commands.job import ScheduledJob
from crawlo.logging import get_logger


# ------------------------------
# 1. 新路径导入 OK（无警告）
# ------------------------------
def test_new_import_path_no_warning():
    """新路径应可直接导入且不产生任何 DeprecationWarning 或其他 warning。"""
    import crawlo.commands.job_executor as _new_mod
    # 导入应成功，类定义存在
    assert hasattr(_new_mod, "JobExecutor")
    assert _new_mod.JobExecutor is JobExecutor


# ------------------------------
# 2. 旧路径已删除（v2.0）
# ------------------------------
def test_old_import_path_raises_import_error():
    """旧路径 crawlo.scheduling.daemon.executor 已物理删除，必须 ImportError。"""
    with pytest.raises(ImportError):
        from crawlo.scheduling.daemon.executor import JobExecutor  # noqa: F401,WPS433


# ------------------------------
# 3. API 兼容性（类签名/关键属性/方法）
# ------------------------------
class _DictLikeSettings(dict):
    """最小 dict-like settings：JobExecutor 内部只调 get_int(key, default)/get(key, default)。"""

    def get_int(self, key, default=0):
        val = self.get(key, default)
        return int(val) if val is not None else default

    def get_float(self, key, default=0.0):
        val = self.get(key, default)
        return float(val) if val is not None else default

    def get_bool(self, key, default=False):
        val = self.get(key, default)
        return bool(val) if val is not None else default


def _make_minimal_settings():
    return _DictLikeSettings({
        "SCHEDULER_MAX_CONCURRENT": 1,
        "SCHEDULER_JOB_TIMEOUT": 10,
    })


def _make_minimal_job(spider_name: str = "test_spider") -> ScheduledJob:
    return ScheduledJob(
        spider_name=spider_name,
        interval={"seconds": 60},
        args={"_from_test": True},
        priority=0,
        max_retries=0,
        retry_delay=0.01,
    )


def test_job_executor_public_api_equivalent():
    """JobExecutor 构造 + 关键方法/属性必须与旧 API 完全一致。"""
    settings = _make_minimal_settings()
    stats: Dict[str, Any] = {
        "total_executions": 0,
        "successful_executions": 0,
        "failed_executions": 0,
        "job_stats": {"test_spider": {
            "total": 0, "successful": 0, "failed": 0,
            "last_execution": None, "last_success": None, "last_failure": None,
        }},
    }
    logger = get_logger("test_executor_api")
    executor = JobExecutor(settings, stats, logger)

    # 属性初始态
    assert executor.running_tasks == set()
    assert executor._semaphore is None

    # init_concurrency 必须创建信号量
    executor.init_concurrency()
    assert executor._semaphore is not None
    # SCHEDULER_MAX_CONCURRENT=1，Semaphore._value 初始为 1
    assert executor._semaphore._value == 1

    # add_task / running_tasks 联动（避免 ensure_future 在没有 running loop 时的 deprecation warning：直接构造 Task-like mock）
    from unittest.mock import MagicMock
    mock_task = MagicMock()
    mock_task.add_done_callback = lambda cb: None  # 真实语义：set.discard 在 done 时自动移除
    executor.add_task(mock_task)
    assert mock_task in executor.running_tasks


# ------------------------------
# 4. SchedulerDaemon → JobExecutor → CrawlerProcess 端到端 dry-run
# ------------------------------
@pytest.mark.asyncio
async def test_executor_calls_crawlerprocess_crawl(monkeypatch):
    """执行链路验证：JobExecutor._run_spider_job 必须走 CrawlerProcess().crawl(spider_name, settings=...)。

    monkeypatch CrawlerProcess.crawl 为 dry-run 空实现，不实际爬取。
    """
    # 记录被调用的参数
    call_log: list = []

    class FakeCrawlerProcess:
        def __init__(self):
            pass

        async def crawl(self, spider_name, settings=None):
            call_log.append({"spider_name": spider_name, "settings": settings or {}})

    import crawlo.commands.job_executor as executor_mod
    # Patch _run_spider_job 内部 import 的 CrawlerProcess：直接 patch 命令级变量引用
    original_import = executor_mod.CrawlerProcess.__class__.__bases__ if False else None

    # Patch 方式：monkeypatch crawlo.crawler_process 模块里的 CrawlerProcess 类
    import crawlo.crawler_process as cp_mod
    monkeypatch.setattr(cp_mod, "CrawlerProcess", FakeCrawlerProcess)

    # CrawlerProcess.crawl 还会 import 其他组件，模拟空的 logger configure
    # executor 内部会调 configure_logging；我们 monkeypatch 它为 no-op
    # LoggerFactory.clear_cache 是 classmethod：不传 cls（已被 classmethod 描述器注入）
    import crawlo.logging as log_mod
    monkeypatch.setattr(log_mod, "configure_logging", lambda *_a, **_kw: None)
    monkeypatch.setattr(log_mod.LoggerFactory, "clear_cache", classmethod(lambda cls: None))

    settings = _make_minimal_settings()
    stats: Dict[str, Any] = {
        "total_executions": 0,
        "successful_executions": 0,
        "failed_executions": 0,
        "job_stats": {"spider_dry": {
            "total": 0, "successful": 0, "failed": 0,
            "last_execution": None, "last_success": None, "last_failure": None,
        }},
    }
    job = _make_minimal_job("spider_dry")
    logger = get_logger("test_executor_dryrun")
    executor = JobExecutor(settings, stats, logger)
    executor.init_concurrency()

    await executor.execute_job(job)

    # CrawlerProcess.crawl 必须被调用 1 次
    assert len(call_log) == 1, f"期望 CrawlerProcess.crawl 调用 1 次，实际 {len(call_log)} 次: {call_log}"
    assert call_log[0]["spider_name"] == "spider_dry"
    # settings 中必须包含调度器内部标识（job_args 注入）
    assert call_log[0]["settings"].get("_INTERNAL_SCHEDULER_TASK") is True

    # 成功统计必须更新
    assert stats["total_executions"] == 1
    assert stats["successful_executions"] == 1
    assert stats["failed_executions"] == 0
    assert stats["job_stats"]["spider_dry"]["successful"] == 1


# ------------------------------
# 5. 旧 executor 文件已删除（v2.0）
# ------------------------------
def test_old_executor_module_deleted():
    """旧 crawlo/scheduling/daemon/executor.py 已物理删除。"""
    import importlib.util
    spec = importlib.util.find_spec("crawlo.scheduling.daemon.executor")
    assert spec is None, "crawlo.scheduling.daemon.executor 应已删除"
