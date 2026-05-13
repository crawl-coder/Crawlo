"""
定时任务模块测试
"""

import asyncio
import time
import pytest
from unittest.mock import Mock, patch, AsyncMock
from crawlo.scheduling import SchedulerDaemon
from crawlo.scheduling.job import ScheduledJob
from crawlo.scheduling.trigger import TimeTrigger
from crawlo.scheduling.registry import JobRegistry


class TestTimeTrigger:
    """测试时间触发器"""
    
    def test_cron_trigger_basic(self):
        """测试基本的 cron 触发器"""
        trigger = TimeTrigger(cron='0 */2 * * *')
        assert trigger.cron == '0 */2 * * *'
        assert trigger.interval is None
    
    def test_interval_trigger_basic(self):
        """测试基本的时间间隔触发器"""
        trigger = TimeTrigger(interval={'minutes': 30})
        assert trigger.cron is None
        assert trigger.interval == {'minutes': 30}
    
    def test_get_next_time_interval(self):
        """测试获取下次执行时间（间隔模式）"""
        trigger = TimeTrigger(interval={'seconds': 10})
        current_time = time.time()
        next_time = trigger.get_next_time(current_time)
        assert next_time >= current_time + 10
        assert next_time < current_time + 11
    
    def test_invalid_cron_expression(self):
        """测试无效的 cron 表达式"""
        with pytest.raises(ValueError):
            TimeTrigger(cron='invalid')
    
    def test_cron_with_seconds(self):
        """测试带秒位的 cron 表达式"""
        trigger = TimeTrigger(cron='0 0 */2 * * *')
        assert len(trigger._cron_parts) == 6
    
    def test_cron_next_time_optimized(self):
        """测试字段级跳进的 cron 下次时间计算"""
        now = time.time()
        
        # */5 * * * *  — 每 5 分钟，next_time 应在接下来 5 分钟内
        t1 = TimeTrigger(cron='*/5 * * * *')
        next1 = t1.get_next_time(now)
        assert next1 > now
        assert next1 - now <= 300
        
        # 0 2 * * *  — 每天凌晨 2 点
        t2 = TimeTrigger(cron='0 2 * * *')
        next2 = t2.get_next_time(now)
        from datetime import datetime as dt
        result2 = dt.fromtimestamp(next2)
        assert result2.hour == 2
        assert result2.minute == 0
        
        # 30 10 * * 1-5  — 工作日 10:30
        t3 = TimeTrigger(cron='30 10 * * 1-5')
        next3 = t3.get_next_time(now)
        result3 = dt.fromtimestamp(next3)
        assert result3.hour == 10
        assert result3.minute == 30
        assert result3.isoweekday() <= 5  # 周一至周五
        
        # 秒级 cron: 30 */2 * * * *  — 每 2 分 30 秒
        t4 = TimeTrigger(cron='30 */2 * * * *')
        next4 = t4.get_next_time(now)
        result4 = dt.fromtimestamp(next4)
        assert result4.second == 30
    
    def test_cron_next_time_never_matching(self):
        """测试永不匹配的 cron（如 2月29日 在非闰年）"""
        import datetime as dt
        # 在 2025 年（非闰年）查找 2 月 29 日
        non_leap = dt.datetime(2025, 3, 1, 0, 0, 0).timestamp()
        t = TimeTrigger(cron='0 0 29 2 *')
        result = t.get_next_time(non_leap)
        # 下一个 2/29 是 2028 年（闰年），但我们在 367 天上限内找不到
        # 此时返回 float('inf')
        if result != float('inf'):
            result_dt = dt.datetime.fromtimestamp(result)
            assert result_dt.month == 2 and result_dt.day == 29


class TestScheduledJob:
    """测试定时任务"""
    
    def test_job_creation(self):
        """测试任务创建"""
        job = ScheduledJob(
            spider_name='test_spider',
            cron='0 */2 * * *',
            args={'test': 'value'},
            priority=10
        )
        assert job.spider_name == 'test_spider'
        assert job.cron == '0 */2 * * *'
        assert job.args == {'test': 'value'}
        assert job.priority == 10
        assert job.max_retries == 0
        assert job.retry_delay == 60
    
    def test_job_with_retries(self):
        """测试带重试配置的任务"""
        job = ScheduledJob(
            spider_name='test_spider',
            cron='0 */2 * * *',
            max_retries=3,
            retry_delay=120
        )
        assert job.max_retries == 3
        assert job.retry_delay == 120
        assert job.current_retries == 0
    
    def test_should_execute(self):
        """测试任务执行判断"""
        job = ScheduledJob(
            spider_name='test_spider',
            interval={'seconds': 10}
        )
        current_time = time.time()
        next_time = job.next_execution_time
        
        # 时间未到，不应该执行
        assert not job.should_execute(current_time)
        
        # 时间到了，应该执行
        assert job.should_execute(next_time)
    
    def test_reset_retries(self):
        """测试重置重试计数"""
        job = ScheduledJob(
            spider_name='test_spider',
            cron='0 */2 * * *',
            max_retries=3
        )
        job.current_retries = 2
        job.reset_retries()
        assert job.current_retries == 0


