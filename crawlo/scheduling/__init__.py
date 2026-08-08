"""
定时任务模块入口（Phase 7：SchedulerDaemon 改为 PEP 562 懒加载；Phase 9.1：start_scheduler 合并到此）

改动原因：
1. Phase 7：为破真环 ``commands.job_executor → scheduling.job → scheduling/__init__ →
   scheduling.daemon.scheduler → commands.job_executor``，将 SchedulerDaemon 从模块级 eager import
   改为 ``__getattr__`` 懒加载。
2. Phase 9.1：将 ``daemon_scheduler.py`` 中的 ``start_scheduler()`` 实现合并到此处，
   消除双入口迷惑（原来 __init__ 转发 → daemon_scheduler 实现）。

API 对外行为 100% 兼容：
    from crawlo.scheduling import SchedulerDaemon  # 首次访问时懒加载
    from crawlo.scheduling import start_scheduler  # 直接在此模块内实现
    from crawlo.scheduling import get_job_registry
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .daemon import SchedulerDaemon as _SchedulerDaemonT  # noqa: F401
    from .registry import JobRegistry  # noqa: F401

from .registry import get_job_registry


def start_scheduler(project_root: str = None):
    """启动定时任务调度器

    Args:
        project_root: 项目根目录路径
    """
    import os
    import sys
    import time
    import asyncio
    from datetime import datetime

    # 先配置日志系统
    from crawlo.project import get_settings
    from crawlo.logging import configure_logging, get_logger
    from crawlo.scheduling.daemon import SchedulerDaemon
    from crawlo.utils.parsing import format_datetime, format_duration

    try:
        temp_settings = get_settings()
        configure_logging(temp_settings)
    except Exception:
        configure_logging()

    logger = get_logger("SchedulerStarter")

    # 如果指定了项目根目录
    if project_root:
        project_root = os.path.abspath(project_root)
        if os.path.isdir(project_root):
            os.chdir(project_root)
            sys.path.insert(0, project_root)
            logger.info(f"切换到项目目录: {project_root}")
        else:
            raise RuntimeError(f"项目目录不存在: {project_root}")

    # get_settings 已在上面导入
    settings = get_settings()

    if not settings.get_bool('SCHEDULER_ENABLED', False):
        logger.info("定时任务未启用，如需启用请在配置中设置 SCHEDULER_ENABLED = True")
        return

    # 初始化调度器（加载任务配置）
    daemon = SchedulerDaemon(settings)

    # 打印启动概览
    logger.info(f"调度器启动 - 时间: {datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')}, 任务数: {len(daemon.jobs)}")

    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        logger.info("接收到中断信号，正在停止调度器...")
    except Exception as e:
        logger.error(f"调度器运行出错: {e}")
        import traceback
        logger.debug(f"详细错误信息:\n{traceback.format_exc()}")


def __getattr__(name):
    """PEP 562 懒加载：SchedulerDaemon 只在首次访问时导入。

    Phase 7 破环说明：commands.job_executor 在模块顶层导入 ScheduledJob（scheduling.job），
    若 scheduling.__init__ 同步 import SchedulerDaemon → scheduling.daemon.scheduler →
    commands.job_executor，就会产生真环（commands.job_executor 尚未初始化完毕）。
    改为懒加载后，import scheduling.job 仅执行 scheduling.job 自身代码，不触发 SchedulerDaemon。
    """
    if name == "SchedulerDaemon":
        from .daemon import SchedulerDaemon
        return SchedulerDaemon
    raise AttributeError(f"module 'crawlo.scheduling' has no attribute '{name}'")


__all__ = ["SchedulerDaemon", "start_scheduler", "get_job_registry"]
