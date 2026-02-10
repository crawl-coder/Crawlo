"""
定时任务定义
"""

import time
from typing import Dict, Any, Optional
from .trigger import TimeTrigger


class ScheduledJob:
    """定时任务定义"""
    
    def __init__(
        self, 
        spider_name: str, 
        cron: Optional[str] = None, 
        interval: Optional[Dict[str, int]] = None,
        args: Optional[Dict[str, Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        priority: int = 0,
        max_retries: int = 0,
        retry_delay: int = 60
    ):
        self.spider_name = spider_name
        self.cron = cron
        self.interval = interval
        self.args = args or {}
        self.kwargs = kwargs or {}
        self.priority = priority
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.current_retries = 0
        self.trigger = TimeTrigger(cron=cron, interval=interval)
        self.last_execution_time = 0
        self.next_execution_time = self.trigger.get_next_time(time.time())
        self.is_executing = False  # 跟踪任务是否正在执行
    
    def should_execute(self, current_time: float) -> bool:
        """判断是否应该执行任务"""
        # 检查是否到达下次执行时间且当前没有在执行
        if current_time >= self.next_execution_time and not self.is_executing:
            return True
        return False
    
    def mark_execution_started(self):
        """标记任务开始执行"""
        self.is_executing = True
        self.last_execution_time = time.time()
        # 计算下一次执行时间
        self.next_execution_time = self.trigger.get_next_time(self.last_execution_time)
    
    def mark_execution_finished(self):
        """标记任务执行完成"""
        self.is_executing = False
        self.current_retries = 0  # 重置重试计数
    
    def get_next_execution_time(self) -> float:
        """获取下次执行时间"""
        return self.next_execution_time
    
    def reset_retries(self):
        """重置重试计数"""
        self.current_retries = 0
    
    def __repr__(self):
        return f"ScheduledJob(spider={self.spider_name}, cron={self.cron}, interval={self.interval})"