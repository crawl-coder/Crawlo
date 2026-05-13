"""
调度器核心模块
"""

import asyncio
import signal
import time
from datetime import datetime
from typing import Any, Dict, Optional

from crawlo.logging import get_logger
from crawlo.scheduling.job import ScheduledJob
from crawlo.scheduling.registry import JobRegistry
from crawlo.scheduling.daemon.executor import JobExecutor
from crawlo.scheduling.daemon.cleanup import ResourceCleanup
from crawlo.utils.time_format import format_duration


class SchedulerDaemon:
    """定时任务守护进程"""
    
    def __init__(self, settings):
        from crawlo.settings.setting_manager import SettingManager as Settings
        from crawlo.utils.resource_manager import ResourceManager, ResourceType
        
        self.settings = settings
        self.running = False
        self._registry = JobRegistry()
        self._sorted_jobs: list = []
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.logger = get_logger("SchedulerDaemon")
        
        # 资源管理
        self._resource_manager = ResourceManager(name="scheduler_daemon")
        
        # 任务执行器
        self._executor: Optional[JobExecutor] = None
        self._cleanup = ResourceCleanup(self.logger)
        
        # 监控统计
        self._stats: Dict[str, Any] = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'job_stats': {}
        }
        
        # 资源监控
        self._resource_monitor_task: Optional[asyncio.Task] = None
        self._resource_check_interval = self.settings.get_int('SCHEDULER_RESOURCE_CHECK_INTERVAL', 300)
        self._resource_monitor_enabled = self.settings.get_bool('SCHEDULER_RESOURCE_MONITOR_ENABLED', True)
        self._resource_leak_threshold = self.settings.get_int('SCHEDULER_RESOURCE_LEAK_THRESHOLD', 3600)
        
        # 从配置加载定时任务
        self._load_jobs_from_settings()
    
    def _load_jobs_from_settings(self):
        """从配置加载定时任务"""
        if not self.settings.get_bool('SCHEDULER_ENABLED', False):
            return
            
        scheduler_jobs = self.settings.get('SCHEDULER_JOBS', [])
        for job_config in scheduler_jobs:
            if job_config.get('enabled', True):
                try:
                    job = ScheduledJob(
                        spider_name=job_config['spider'],
                        cron=job_config.get('cron'),
                        interval=job_config.get('interval'),
                        args=job_config.get('args', {}),
                        priority=job_config.get('priority', 0),
                        max_retries=job_config.get('max_retries', 0),
                        retry_delay=job_config.get('retry_delay', 60)
                    )
                    self._registry.register_job(job)
                    self._stats['job_stats'][job.spider_name] = {
                        'total': 0,
                        'successful': 0,
                        'failed': 0,
                        'last_execution': None,
                        'last_success': None,
                        'last_failure': None
                    }
                except Exception as e:
                    self.logger.error(f"加载定时任务失败: {job_config}, 错误: {e}")
        
        # 按优先级预排序，供 _check_and_execute_jobs 和 jobs 属性使用
        self._sorted_jobs = sorted(self._registry.get_all_jobs(), key=lambda j: j.priority)
        
        # 打印任务汇总信息
        if self._sorted_jobs:
            self.logger.info(f"共加载 {len(self._sorted_jobs)} 个定时任务:")
            for job in self._sorted_jobs:
                cron_expr = job.cron or f"每 {job.interval}s"
                
                # 解析下次执行时间
                try:
                    next_time_str = datetime.fromtimestamp(job.next_execution_time).strftime('%Y-%m-%d %H:%M:%S')
                except (OSError, OverflowError, ValueError):
                    next_time_str = "N/A"
                
                time_diff = job.next_execution_time - time.time()
                if time_diff > 0:
                    remaining = format_duration(time_diff)
                    self.logger.info(f"  {job.spider_name} [{cron_expr}] 下次: {next_time_str} (剩余: {remaining})")
                else:
                    self.logger.info(f"  {job.spider_name} [{cron_expr}] 下次: {next_time_str} (即将执行)")
    
    async def start(self):
        """启动调度守护进程"""
        if self.running:
            self.logger.warning("调度器已在运行中")
            return
            
        self.running = True
        
        # 初始化执行器
        self._executor = JobExecutor(self.settings, self._stats, self.logger)
        self._executor.init_concurrency()
        
        # 设置信号处理器
        def signal_handler(signum, frame):
            self.logger.info(f"收到信号 {signum}，准备停止调度器")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 启动资源监控任务（如果启用）
        if self._resource_monitor_enabled:
            self._resource_monitor_task = asyncio.create_task(self._monitor_resources())
            self.logger.info(f"资源监控已启用 (间隔: {self._resource_check_interval}s)")
        else:
            self.logger.info("资源监控未启用")
        
        # 启动调度主循环
        await self._run_scheduler()
    
    async def _run_scheduler(self):
        """调度主循环 — 按最近任务时间智能 sleep，避免忙轮询"""
        check_interval = self.settings.get_int('SCHEDULER_CHECK_INTERVAL', 1)
        
        self.logger.debug(f"调度器主循环启动，最大检查间隔: {check_interval} 秒")
        
        while self.running:
            try:
                now = time.time()
                min_next = self._get_min_next_execution_time()
                if min_next != float('inf'):
                    sleep_sec = min_next - now
                else:
                    sleep_sec = check_interval
                sleep_sec = max(0.1, min(sleep_sec, check_interval))
                await asyncio.sleep(sleep_sec)
                await self._check_and_execute_jobs()
            except Exception as e:
                self.logger.error(f"调度器运行错误: {e}")
                await asyncio.sleep(check_interval)
        
        self.logger.info("调度器主循环停止")
    
    def _get_min_next_execution_time(self):
        """获取所有任务中最近的下次执行时间"""
        if not self._sorted_jobs:
            return float('inf')
        return min(job.get_next_execution_time() for job in self._sorted_jobs)
    
    async def _check_and_execute_jobs(self):
        """检查并执行定时任务"""
        current_time = time.time()
        
        for job in self._sorted_jobs:
            if job.should_execute(current_time):
                job.mark_execution_started()
                self.logger.info(f"调度任务: {job.spider_name}")
                
                # 使用执行器执行任务
                task = asyncio.create_task(self._executor.execute_with_semaphore(job))
                self._executor.add_task(task)
    
    async def _monitor_resources(self):
        """监控资源使用情况"""
        try:
            import psutil
        except ImportError:
            self.logger.warning("psutil 未安装，资源监控功能受限")
            return
        
        import gc
        
        while self.running:
            try:
                resource_stats = self._resource_manager.get_stats()
                active_resources = resource_stats.get('active_resources', 0)
                active_by_type = resource_stats.get('active_by_type', {})
                
                # 检测资源泄露
                leaks = self._resource_manager.detect_leaks(max_lifetime=self._resource_leak_threshold)
                if leaks:
                    self.logger.warning(f"检测到 {len(leaks)} 个潜在资源泄露")
                    for leak in leaks[:5]:
                        self.logger.warning(f"  - {leak.name} (生命周期: {leak.get_lifetime():.2f}s)")
                    if len(leaks) > 5:
                        self.logger.warning(f"  ... 还有 {len(leaks) - 5} 个潜在资源泄露未显示")
                
                # 获取系统资源使用情况
                process = psutil.Process()
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                cpu_percent = process.cpu_percent(interval=1)
                
                self.logger.debug(
                    f"资源监控 - 活跃资源: {active_resources}, "
                    f"内存: {memory_mb:.2f}MB, CPU: {cpu_percent:.1f}%"
                )
                
                if active_by_type:
                    type_str = ", ".join([f"{k}: {v}" for k, v in active_by_type.items()])
                    self.logger.debug(f"资源类型分布 - {type_str}")
                
                # 执行垃圾回收
                collected = gc.collect()
                self.logger.debug(f"垃圾回收完成 - 回收对象数: {collected}")
                
                await asyncio.sleep(self._resource_check_interval)
                
            except asyncio.CancelledError:
                self.logger.info("资源监控任务被取消")
                break
            except Exception as e:
                self.logger.error(f"资源监控错误: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(self._resource_check_interval)
    
    async def stop(self):
        """停止调度守护进程"""
        if not self.running:
            return
            
        self.logger.info("正在停止定时任务调度器...")
        self.running = False
        
        # 执行资源清理
        await self._cleanup.cleanup_all(
            self._resource_manager,
            self._resource_monitor_task,
            self._executor.running_tasks if self._executor else set()
        )
        
        self.logger.info("定时任务调度器已停止")
    
    @property
    def jobs(self):
        """获取所有定时任务（按优先级排序）"""
        return self._sorted_jobs
    
    @property
    def running_tasks(self):
        """获取运行中的任务集合"""
        return self._executor.running_tasks if self._executor else set()
    
    @property
    def _semaphore(self):
        """获取信号量（兼容性属性）"""
        return self._executor._semaphore if self._executor else None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self._stats.copy()
