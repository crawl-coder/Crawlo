"""
定时任务守护进程
"""

import asyncio
import signal
import sys
import time
from datetime import datetime
import logging
from typing import Dict, List, Any, Optional, Set
from .job import ScheduledJob
from .trigger import TimeTrigger
from crawlo.settings.setting_manager import SettingManager as Settings
from crawlo.utils.resource_manager import ResourceManager, ResourceType
from crawlo.logging import get_logger


class SchedulerDaemon:
    """定时任务守护进程"""
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.running = False
        self.jobs: List[ScheduledJob] = []
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.logger = get_logger("SchedulerDaemon")
        
        # 资源管理
        self._resource_manager = ResourceManager(name="scheduler_daemon")
        
        # 并发控制
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._running_tasks: Set[asyncio.Task] = set()
        
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
        
        # 检查Redis可用性缓存
        self._redis_available_cache = None
        self._redis_check_time = 0
        self._redis_cache_ttl = 300  # 缓存5分钟
    
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
                        kwargs=job_config.get('kwargs', {}),
                        priority=job_config.get('priority', 0),
                        max_retries=job_config.get('max_retries', 0),
                        retry_delay=job_config.get('retry_delay', 60)
                    )
                    self.jobs.append(job)
                    # 初始化任务统计
                    self._stats['job_stats'][job.spider_name] = {
                        'total': 0,
                        'successful': 0,
                        'failed': 0,
                        'last_execution': None,
                        'last_success': None,
                        'last_failure': None
                    }
                    self.logger.info(f"已加载定时任务: {job.spider_name} - {job_config.get('cron', job_config.get('interval'))}")
                except Exception as e:
                    self.logger.error(f"加载定时任务失败: {job_config}, 错误: {e}")
        
        # 检查Redis可用性缓存
        self._redis_available_cache = None
        self._redis_check_time = 0
        self._redis_cache_ttl = 300  # 缓存5分钟
    
    async def _check_redis_availability(self):
        """检查Redis是否可用，带缓存以避免频繁连接测试"""
        import time
        current_time = time.time()
        
        # 如果缓存未过期，直接返回缓存结果
        if (self._redis_available_cache is not None and 
            current_time - self._redis_check_time < self._redis_cache_ttl):
            return self._redis_available_cache
        
        # 获取Redis配置
        redis_url = self.settings.get('REDIS_URL', None)
        if not redis_url:
            # 尝试从其他Redis配置项构建URL
            redis_host = self.settings.get('REDIS_HOST', '127.0.0.1')
            redis_port = self.settings.get('REDIS_PORT', 6379)
            redis_password = self.settings.get('REDIS_PASSWORD', None)
            redis_db = self.settings.get('REDIS_DB', 0)
            
            if redis_password:
                redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
            else:
                redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
        
        self.logger.debug(f"Attempting to connect to Redis: {redis_url}")
        
        try:
            from crawlo.queue.redis_priority_queue import RedisPriorityQueue
            
            # 创建一个简单的异步函数来测试连接
            test_queue = RedisPriorityQueue(
                redis_url=redis_url,
                project_name="scheduler_test",
                timeout=5  # 5秒超时
            )
            try:
                await test_queue.connect()
                await test_queue.close()
                is_available = True
            except Exception as e:
                self.logger.debug(f"Redis connection test failed: {e}")
                is_available = False
            
            # 更新缓存
            self._redis_available_cache = is_available
            self._redis_check_time = current_time
            
            return is_available
            
        except ImportError:
            # 如果Redis模块不可用，直接返回False
            self._redis_available_cache = False
            self._redis_check_time = current_time
            return False
        except Exception as e:
            # 其他错误也返回False
            self.logger.debug(f"Redis连接测试失败: {e}")
            self._redis_available_cache = False
            self._redis_check_time = current_time
            return False
    
    async def start(self):
        """启动调度守护进程"""
        if self.running:
            self.logger.warning("调度器已在运行中")
            return
            
        self.running = True
        self.logger.info("定时任务调度器启动")
        
        # 初始化并发控制
        max_concurrent = self.settings.get_int('SCHEDULER_MAX_CONCURRENT', 3)
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self.logger.info(f"最大并发任务数: {max_concurrent}")
        
        # 设置信号处理器
        def signal_handler(signum, frame):
            self.logger.info(f"收到信号 {signum}，准备停止调度器")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 启动资源监控任务（如果启用）
        if self._resource_monitor_enabled:
            self._resource_monitor_task = asyncio.create_task(self._monitor_resources())
            self.logger.info(f"资源监控已启用，检查间隔: {self._resource_check_interval} 秒")
        else:
            self.logger.info("资源监控未启用")
        
        # 启动调度主循环
        await self._run_scheduler()
    
    async def _run_scheduler(self):
        """调度主循环"""
        check_interval = self.settings.get_int('SCHEDULER_CHECK_INTERVAL', 1)
        
        self.logger.info(f"调度器主循环启动，检查间隔: {check_interval} 秒")
        
        while self.running:
            try:
                self.logger.debug(f"检查任务，当前时间: {self._format_datetime(time.time())}")
                await self._check_and_execute_jobs()
                await asyncio.sleep(check_interval)
            except Exception as e:
                self.logger.error(f"调度器运行错误: {e}")
                await asyncio.sleep(check_interval)
        
        self.logger.info("调度器主循环停止")
    
    async def _check_and_execute_jobs(self):
        """检查并执行定时任务"""
        current_time = time.time()
        
        for job in self.jobs:
            if job.should_execute(current_time):
                # 立即标记任务为执行中，防止重复调度
                job.mark_execution_started()
                self.logger.info(f"调度任务: {job.spider_name}")
                # 使用信号量控制并发
                task = asyncio.create_task(self._execute_job_with_semaphore(job))
                self._running_tasks.add(task)
                task.add_done_callback(self._running_tasks.discard)
    
    async def _execute_job_with_semaphore(self, job: ScheduledJob):
        """使用信号量控制的任务执行"""
        async with self._semaphore:
            await self._execute_job(job)
    
    async def _execute_job(self, job: ScheduledJob):
        """执行单个任务"""
        
        # 保存原始参数，以便参考
        original_args = dict(job.args) if job.args else {}
        
        # 清空job.args并根据配置重新构建
        job.args = {}
        
        # 确定队列类型：优先使用任务参数中的QUEUE_TYPE，否则使用项目设置中的QUEUE_TYPE
        queue_type = original_args.get('QUEUE_TYPE', self.settings.get('QUEUE_TYPE', 'auto'))
        self.logger.debug(f"Queue type determined as: {queue_type} for job: {job.spider_name}")
        
        # 根据队列类型和Redis可用性决定使用何种配置
        if queue_type == 'distributed':
            # 检查Redis是否可用
            self.logger.debug(f"Checking Redis availability for distributed mode job: {job.spider_name}")
            redis_available = await self._check_redis_availability()
            self.logger.debug(f"Redis availability result for distributed mode: {redis_available} for job: {job.spider_name}")
            if redis_available:
                # Redis可用，使用Redis配置
                job.args['QUEUE_TYPE'] = 'redis'
                job.args['FILTER_CLASS'] = original_args.get('FILTER_CLASS', 'crawlo.filters.aioredis_filter.AioRedisFilter')
                job.args['DEFAULT_DEDUP_PIPELINE'] = original_args.get('DEFAULT_DEDUP_PIPELINE', 'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline')
                job.args['RUN_MODE'] = original_args.get('RUN_MODE', 'distributed')
                self.logger.info(f"Redis available, using Redis queue for job: {job.spider_name}")
            else:
                # Redis不可用，分布式模式必须退出
                error_msg = f"Distributed mode requires Redis, but Redis is unavailable for job: {job.spider_name}"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)
        elif queue_type == 'auto':
            # 检查Redis是否可用
            self.logger.debug(f"Checking Redis availability for job: {job.spider_name}")
            redis_available = await self._check_redis_availability()
            self.logger.debug(f"Redis availability result: {redis_available} for job: {job.spider_name}")
            if redis_available:
                # Redis可用，使用Redis配置
                job.args['QUEUE_TYPE'] = 'redis'
                job.args['FILTER_CLASS'] = original_args.get('FILTER_CLASS', 'crawlo.filters.aioredis_filter.AioRedisFilter')
                job.args['DEFAULT_DEDUP_PIPELINE'] = original_args.get('DEFAULT_DEDUP_PIPELINE', 'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline')
                job.args['RUN_MODE'] = original_args.get('RUN_MODE', 'distributed')
                self.logger.info(f"Redis available, using Redis queue for job: {job.spider_name}")
            else:
                # Redis不可用，使用内存配置
                job.args['QUEUE_TYPE'] = 'memory'
                job.args['FILTER_CLASS'] = original_args.get('FILTER_CLASS', 'crawlo.filters.memory_filter.MemoryFilter')
                job.args['DEFAULT_DEDUP_PIPELINE'] = original_args.get('DEFAULT_DEDUP_PIPELINE', 'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline')
                job.args['RUN_MODE'] = original_args.get('RUN_MODE', 'standalone')
                self.logger.info(f"Redis unavailable, using memory queue for job: {job.spider_name}")
        elif queue_type == 'memory':
            # 强制使用内存配置
            job.args['QUEUE_TYPE'] = 'memory'
            job.args['FILTER_CLASS'] = original_args.get('FILTER_CLASS', 'crawlo.filters.memory_filter.MemoryFilter')
            job.args['DEFAULT_DEDUP_PIPELINE'] = original_args.get('DEFAULT_DEDUP_PIPELINE', 'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline')
            job.args['RUN_MODE'] = original_args.get('RUN_MODE', 'standalone')
        else:
            # 未知队列类型，按auto模式处理
            redis_available = await self._check_redis_availability()
            if redis_available:
                # Redis可用，使用Redis配置
                job.args['QUEUE_TYPE'] = 'redis'
                job.args['FILTER_CLASS'] = original_args.get('FILTER_CLASS', 'crawlo.filters.aioredis_filter.AioRedisFilter')
                job.args['DEFAULT_DEDUP_PIPELINE'] = original_args.get('DEFAULT_DEDUP_PIPELINE', 'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline')
                job.args['RUN_MODE'] = original_args.get('RUN_MODE', 'distributed')
                self.logger.info(f"Unknown QUEUE_TYPE: {queue_type}, Redis available, using Redis queue for job: {job.spider_name}")
            else:
                # Redis不可用，使用内存配置
                job.args['QUEUE_TYPE'] = 'memory'
                job.args['FILTER_CLASS'] = original_args.get('FILTER_CLASS', 'crawlo.filters.memory_filter.MemoryFilter')
                job.args['DEFAULT_DEDUP_PIPELINE'] = original_args.get('DEFAULT_DEDUP_PIPELINE', 'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline')
                job.args['RUN_MODE'] = original_args.get('RUN_MODE', 'standalone')
                self.logger.info(f"Unknown QUEUE_TYPE: {queue_type}, Redis unavailable, using memory queue for job: {job.spider_name}")
        
        # 从原始参数中复制其他配置项，但排除已处理的配置项
        # 避免重复设置队列、过滤器、去重管道等相关配置
        excluded_keys = {
            'REDIS_HOST', 'REDIS_PORT', 'REDIS_PASSWORD', 'REDIS_DB', 'REDIS_URL',
            'FILTER_CLASS', 'DEFAULT_DEDUP_PIPELINE', 'QUEUE_TYPE', 'RUN_MODE'
        }
        for key, value in original_args.items():
            if key not in excluded_keys:
                job.args[key] = value
        
        # 添加调度器内部标识
        job.args['_INTERNAL_SCHEDULER_TASK'] = True
        
        # 从项目配置中获取监控相关设置，如果原始配置中未设置，则使用项目配置
        # 这样可以确保使用项目settings.py中的监控设置
        monitor_configs = [
            ('MEMORY_MONITOR_ENABLED', bool, False),
            ('MEMORY_MONITOR_INTERVAL', int, 30),
            ('MEMORY_WARNING_THRESHOLD', float, 80.0),
            ('MEMORY_CRITICAL_THRESHOLD', float, 90.0),
            ('MYSQL_MONITOR_ENABLED', bool, False),
            ('MYSQL_MONITOR_INTERVAL', int, 60),
            ('REDIS_MONITOR_ENABLED', bool, False),
            ('REDIS_MONITOR_INTERVAL', int, 60),
        ]
        
        for config_key, config_type, default_value in monitor_configs:
            if config_key not in job.args:
                if config_type == bool:
                    job.args[config_key] = self.settings.get_bool(config_key, default_value)
                elif config_type == int:
                    job.args[config_key] = self.settings.get_int(config_key, default_value)
                elif config_type == float:
                    job.args[config_key] = self.settings.get_float(config_key, default_value)
        
        # 但强制将Redis监控设为False，防止Redis连接池初始化
        # 在定时任务执行期间，避免重复的Redis连接池创建
        job.args['REDIS_MONITOR_ENABLED'] = False
        
        # 也要禁用内存监控，防止在调度模式下重复创建内存监控实例
        job.args['MEMORY_MONITOR_ENABLED'] = False
        
        try:
            # 更新统计信息
            self._stats['total_executions'] += 1
            self._stats['job_stats'][job.spider_name]['total'] += 1
            self._stats['job_stats'][job.spider_name]['last_execution'] = time.time()
            
            # 获取超时配置
            timeout = self.settings.get_int('SCHEDULER_JOB_TIMEOUT', 3600)
            
            try:
                # 使用 asyncio.wait_for 实现超时控制
                await asyncio.wait_for(self._run_spider_job(job), timeout=timeout)
                
                # 更新成功统计
                self._stats['successful_executions'] += 1
                self._stats['job_stats'][job.spider_name]['successful'] += 1
                self._stats['job_stats'][job.spider_name]['last_success'] = time.time()
                # 显示任务完成和下次运行信息
                self._log_task_completion(job)
                
            except asyncio.TimeoutError:
                self.logger.error(f"定时任务超时: {job.spider_name} (超时时间: {timeout}秒)")
                await self._handle_job_failure(job, "timeout")
                
                # 显示任务完成和下次运行信息
                self._log_task_completion(job)
                
            except Exception as e:
                self.logger.error(f"执行定时任务失败 {job.spider_name}: {e}")
                import traceback
                traceback.print_exc()
                await self._handle_job_failure(job, str(e))
                
                # 显示任务完成和下次运行信息
                self._log_task_completion(job)
        finally:
            # 只标记任务执行完成，不恢复原始参数，因为爬虫已经启动
            # job.args在爬虫运行期间的修改不影响调度器本身
            job.mark_execution_finished()
    
    @staticmethod
    def _format_datetime(timestamp: float) -> str:
        """格式化时间戳为字符串"""
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    
    @staticmethod
    def _format_duration(seconds: float) -> str:
        """格式化持续时间为易读字符串"""
        if seconds < 60:
            return f"{int(seconds)} 秒"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            remaining_seconds = int(seconds % 60)
            return f"{minutes} 分钟" + (f" {remaining_seconds} 秒" if remaining_seconds > 0 else "")
        elif seconds < 86400:  # 小于一天
            hours = int(seconds / 3600)
            remaining_minutes = int((seconds % 3600) / 60)
            return f"{hours} 小时" + (f" {remaining_minutes} 分钟" if remaining_minutes > 0 else "")
        else:  # 一天或以上
            days = int(seconds / 86400)
            remaining_hours = int((seconds % 86400) / 3600)
            return f"{days} 天" + (f" {remaining_hours} 小时" if remaining_hours > 0 else "")
    
    def _log_task_completion(self, job: ScheduledJob):
        """记录任务完成和下次运行信息"""
        # 重新计算下次执行时间
        next_time = job.trigger.get_next_time(time.time())
        current_time = time.time()
        time_diff = next_time - current_time
        
        # 格式化时间
        next_time_str = self._format_datetime(next_time)
        
        # 格式化时间差
        if time_diff > 0:
            time_str = self._format_duration(time_diff)
            self.logger.info(f"定时任务完成: {job.spider_name}, 下次运行时间: {next_time_str} (距离: {time_str})\n")
        else:
            self.logger.info(f"定时任务完成: {job.spider_name}, 下次运行时间: {next_time_str} (即将执行)\n")
    
    async def _run_spider_job(self, job: ScheduledJob):
        """运行爬虫任务"""
        # 使用job.args作为基础，确保包含调度模式标识
        job_args = dict(job.args)  # 这已经包含了SCHEDULER_MODE和监控配置
        
        # 确保使用爬虫的特定日志配置，而不是框架默认配置
        # 优先使用原始项目配置中的日志文件设置，避免创建额外的日志文件
        # 强制使用项目配置中的日志文件，不管job_args中是否有其他配置
        project_log_file = self.settings.get('LOG_FILE', None)
        if project_log_file:
            job_args['LOG_FILE'] = project_log_file
        elif not job_args.get('LOG_FILE'):
            # 如果项目配置中也没有设置日志文件，使用默认值
            job_args['LOG_FILE'] = 'logs/crawlo.log'
        
        # 重新配置日志系统以使用爬虫的配置（特别是LOG_FILE）
        # 这必须在创建CrawlerProcess之前完成，以确保框架初始化时使用正确的日志配置
        from crawlo.logging import configure_logging, LoggerFactory
        import logging
        
        # 在重新配置前，先清除可能存在的基础配置
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        configure_logging(job_args)  # 使用爬虫配置重新配置日志系统
        
        # 刷新所有缓存的logger以应用新配置
        LoggerFactory.clear_cache()
        
        # 导入 Crawlo 的 CrawlerProcess 来运行爬虫
        from crawlo.crawler import CrawlerProcess
        
        # 创建爬虫进程并运行指定的爬虫
        process = CrawlerProcess()
        
        # 传递任务参数给爬虫，包括调度模式信息和监控配置
        # CrawlerProcess.crawl方法需要爬虫类或名称，以及配置参数
        await process.crawl(job.spider_name, settings=job_args)
    
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
            
            # 延迟后重试
            await asyncio.sleep(job.retry_delay)
            
            # 重新执行任务
            try:
                await self._run_spider_job(job)
                # 重试成功
                self._stats['successful_executions'] += 1
                self._stats['job_stats'][job.spider_name]['successful'] += 1
                self._stats['job_stats'][job.spider_name]['last_success'] = time.time()
                job.current_retries = 0  # 重置重试计数
                self.logger.info(f"任务 {job.spider_name} 重试成功")
                
                # 显示任务完成和下次运行信息
                self._log_task_completion(job)
            except Exception as e:
                self.logger.error(f"任务 {job.spider_name} 重试失败: {e}")
                # 继续尝试重试，直到达到最大重试次数
                await self._handle_job_failure(job, str(e))
        else:
            self.logger.error(f"任务 {job.spider_name} 已达到最大重试次数 ({job.max_retries})，不再重试")
            # 任务已达到最大重试次数，标记执行完成
            job.mark_execution_finished()
            
            # 显示任务完成和下次运行信息
            self._log_task_completion(job)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self._stats.copy()
    
    async def stop(self):
        """停止调度守护进程"""
        if not self.running:
            return
            
        self.logger.info("正在停止定时任务调度器...")
        self.running = False
        
        # 停止资源监控任务
        if self._resource_monitor_task and not self._resource_monitor_task.done():
            self._resource_monitor_task.cancel()
            try:
                await self._resource_monitor_task
            except asyncio.CancelledError:
                pass
            self.logger.info("资源监控任务已停止")
        
        # 等待正在运行的任务完成
        if self._running_tasks:
            self.logger.info(f"等待 {len(self._running_tasks)} 个任务完成...")
            try:
                # 等待最多 30 秒
                await asyncio.wait_for(
                    asyncio.gather(*self._running_tasks, return_exceptions=True),
                    timeout=30.0
                )
                self.logger.info("所有任务已完成")
            except asyncio.TimeoutError:
                self.logger.warning("部分任务未能在超时时间内完成，强制停止")
                # 取消所有未完成的任务
                for task in self._running_tasks:
                    if not task.done():
                        task.cancel()
        
        # 清理资源
        try:
            await self._resource_manager.cleanup_all()
            self.logger.info("资源清理完成")
        except Exception as e:
            self.logger.error(f"资源清理失败: {e}")
        
        # 清理监控管理器中的所有监控实例
        try:
            from crawlo.utils.monitor_manager import monitor_manager
            monitor_manager.cleanup()
            self.logger.info("监控管理器清理完成")
        except Exception as e:
            self.logger.error(f"监控管理器清理失败: {e}")
        
        self.logger.info("定时任务调度器已停止")
    
    async def _monitor_resources(self):
        """监控资源使用情况"""
        try:
            import psutil
        except ImportError:
            self.logger.warning("psutil 未安装，资源监控功能受限")
            return
        
        import gc
        
        self.logger.info("资源监控任务已启动")
        
        while self.running:
            try:
                # 获取资源统计信息
                resource_stats = self._resource_manager.get_stats()
                active_resources = resource_stats.get('active_resources', 0)
                active_by_type = resource_stats.get('active_by_type', {})
                
                # 检测资源泄露
                leaks = self._resource_manager.detect_leaks(max_lifetime=self._resource_leak_threshold)
                if leaks:
                    self.logger.warning(f"检测到 {len(leaks)} 个潜在资源泄露")
                    for leak in leaks:
                        self.logger.warning(f"  - {leak.name} (生命周期: {leak.get_lifetime():.2f}s)")
                
                # 获取系统资源使用情况
                process = psutil.Process()
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                cpu_percent = process.cpu_percent(interval=1)
                
                # 打印资源使用情况
                self.logger.info(
                    f"资源监控 - 活跃资源: {active_resources}, "
                    f"内存: {memory_mb:.2f}MB, CPU: {cpu_percent:.1f}%"
                )
                
                # 打印按类型统计的资源
                if active_by_type:
                    type_str = ", ".join([f"{k}: {v}" for k, v in active_by_type.items()])
                    self.logger.info(f"资源类型分布 - {type_str}")
                
                # 执行垃圾回收
                gc.collect()
                self.logger.info(f"垃圾回收完成 - 回收对象数: {len(gc.garbage)}")
                
                # 等待下次检查
                await asyncio.sleep(self._resource_check_interval)
                
            except asyncio.CancelledError:
                self.logger.info("资源监控任务被取消")
                break
            except Exception as e:
                self.logger.error(f"资源监控错误: {e}")
                import traceback
                traceback.print_exc()
                # 等待下次检查
                await asyncio.sleep(self._resource_check_interval)


