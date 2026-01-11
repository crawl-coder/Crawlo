# -*- coding: UTF-8 -*-
"""
定时任务配置示例
================
展示各种定时任务配置方式
"""

# =================================== 基础配置 ===================================

# 启用定时任务
SCHEDULER_ENABLED = True

# =================================== 任务配置示例 ===================================

# 示例1: 每2分钟执行一次
SCHEDULER_JOBS_EXAMPLE_1 = [
    {
        'spider': 'of_week',
        'cron': '*/2 * * * *',
        'enabled': True,
        'args': {},
        'priority': 10
    }
]

# 示例2: 每5分钟执行一次
SCHEDULER_JOBS_EXAMPLE_2 = [
    {
        'spider': 'of_week',
        'cron': '*/5 * * * *',
        'enabled': True,
        'args': {},
        'priority': 10
    }
]

# 示例3: 每小时执行一次
SCHEDULER_JOBS_EXAMPLE_3 = [
    {
        'spider': 'of_week',
        'cron': '0 * * * *',
        'enabled': True,
        'args': {},
        'priority': 10
    }
]

# 示例4: 每天凌晨执行一次
SCHEDULER_JOBS_EXAMPLE_4 = [
    {
        'spider': 'of_week',
        'cron': '0 0 * * *',
        'enabled': True,
        'args': {},
        'priority': 10
    }
]

# 示例5: 每周一凌晨执行一次
SCHEDULER_JOBS_EXAMPLE_5 = [
    {
        'spider': 'of_week',
        'cron': '0 0 * * 1',
        'enabled': True,
        'args': {},
        'priority': 10
    }
]

# 示例6: 每月1号凌晨执行一次
SCHEDULER_JOBS_EXAMPLE_6 = [
    {
        'spider': 'of_week',
        'cron': '0 0 1 * *',
        'enabled': True,
        'args': {},
        'priority': 10
    }
]

# 示例7: 工作日9点到18点每小时执行一次
SCHEDULER_JOBS_EXAMPLE_7 = [
    {
        'spider': 'of_week',
        'cron': '0 9-18 * * 1-5',
        'enabled': True,
        'args': {},
        'priority': 10
    }
]

# 示例8: 每天凌晨和中午12点执行一次
SCHEDULER_JOBS_EXAMPLE_8 = [
    {
        'spider': 'of_week',
        'cron': '0 0,12 * * *',
        'enabled': True,
        'args': {},
        'priority': 10
    }
]

# 示例9: 多任务配置
SCHEDULER_JOBS_EXAMPLE_9 = [
    {
        'spider': 'of_week',
        'cron': '*/2 * * * *',
        'enabled': True,
        'args': {},
        'priority': 10
    },
    {
        'spider': 'news_spider',
        'cron': '0 */4 * * *',
        'enabled': True,
        'args': {'category': 'tech'},
        'priority': 5
    },
    {
        'spider': 'product_spider',
        'cron': '0 0 * * *',
        'enabled': True,
        'args': {'max_pages': 100},
        'priority': 1
    }
]

# 示例10: 传递参数给爬虫
SCHEDULER_JOBS_EXAMPLE_10 = [
    {
        'spider': 'my_spider',
        'cron': '0 0 * * *',
        'enabled': True,
        'args': {
            'start_url': 'https://example.com',
            'max_pages': 100,
            'category': 'news'
        },
        'priority': 10
    }
]

# =================================== 使用说明 ===================================

"""
使用方法：

1. 选择一个示例配置，复制到 SCHEDULER_JOBS 变量中
2. 根据需要修改参数
3. 启动调度器：python run.py --schedule

例如，使用示例1（每2分钟执行一次）：

SCHEDULER_JOBS = [
    {
        'spider': 'of_week',
        'cron': '*/2 * * * *',
        'enabled': True,
        'args': {},
        'priority': 10
    }
]
"""

# =================================== 实际配置 ===================================

# 取消注释下面的配置来使用
# SCHEDULER_JOBS = SCHEDULER_JOBS_EXAMPLE_1

# =================================== 高级配置 ===================================

# 调度器检查间隔（秒）
SCHEDULER_CHECK_INTERVAL = 1

# 最大并发任务数
SCHEDULER_MAX_CONCURRENT = 3

# 单个任务超时时间（秒）
SCHEDULER_JOB_TIMEOUT = 3600