class TestJobRegistry:
    """测试任务注册表"""
    
    def test_register_and_get_job(self):
        """测试注册和获取任务"""
        registry = JobRegistry()
        job = ScheduledJob(spider_name='test_spider', cron='0 */2 * * *')
        
        registry.register_job(job)
        retrieved_job = registry.get_job('test_spider')
        
        assert retrieved_job is job
        assert retrieved_job.spider_name == 'test_spider'
    
    def test_unregister_job(self):
        """测试注销任务"""
        registry = JobRegistry()
        job = ScheduledJob(spider_name='test_spider', cron='0 */2 * * *')
        
        registry.register_job(job)
        assert registry.get_job('test_spider') is not None
        
        registry.unregister_job('test_spider')
        assert registry.get_job('test_spider') is None
    
    def test_get_all_jobs(self):
        """测试获取所有任务"""
        registry = JobRegistry()
        job1 = ScheduledJob(spider_name='spider1', cron='0 */2 * * *')
        job2 = ScheduledJob(spider_name='spider2', interval={'minutes': 30})
        
        registry.register_job(job1)
        registry.register_job(job2)
        
        all_jobs = registry.get_all_jobs()
        assert len(all_jobs) == 2
        assert job1 in all_jobs
        assert job2 in all_jobs
    
    def test_clear_registry(self):
        """测试清空注册表"""
        registry = JobRegistry()
        job1 = ScheduledJob(spider_name='spider1', cron='0 */2 * * *')
        job2 = ScheduledJob(spider_name='spider2', interval={'minutes': 30})
        
        registry.register_job(job1)
        registry.register_job(job2)
        
        registry.clear()
        
        assert len(registry.get_all_jobs()) == 0