def start_scheduler(project_root: str = None):
    """启动定时任务调度器的便捷函数"""
    import os
    import sys
    import time
    from datetime import datetime
    
    # 先配置日志系统，确保SchedulerStarter日志记录器使用正确的配置
    from crawlo.project import get_settings
    from crawlo.logging import configure_logging
    
    # 尝试加载项目配置来配置日志系统
    try:
        temp_settings = get_settings()
        configure_logging(temp_settings)
    except Exception:
        # 如果无法加载配置，使用默认配置
        configure_logging()
    
    # 获取调度器日志记录器
    logger = get_logger("SchedulerStarter")
    
    # 如果指定了项目根目录，则切换到该目录
    if project_root:
        project_root = os.path.abspath(project_root)
        if os.path.isdir(project_root):
            os.chdir(project_root)
            sys.path.insert(0, project_root)
            logger.info(f"切换到项目目录: {project_root}")
        else:
            raise RuntimeError(f"项目目录不存在: {project_root}")
    
    from crawlo.project import get_settings
    
    # 使用已加载的配置
    settings = temp_settings
    
    if not settings.get_bool('SCHEDULER_ENABLED', False):
        logger.info("定时任务未启用，如需启用请在配置中设置 SCHEDULER_ENABLED = True")
        return
    
    daemon = SchedulerDaemon(settings)
    
    # 记录任务信息
    logger.info("="*80)
    logger.info("定时任务调度器")
    logger.info("="*80)
    logger.info(f"当前时间: {datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"任务数量: {len(daemon.jobs)}")
    
    if len(daemon.jobs) == 0:
        logger.info("未配置任何定时任务")
    else:
        for job in daemon.jobs:
            next_time = datetime.fromtimestamp(job.next_execution_time).strftime('%Y-%m-%d %H:%M:%S')
            time_diff = job.next_execution_time - time.time()
            if time_diff > 0:
                if time_diff < 60:
                    time_str = f"{int(time_diff)} 秒"
                elif time_diff < 3600:
                    minutes = int(time_diff / 60)
                    seconds = int(time_diff % 60)
                    time_str = f"{minutes} 分钟" + (f" {seconds} 秒" if seconds > 0 else "")
                elif time_diff < 86400:  # 小于一天
                    hours = int(time_diff / 3600)
                    minutes = int((time_diff % 3600) / 60)
                    time_str = f"{hours} 小时" + (f" {minutes} 分钟" if minutes > 0 else "")
                else:  # 一天或以上
                    days = int(time_diff / 86400)
                    hours = int((time_diff % 86400) / 3600)
                    time_str = f"{days} 天" + (f" {hours} 小时" if hours > 0 else "")
                logger.info(f"任务: {job.spider_name}")
                logger.info(f"  Cron表达式: {job.cron or job.interval}")
                logger.info(f"  下次运行时间: {next_time}")
                logger.info(f"  距离下次运行: {time_str}")
            else:
                logger.info(f"任务: {job.spider_name}")
                logger.info(f"  Cron表达式: {job.cron or job.interval}")
                logger.info(f"  下次运行时间: {next_time}")
                logger.info(f"  状态: 立即执行")
    
    logger.info("="*80)
    logger.info("调度器主循环启动，等待任务执行...")
    logger.info("="*80)
    
    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        logger.info("接收到中断信号，正在停止调度器...")
    except Exception as e:
        logger.error(f"调度器运行出错: {e}")
        import traceback
        logger.debug(f"详细错误信息:\n{traceback.format_exc()}")
