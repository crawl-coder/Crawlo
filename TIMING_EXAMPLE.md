# Crawlo 定时调度功能使用案例

## 1. 基本配置案例

### 1.1 项目配置文件 (settings.py)

```python
# -*- coding: UTF-8 -*-
"""
定时任务项目配置示例
"""
from crawlo.config import CrawloConfig

# 创建基础配置
config = CrawloConfig.auto(
    project_name='financial_crawler',
    concurrency=5,
    download_delay=1.0
)

# 将配置转换为全局变量
locals().update(config.to_dict())

# =================================== 定时任务配置 ===================================
# 启用调度器
SCHEDULER_ENABLED = True

# 调度器配置
SCHEDULER_CHECK_INTERVAL = 30      # 检查间隔（秒）
SCHEDULER_MAX_CONCURRENT = 2       # 最大并发任务数
SCHEDULER_JOB_TIMEOUT = 3600       # 单个任务超时时间（秒）

# 定时任务定义
SCHEDULER_JOBS = [
    {
        'spider': 'financial_data_spider',    # 爬虫名称
        'cron': '0 */6 * * *',              # 每6小时执行一次
        'enabled': True,                     # 是否启用
        'priority': 10,                      # 优先级
        'max_retries': 3,                    # 最大重试次数
        'retry_delay': 60                    # 重试延迟（秒）
    },
    {
        'spider': 'news_spider',              # 新闻爬虫
        'cron': '0 2 * * *',                # 每天凌晨2点执行
        'enabled': True,
        'priority': 5,
        'max_retries': 2,
        'retry_delay': 120
    }
]

# 资源监控配置
SCHEDULER_RESOURCE_MONITOR_ENABLED = True    # 启用资源监控
SCHEDULER_RESOURCE_CHECK_INTERVAL = 300      # 资源检查间隔（秒）
```

### 1.2 启动脚本 (run.py)

```python
#!/usr/bin/env python3
"""
项目启动脚本
"""
import os
import sys
import asyncio

from crawlo.crawler import CrawlerProcess


def main():
    """主函数"""
    try:
        # 检查命令行参数
        if len(sys.argv) > 1 and sys.argv[1] == '--schedule':
            # 启动定时任务模式
            from crawlo.scheduling.scheduler_daemon import start_scheduler
            project_root = os.path.dirname(os.path.abspath(__file__))
            start_scheduler(project_root=project_root)
        else:
            # 正常运行模式
            spider_name = sys.argv[1] if len(sys.argv) > 1 else 'financial_data_spider'
            asyncio.run(CrawlerProcess().crawl(spider_name))
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"❌ 运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
```

## 2. 常见定时任务场景

### 2.1 每小时执行一次

```python
{
    'spider': 'hourly_data_sync',
    'cron': '0 * * * *',        # 每小时执行一次
    'enabled': True,
    'priority': 10
}
```

### 2.2 每天凌晨执行

```python
{
    'spider': 'daily_report',
    'cron': '0 2 * * *',        # 每天凌晨2点执行
    'enabled': True,
    'priority': 20
}
```

### 2.3 每周执行一次

```python
{
    'spider': 'weekly_summary',
    'cron': '0 3 * * 0',        # 每周日凌晨3点执行
    'enabled': True,
    'priority': 5
}
```

### 2.4 每分钟执行（高频率）

```python
{
    'spider': 'real_time_monitor',
    'cron': '* * * * *',        # 每分钟执行
    'enabled': True,
    'priority': 15,
    'max_retries': 1,
    'retry_delay': 30
}
```

## 3. 完整的项目示例

### 3.1 项目结构

```
my_crawler_project/
├── my_crawler_project/
│   ├── __init__.py
│   ├── settings.py          # 配置文件
│   ├── spiders/
│   │   ├── __init__.py
│   │   └── data_spider.py   # 爬虫定义
│   └── pipelines.py         # 数据管道
├── run.py                   # 启动脚本
└── requirements.txt
```

### 3.2 完整配置文件示例