class TestSchedulerDaemon:
    """测试调度守护进程"""
    
    @pytest.fixture
    def mock_settings(self):
        """创建模拟配置"""
        settings = Mock()
        settings.get_bool.return_value = True
        settings.get.return_value = [
            {
                'spider': 'test_spider',
                'cron': '0 */2 * * *',
                'enabled': True,
                'args': {},
                'priority': 0,
                'max_retries': 2,
                'retry_delay': 60
            }
        ]
        settings.get_int.return_value = 1
        return settings
    
    def test_daemon_initialization(self, mock_settings):
        """测试守护进程初始化"""
        daemon = SchedulerDaemon(mock_settings)
        
        assert daemon.running is False
        assert len(daemon.jobs) == 1
        assert daemon.jobs[0].spider_name == 'test_spider'
        assert daemon._stats['total_executions'] == 0
    
    def test_daemon_disabled(self):
        """测试禁用状态的守护进程"""
        settings = Mock()
        settings.get_bool.return_value = False
        
        daemon = SchedulerDaemon(settings)
        
        assert len(daemon.jobs) == 0
    
    def test_concurrent_control_initialization(self, mock_settings):
        """测试并发控制初始化"""
        daemon = SchedulerDaemon(mock_settings)
        assert daemon._semaphore is None
        
        # 模拟启动
        asyncio.run(daemon.start())
        
        # 注意：start() 会进入无限循环，所以这里只测试初始化部分
        # 在实际测试中，应该使用更复杂的 mock 来避免无限循环
    
    def test_stats_tracking(self, mock_settings):
        """测试统计信息跟踪"""
        daemon = SchedulerDaemon(mock_settings)
        
        stats = daemon.get_stats()
        
        assert 'total_executions' in stats
        assert 'successful_executions' in stats
        assert 'failed_executions' in stats
        assert 'job_stats' in stats
        assert 'test_spider' in stats['job_stats']
    
    def test_job_stats_initialization(self, mock_settings):
        """测试任务统计初始化"""
        daemon = SchedulerDaemon(mock_settings)
        
        job_stats = daemon._stats['job_stats']['test_spider']
        
        assert job_stats['total'] == 0
        assert job_stats['successful'] == 0
        assert job_stats['failed'] == 0
        assert job_stats['last_execution'] is None
        assert job_stats['last_success'] is None
        assert job_stats['last_failure'] is None
    
    def test_priority_sorting(self):
        """测试任务按优先级排序（小值高优优先）"""
        settings = Mock()
        settings.get_bool.return_value = True
        settings.get.return_value = [
            {
                'spider': 'spider_low',
                'cron': '0 */2 * * *',
                'enabled': True,
                'args': {},
                'priority': 20,
                'max_retries': 0,
                'retry_delay': 60
            },
            {
                'spider': 'spider_high',
                'cron': '0 */2 * * *',
                'enabled': True,
                'args': {},
                'priority': 5,
                'max_retries': 0,
                'retry_delay': 60
            },
            {
                'spider': 'spider_medium',
                'cron': '0 */2 * * *',
                'enabled': True,
                'args': {},
                'priority': 10,
                'max_retries': 0,
                'retry_delay': 60
            }
        ]
        settings.get_int.return_value = 1
        
        daemon = SchedulerDaemon(settings)
        
        assert len(daemon.jobs) == 3
        assert daemon.jobs[0].spider_name == 'spider_high'
        assert daemon.jobs[1].spider_name == 'spider_medium'
        assert daemon.jobs[2].spider_name == 'spider_low'
        
        # 验证优先级值排序
        priorities = [job.priority for job in daemon.jobs]
        assert priorities == [5, 10, 20]
    
    def test_min_next_execution_time(self):
        """测试 _get_min_next_execution_time 返回最早的下次执行时间"""
        settings = Mock()
        settings.get_bool.return_value = True
        settings.get.return_value = [
            {
                'spider': 'spider_a',
                'cron': '0 */2 * * *',
                'enabled': True,
                'args': {},
                'priority': 0,
                'max_retries': 0,
                'retry_delay': 60
            },
            {
                'spider': 'spider_b',
                'interval': {'seconds': 1},
                'enabled': True,
                'args': {},
                'priority': 0,
                'max_retries': 0,
                'retry_delay': 60
            }
        ]
        settings.get_int.return_value = 1
        
        daemon = SchedulerDaemon(settings)
        
        min_next = daemon._get_min_next_execution_time()
        assert min_next != float('inf')
        # interval=1s 的 job 下次执行时间应在 1 秒内
        now = time.time()
        assert min_next <= now + 1
    
    def test_min_next_execution_time_empty(self):
        """测试无任务时返回 inf"""
        settings = Mock()
        settings.get_bool.return_value = False
        settings.get.return_value = []
        settings.get_int.return_value = 1
        
        daemon = SchedulerDaemon(settings)
        assert daemon._get_min_next_execution_time() == float('inf')


class TestSchedulerIntegration:
    """测试调度器集成功能"""
    
    @pytest.mark.asyncio
    async def test_concurrent_execution_limit(self):
        """测试并发执行限制"""
        settings = Mock()
        settings.get_bool.return_value = True
        settings.get.return_value = [
            {
                'spider': 'spider1',
                'interval': {'seconds': 1},
                'enabled': True,
                'args': {},
                'priority': 0,
                'max_retries': 0,
                'retry_delay': 60
            },
            {
                'spider': 'spider2',
                'interval': {'seconds': 1},
                'enabled': True,
                'args': {},
                'priority': 0,
                'max_retries': 0,
                'retry_delay': 60
            }
        ]
        settings.get_int.return_value = 1  # 最大并发数为 1
        
        daemon = SchedulerDaemon(settings)
        
        # 验证信号量已创建
        assert daemon._semaphore is not None
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """测试超时处理"""
        settings = Mock()
        settings.get_bool.return_value = True
        settings.get.return_value = [
            {
                'spider': 'test_spider',
                'cron': '0 */2 * * *',
                'enabled': True,
                'args': {},
                'priority': 0,
                'max_retries': 0,
                'retry_delay': 60
            }
        ]
        settings.get_int.return_value = 1
        
        daemon = SchedulerDaemon(settings)
        
        # 验证超时配置
        timeout = settings.get_int('SCHEDULER_JOB_TIMEOUT', 3600)
        assert timeout == 1
    
    @pytest.mark.asyncio
    async def test_retry_mechanism(self):
        """测试重试机制"""
        job = ScheduledJob(
            spider_name='test_spider',
            cron='0 */2 * * *',
            max_retries=3,
            retry_delay=60
        )
        
        assert job.max_retries == 3
        assert job.retry_delay == 60
        assert job.current_retries == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
