"""
定时任务注册表
"""

from typing import Dict, List, Optional
from .job import ScheduledJob


class JobRegistry:
    """定时任务注册表"""
    
    def __init__(self):
        self._jobs: Dict[str, ScheduledJob] = {}
    
    def register_job(self, job: ScheduledJob):
        """注册定时任务"""
        self._jobs[job.spider_name] = job
    
    def unregister_job(self, spider_name: str):
        """注销定时任务"""
        if spider_name in self._jobs:
            del self._jobs[spider_name]
    
    def get_job(self, spider_name: str) -> Optional[ScheduledJob]:
        """获取定时任务"""
        return self._jobs.get(spider_name)
    
    def get_all_jobs(self) -> List[ScheduledJob]:
        """获取所有定时任务"""
        return list(self._jobs.values())
    
    def clear(self):
        """清空注册表"""
        self._jobs.clear()


# 全局注册表实例
_job_registry = JobRegistry()


def get_job_registry() -> JobRegistry:
    """获取全局定时任务注册表"""
    return _job_registry