```python
# settings.py
from crawlo.config import CrawloConfig

# 基础配置
config = CrawloConfig.auto(
    project_name='my_financial_crawler',
    concurrency=8,
    download_delay=1.0
)

locals().update(config.to_dict())

# 爬虫模块
SPIDER_MODULES = ['my_crawler_project.spiders']

# 数据管道
PIPELINES = [
    'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',
]

# 数据库配置
MYSQL_HOST = '127.0.0.1'
MYSQL_PORT = 3306
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'password'
MYSQL_DB = 'crawler_db'

# =================================== 定时任务配置 ===================================
# 启用调度器
SCHEDULER_ENABLED = True
SCHEDULER_CHECK_INTERVAL = 60      # 1分钟检查一次
SCHEDULER_MAX_CONCURRENT = 3       # 最多3个并发任务
SCHEDULER_JOB_TIMEOUT = 7200       # 2小时超时

# 定时任务配置
SCHEDULER_JOBS = [
    # 财务数据爬取 - 每6小时执行
    {
        'spider': 'financial_data_spider',
        'cron': '0 */6 * * *',
        'enabled': True,
        'priority': 10,
        'max_retries': 3,
        'retry_delay': 120
    },
    # 新闻资讯爬取 - 每小时执行
    {
        'spider': 'news_spider',
        'cron': '0 * * * *',
        'enabled': True,
        'priority': 5,
        'max_retries': 2,
        'retry_delay': 60
    },
    # 每日报告生成 - 每天凌晨执行
    {
        'spider': 'daily_report_spider',
        'cron': '0 1 * * *',
        'enabled': True,
        'priority': 20,
        'max_retries': 1,
        'retry_delay': 300
    }
]

# 资源监控
SCHEDULER_RESOURCE_MONITOR_ENABLED = True
SCHEDULER_RESOURCE_CHECK_INTERVAL = 600  # 10分钟检查一次资源
```

### 3.3 启动脚本

```python
# run.py
#!/usr/bin/env python3
"""
My Financial Crawler 项目启动脚本
"""
import os
import sys
import asyncio

from crawlo.crawler import CrawlerProcess


def main():
    """主函数"""
    print("My Financial Crawler 启动中...")
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--schedule':
            # 启动定时任务模式
            print("启动定时任务模式...")
            from crawlo.scheduling.scheduler_daemon import start_scheduler
            project_root = os.path.dirname(os.path.abspath(__file__))
            start_scheduler(project_root=project_root)
        elif sys.argv[1] == '--help':
            print_help()
        else:
            # 运行指定爬虫
            spider_name = sys.argv[1]
            print(f"运行爬虫: {spider_name}")
            asyncio.run(CrawlerProcess().crawl(spider_name))
    else:
        # 默认运行
        print("使用方法:")
        print("  python run.py --schedule    # 启动定时任务")
        print("  python run.py spider_name   # 运行指定爬虫")
        print("  python run.py --help        # 显示帮助")


def print_help():
    """打印帮助信息"""
    print("""
My Financial Crawler 使用说明:

定时任务模式:
  python run.py --schedule
    启动调度器，根据 settings.py 中的 SCHEDULER_JOBS 配置执行定时任务

运行特定爬虫:
  python run.py spider_name
    运行指定名称的爬虫

可用爬虫:
  - financial_data_spider    # 财务数据爬虫
  - news_spider             # 新闻爬虫  
  - daily_report_spider     # 每日报告爬虫
    """)


if __name__ == '__main__':
    main()
```

## 4. 启动和管理

### 4.1 启动定时任务

```bash
# 进入项目目录
cd my_crawler_project

# 启动定时任务
python run.py --schedule
```

### 4.2 使用 systemd 管理（Linux）

创建服务文件 `/etc/systemd/system/my-crawler.service`：

```ini
[Unit]
Description=My Crawler Scheduler
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/my_crawler_project
ExecStart=/usr/bin/python3 /path/to/my_crawler_project/run.py --schedule
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable my-crawler
sudo systemctl start my-crawler
```

### 4.3 Docker 部署

Dockerfile:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "run.py", "--schedule"]
```

docker-compose.yml:
```yaml
version: '3.8'
services:
  crawler-scheduler:
    build: .
    restart: unless-stopped
    environment:
      - PYTHONUNBUFFERED=1
    volumes:
      - ./logs:/app/logs
```

## 5. 监控和维护

### 5.1 日志监控

定时任务的日志会输出到配置的 LOG_FILE 中，可以通过以下命令监控：

```bash
# 实时查看日志
tail -f logs/my_financial_crawler.log

# 查看最近的调度器日志
grep -i "scheduler\|cron" logs/my_financial_crawler.log
```

### 5.2 任务状态检查

可以通过调度器的统计信息来监控任务执行状态：

```python
# 获取调度器统计信息
from crawlo.scheduling.scheduler_daemon import SchedulerDaemon
from crawlo.settings.setting_manager import SettingManager

settings = SettingManager()
# ... 加载配置 ...
daemon = SchedulerDaemon(settings)
stats = daemon.get_stats()

print(f"总执行次数: {stats['total_executions']}")
print(f"成功执行: {stats['successful_executions']}")
print(f"失败执行: {stats['failed_executions']}")
```

这个案例展示了如何在 Crawlo 框架中配置和使用定时调度功能，包括基础配置、常见场景、完整项目示例以及部署和监控方法。