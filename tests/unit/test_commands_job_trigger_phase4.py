#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Phase 4: Commands Job / Trigger 单元测试

覆盖：
1. ScheduledJob 基本属性（spider_name/cron/interval/args/priority...）
2. ScheduledJob → dict 往返相等（构造→属性提取→再构造，属性一致）
   （实际类无 to_dict/from_dict，采用语义等价方案）
3. ScheduledJob.should_execute(current_time)：到时间 True / 未到 False
4. TimeTrigger interval 模式：get_next_time(last_ts=100) == 110（10s 间隔）
5. TimeTrigger cron 模式：'* * * * *' 构造不抛异常
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch

from crawlo.commands.job import ScheduledJob
from crawlo.commands.trigger import TimeTrigger


# ========================================================================
# 辅助函数：手动 dict 往返（语义等价 to_dict/from_dict）
# ========================================================================

def _job_to_dict(job: ScheduledJob) -> dict:
    """语义等价 to_dict：提取可构造属性"""
    return {
        'spider_name': job.spider_name,
        'cron': job.cron,
        'interval': job.interval,
        'args': job.args,
        'priority': job.priority,
        'max_retries': job.max_retries,
        'retry_delay': job.retry_delay,
        'timeout': job.timeout,
    }


def _job_from_dict(d: dict) -> ScheduledJob:
    """语义等价 from_dict：从 dict 再构造"""
    return ScheduledJob(**d)


# ========================================================================
# Tests 1-3: ScheduledJob
# ========================================================================

class TestScheduledJobPhase4:
    """ScheduledJob 3 个核心测试"""

    def test_scheduled_job_basic_attributes(self):
        """
        1. 基本属性：spider_name/cron/interval/args/priority/max_retries/retry_delay/timeout
        对应用户需求：ScheduledJob(id='j1', func='f', trigger=None) 基本属性
        """
        job = ScheduledJob(
            spider_name='my_spider',
            cron='0 * * * *',
            interval=None,
            args={'foo': 'bar'},
            priority=5,
            max_retries=3,
            retry_delay=120,
            timeout=3600,
        )
        assert job.spider_name == 'my_spider'
        assert job.cron == '0 * * * *'
        assert job.interval is None
        assert job.args == {'foo': 'bar'}
        assert job.priority == 5
        assert job.max_retries == 3
        assert job.retry_delay == 120
        assert job.timeout == 3600
        # 运行时状态初始化
        assert job.current_retries == 0
        assert job.last_execution_time == 0
        assert job.is_executing is False
        # trigger 自动被构造
        assert job.trigger is not None
        assert isinstance(job.trigger, TimeTrigger)

    def test_scheduled_job_dict_roundtrip_equal(self):
        """
        2. to_dict() / from_dict() 往返相等
        （实际类无此方法 → 采用提取属性→再构造→比较核心字段）
        """
        original = ScheduledJob(
            spider_name='spider_x',
            cron='*/15 * * * *',
            interval={'minutes': 30},
            args={'depth': 3},
            priority=2,
            max_retries=5,
            retry_delay=90,
            timeout=1800,
        )
        # 提取字段
        d = _job_to_dict(original)
        # 重建
        rebuilt = _job_from_dict(d)
        # 可构造字段一致
        assert rebuilt.spider_name == original.spider_name
        assert rebuilt.cron == original.cron
        assert rebuilt.interval == original.interval
        assert rebuilt.args == original.args
        assert rebuilt.priority == original.priority
        assert rebuilt.max_retries == original.max_retries
        assert rebuilt.retry_delay == original.retry_delay
        assert rebuilt.timeout == original.timeout

    def test_scheduled_job_should_execute_time_check(self):
        """
        3. should_execute：到达 next_execution_time → True；
           未到达 → False；
           is_executing=True → 即使到时间也 False（防重入）
        对应用户需求：next_run_at=1000, should_run(now=2000) True / (now=500) False
        """
        # 构造时不依赖真实 time.time()：用 patch 固定基准
        fixed_time = 100.0
        with patch('crawlo.commands.job.time.time', return_value=fixed_time):
            # 用 interval 模式，保证 get_next_time 可预测
            job = ScheduledJob(
                spider_name='s1',
                interval={'seconds': 1000},  # get_next_time = fixed_time + 1000 = 1100
            )
        # 手动设置 next_execution_time = 1000（对应用户需求 next_run_at=1000）
        job.next_execution_time = 1000

        # now=2000 到点 → True
        assert job.should_execute(current_time=2000) is True

        # now=500 还没到 → False
        assert job.should_execute(current_time=500) is False

        # now=2000 但是正在执行 → False
        job.is_executing = True
        assert job.should_execute(current_time=2000) is False


# ========================================================================
# Tests 4-5: TimeTrigger
# ========================================================================

class TestTimeTriggerPhase4:
    """TimeTrigger 2 个核心测试"""

    def test_time_trigger_interval_next_fire(self):
        """
        4. TimeTrigger interval seconds=10：get_next_time(last_ts=100) == 110
        对应用户需求：next_fire_time(last_ts=100) == 110
        """
        trigger = TimeTrigger(interval={'seconds': 10})
        next_time = trigger.get_next_time(current_time=100)
        assert next_time == 110

        # 其他单位组合也测一下保证逻辑无误
        trigger2 = TimeTrigger(interval={'minutes': 1})
        assert trigger2.get_next_time(0) == 60

        trigger3 = TimeTrigger(interval={'hours': 1, 'seconds': 30})
        assert trigger3.get_next_time(0) == 3600 + 30

    def test_time_trigger_cron_construct_no_error(self):
        """
        5. TimeTrigger(cron='* * * * *')：不抛异常构造即可
        """
        # 5 位标准 cron（标准格式）
        t1 = TimeTrigger(cron='* * * * *')
        assert t1.cron == '* * * * *'
        assert t1._cron_parts is not None  # 被解析为 6 位（前补秒位 0）
        assert len(t1._cron_parts) == 6

        # 6 位扩展 cron
        t2 = TimeTrigger(cron='30 * * * * *')
        assert len(t2._cron_parts) == 6

        # 一些常见 cron 表达式
        t3 = TimeTrigger(cron='0 */6 * * *')
        assert t3.cron == '0 */6 * * *'

        # 非法格式应该抛 ValueError（反向验证构造函数确实解析）
        with pytest.raises(ValueError):
            TimeTrigger(cron='invalid-cron-string')

        # 空 cron + interval 都不设置 → 也能构造
        t_inactive = TimeTrigger()
        assert t_inactive.cron is None
        assert t_inactive.interval is None
