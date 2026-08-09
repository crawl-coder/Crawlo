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


def _resolve_registry_context():
    """优先从容器拿 RegistryContext，否则 fallback ctx.registries。"""
    try:
        from crawlo.core.application import default_container
        from crawlo.core.application import RegistryContext
        if default_container.is_registered(RegistryContext):
            return default_container.resolve(RegistryContext)
    except Exception:  # noqa: S110
        pass
    from crawlo.core.application import get_global_context
    return get_global_context().registries


def get_job_registry() -> JobRegistry:
    """获取全局定时任务注册表（DI 容器优先 + RegistryContext fallback）。

    与 ComponentRegistry / InitializerRegistry 保持统一策略：容器已注册则直接 resolve，
    否则 fallback 到 RegistryContext 懒创建并 ``register_instance`` 补充注册。
    """
    try:
        from crawlo.core.application import default_container
        if default_container.is_registered(JobRegistry):
            return default_container.resolve(JobRegistry)
    except Exception:  # pragma: no cover
        pass

    rctx = _resolve_registry_context()
    if rctx.job_registry is None:
        inst = JobRegistry()
        rctx.job_registry = inst
        try:
            from crawlo.core.application import default_container as _c
            _c.register_instance(JobRegistry, inst)
        except Exception:  # pragma: no cover
            pass
    return rctx.job_registry
