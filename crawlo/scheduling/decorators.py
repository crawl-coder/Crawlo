"""
定时任务装饰器
"""

from typing import Callable, Optional, Dict, Any
from functools import wraps
from .job import ScheduledJob


# 全局任务注册表
_scheduled_jobs = []


def scheduled_job(cron: Optional[str] = None, interval: Optional[Dict[str, int]] = None, **job_kwargs):
    """
    定时任务装饰器
    
    Args:
        cron: Cron表达式，如 '0 */2 * * *' 表示每2小时执行
        interval: 时间间隔，如 {'hours': 2} 表示每2小时执行
        **job_kwargs: 其他任务参数
    """
    def decorator(func: Callable) -> Callable:
        # 创建任务配置
        job_config = {
            'cron': cron,
            'interval': interval,
            **job_kwargs
        }
        
        # 将任务添加到全局注册表
        _scheduled_jobs.append({
            'func': func,
            'config': job_config
        })
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def get_scheduled_jobs():
    """获取所有已注册的定时任务"""
    return _scheduled_jobs


def clear_scheduled_jobs():
    """清空定时任务注册表"""
    global _scheduled_jobs
    _scheduled_jobs = []