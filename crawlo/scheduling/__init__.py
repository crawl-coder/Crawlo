"""
定时任务模块入口
"""

from .daemon import SchedulerDaemon
from .registry import get_job_registry


def start_scheduler(project_root: str = None):
    """启动定时任务调度器
    
    Args:
        project_root: 项目根目录路径
    """
    from .daemon_scheduler import start_scheduler as _start_scheduler
    return _start_scheduler(project_root)


__all__ = ['SchedulerDaemon', 'start_scheduler', 'get_job_registry']