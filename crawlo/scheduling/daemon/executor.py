"""
任务执行器
负责执行定时任务的核心逻辑
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional, Set

from crawlo.scheduling.job import ScheduledJob
from crawlo.logging import get_logger
from crawlo.utils.time_format import format_datetime, format_duration


class JobExecutor:
    """任务执行器"""
    
    def __init__(self, settings, stats: Dict[str, Any], logger: logging.Logger):
        self.settings = settings
        self._stats = stats
        self.logger = logger
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._running_tasks: Set[asyncio.Task] = set()
    
    async def execute_job(self, job: ScheduledJob):
        """执行单个任务
        
        Args:
            job: 定时任务对象
        """
        try:
            # 更新统计信息
            self._stats['total_executions'] += 1
            self._stats['job_stats'][job.spider_name]['total'] += 1
            self._stats['job_stats'][job.spider_name]['last_execution'] = time.time()
            
            # 获取超时配置
            timeout = self.settings.get_int('SCHEDULER_JOB_TIMEOUT', 3600)
            
            try:
                # 使用 asyncio.timeout 实现超时控制
                # 将 spider 协程包装为 Task，超时后显式 cancel 防止后台并发运行
                job_task = asyncio.ensure_future(self._run_spider_job(job))
                try:
                    async with asyncio.timeout(timeout):
                        await job_task
                except asyncio.TimeoutError:
                    # 超时后必须显式取消任务，避免后续调度周期并发执行 spider
                    job_task.cancel()
                    try:
                        await job_task
                    except asyncio.CancelledError:
                        pass
                    raise  # 重新抛给外层 except 处理
                
                # 更新成功统计
                self._stats['successful_executions'] += 1
                self._stats['job_stats'][job.spider_name]['successful'] += 1
                self._stats['job_stats'][job.spider_name]['last_success'] = time.time()
                
                # 记录任务完成和下次运行信息
                self._log_task_completion(job)
                
            except asyncio.TimeoutError:
                self.logger.error(f"定时任务超时: {job.spider_name} (超时时间: {timeout}秒)")
                await self._handle_job_failure(job, "timeout")
                # _handle_job_failure 内部已在各分支调用 _log_task_completion
                
            except Exception as e:
                self.logger.error(f"执行定时任务失败 {job.spider_name}: {e}")
                import traceback
                traceback.print_exc()
                await self._handle_job_failure(job, str(e))
                # _handle_job_failure 内部已在各分支调用 _log_task_completion
        finally:
            job.mark_execution_finished()
    
    async def _run_spider_job(self, job: ScheduledJob):
        """运行爬虫任务"""
        job_args = dict(job.args)
        
        # 添加调度器内部标识，用于区分定时任务触发的爬虫执行
        job_args['_INTERNAL_SCHEDULER_TASK'] = True
        
        # 确保使用爬虫的特定日志配置
        project_log_file = self.settings.get('LOG_FILE', None)
        if project_log_file:
            job_args['LOG_FILE'] = project_log_file
        elif not job_args.get('LOG_FILE'):
            job_args['LOG_FILE'] = 'logs/crawlo.log'
        
        # 重新配置日志系统
        from crawlo.logging import configure_logging, LoggerFactory
        # logging 已在顶部导入
        
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        configure_logging(job_args)
        LoggerFactory.clear_cache()
        
        # 导入 CrawlerProcess
        from crawlo.crawler import CrawlerProcess
        
        process = CrawlerProcess()
        
        try:
            await process.crawl(job.spider_name, settings=job_args)
        finally:
            # 连接池将在调度器完全停止时统一关闭
            pass
    
    async def _handle_job_failure(self, job: ScheduledJob, error: str):
        """处理任务失败"""
        # 更新失败统计
        self._stats['failed_executions'] += 1
        self._stats['job_stats'][job.spider_name]['failed'] += 1
        self._stats['job_stats'][job.spider_name]['last_failure'] = time.time()
        
        # 检查是否需要重试
        if job.current_retries < job.max_retries:
            job.current_retries += 1
            self.logger.info(f"任务 {job.spider_name} 将在 {job.retry_delay} 秒后重试 (第 {job.current_retries}/{job.max_retries} 次)")
            
            await asyncio.sleep(job.retry_delay)
            
            try:
                await self._run_spider_job(job)
                self._stats['successful_executions'] += 1
                self._stats['job_stats'][job.spider_name]['successful'] += 1
                self._stats['job_stats'][job.spider_name]['last_success'] = time.time()
                job.current_retries = 0
                self.logger.info(f"任务 {job.spider_name} 重试成功")
                self._log_task_completion(job)
            except Exception as e:
                self.logger.error(f"任务 {job.spider_name} 重试失败: {e}")
                await self._handle_job_failure(job, str(e))
        else:
            self.logger.error(f"任务 {job.spider_name} 已达到最大重试次数 ({job.max_retries})，不再重试")
            job.mark_execution_finished()
            self._log_task_completion(job)
    
    def _log_task_completion(self, job: ScheduledJob):
        """记录任务完成和下次运行信息"""
        next_time = job.trigger.get_next_time(time.time())
        current_time = time.time()
        time_diff = next_time - current_time
        
        next_time_str = format_datetime(next_time)
        
        if time_diff > 0:
            time_str = format_duration(time_diff)
            self.logger.info(f"定时任务完成: {job.spider_name}, 下次运行时间: {next_time_str} (距离: {time_str})\n")
        else:
            self.logger.info(f"定时任务完成: {job.spider_name}, 下次运行时间: {next_time_str} (即将执行)\n")
    
    def init_concurrency(self):
        """初始化并发控制"""
        max_concurrent = self.settings.get_int('SCHEDULER_MAX_CONCURRENT', 3)
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self.logger.info(f"最大并发爬虫数: {max_concurrent}")
    
    async def execute_with_semaphore(self, job: ScheduledJob):
        """使用信号量控制的任务执行"""
        async with self._semaphore:
            await self.execute_job(job)
    
    @property
    def running_tasks(self) -> Set[asyncio.Task]:
        return self._running_tasks
    
    def add_task(self, task: asyncio.Task):
        """添加运行中的任务"""
        self._running_tasks.add(task)
        task.add_done_callback(self._running_tasks.discard)
