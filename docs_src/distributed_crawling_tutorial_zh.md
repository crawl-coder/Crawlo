# 分布式爬取教程

本教程将指导您设置和运行 Crawlo 的分布式爬取系统。

## 先决条件

- 已安装 Crawlo 框架
- 可访问的 Redis 服务器
- 用于分布式爬取的多台机器或进程

## 设置 Redis

### 本地安装 Redis

#### Windows
从官方网站下载 Redis for Windows 或使用 Docker：

```bash
docker run -d -p 6379:6379 --name redis-crawlo redis:alpine
```

#### Linux
```bash
sudo apt-get install redis-server
```

#### macOS
```bash
brew install redis
```

### 启动 Redis

```bash
redis-server
```

验证 Redis 是否运行：
```bash
redis-cli ping
# 应返回：PONG
```

## 为分布式爬取配置项目

### 更新 settings.py

在项目的 `settings.py` 文件中，添加以下分布式配置：

```python
# 分布式模式配置
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis'

# 分布式模式的并发设置
CONCURRENCY = 16
DOWNLOAD_DELAY = 1.0

# 调度器配置
SCHEDULER = 'crawlo.scheduler.redis_scheduler.RedisScheduler'

# Redis 配置
REDIS_HOST = '127.0.0.1'  # 更改为您的 Redis 服务器 IP
REDIS_PORT = 6379
REDIS_PASSWORD = ''  # 如果您的 Redis 需要密码，请设置
REDIS_DB = 2  # Redis 数据库编号
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# 分布式去重
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'
REDIS_KEY = 'myproject:fingerprint'  # 更改为您的项目名称

# 其他分布式设置
SCHEDULER_QUEUE_NAME = 'myproject:requests'
REDIS_TTL = 0  # 指纹过期时间（0 = 永不过期）
CLEANUP_FP = False  # 关闭时是否清理指纹
```

### 更新 run.py

确保您的 `run.py` 文件正确处理分布式模式：

```python
#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import sys
import asyncio
import argparse
from pathlib import Path

# 将项目路径添加到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from crawlo.crawler import CrawlerProcess
    from myproject.spiders.myspider import MySpider
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请确保您在项目根目录中运行此脚本")
    sys.exit(1)

def create_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(description='分布式 Crawlo 爬虫运行器')
    
    parser.add_argument('spider_name', nargs='?', default='myspider',
                        help='要运行的爬虫名称（默认：myspider）')
    
    parser.add_argument('--redis-host', type=str, default='localhost',
                        help='Redis 服务器地址（默认：localhost）')
    
    parser.add_argument('--redis-port', type=int, default=6379,
                        help='Redis 端口（默认：6379）')
    
    parser.add_argument('--redis-password', type=str,
                        help='Redis 密码（如果需要）')
    
    parser.add_argument('--concurrency', type=int,
                        help='并发级别（覆盖设置）')
    
    parser.add_argument('--delay', type=float,
                        help='下载延迟（秒）')
    
    parser.add_argument('--debug', action='store_true',
                        help='启用调试模式')
    
    parser.add_argument('--check-redis', action='store_true',
                        help='检查 Redis 连接并退出')
    
    return parser

async def check_redis_connection(host, port, password=None):
    """检查 Redis 连接"""
    try:
        import redis.asyncio as aioredis
        
        if password:
            url = f'redis://:{password}@{host}:{port}/0'
        else:
            url = f'redis://{host}:{port}/0'
        
        redis = aioredis.from_url(url)
        await redis.ping()
        await redis.aclose()
        
        print(f"✅ Redis 连接成功: {host}:{port}")
        return True
        
    except Exception as e:
        print(f"❌ Redis 连接失败: {host}:{port} - {e}")
        return False

def build_settings(args):
    """从命令行参数构建设置"""
    settings = {}
    
    # Redis 配置
    if args.redis_password:
        redis_url = f'redis://:{args.redis_password}@{args.redis_host}:{args.redis_port}/0'
    else:
        redis_url = f'redis://{args.redis_host}:{args.redis_port}/0'
    
    settings['REDIS_URL'] = redis_url
    settings['REDIS_HOST'] = args.redis_host
    settings['REDIS_PORT'] = args.redis_port
    if args.redis_password:
        settings['REDIS_PASSWORD'] = args.redis_password
    
    # 其他设置
    if args.debug:
        settings['LOG_LEVEL'] = 'DEBUG'
        settings['DUPEFILTER_DEBUG'] = True
        settings['FILTER_DEBUG'] = True
        print("🐛 调试模式已启用")
    
    if args.concurrency:
        settings['CONCURRENCY'] = args.concurrency
        print(f"⚡ 并发数设置为: {args.concurrency}")
    
    if args.delay:
        settings['DOWNLOAD_DELAY'] = args.delay
        print(f"⏱️  下载延迟设置为: {args.delay} 秒")
    
    return settings

async def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    print("🌐 启动分布式 Crawlo 爬虫")
    
    # 检查 Redis 连接
    redis_ok = await check_redis_connection(
        args.redis_host, 
        args.redis_port, 
        args.redis_password
    )
    
    if not redis_ok:
        print("\n💡 解决方案:")
        print("   1. 确保 Redis 服务器正在运行")
        print("   2. 检查 Redis 配置和网络连接")
        print("   3. 验证 Redis 密码（如果已设置）")
        if args.check_redis:
            return
        else:
            print("   4. 使用 --check-redis 选项仅测试连接")
            sys.exit(1)
    
    if args.check_redis:
        print("🎉 Redis 连接检查完成")
        return
    
    # 构建设置
    custom_settings = build_settings(args)
    
    print(f"🔗 Redis 服务器: {args.redis_host}:{args.redis_port}")
    print(f"🌐 多节点模式: 在其他机器上运行相同的脚本")
    
    # 创建爬虫进程
    print(f"\n🚀 启动爬虫: {args.spider_name}")
    
    try:
        # 应用配置并启动
        process = CrawlerProcess()
        
        # 运行指定的爬虫
        if args.spider_name == 'myspider':
            spider_cls = MySpider
            await process.crawl(spider_cls, **custom_settings)
        else:
            print(f"❌ 未知爬虫: {args.spider_name}")
            print("可用爬虫: myspider")
            return
        
        print("✅ 节点执行完成！")
        print("📊 查看输出文件获取此节点的结果")
        print("🔄 其他节点可以继续处理剩余任务")
        
    except ImportError as e:
        print(f"❌ 无法导入爬虫: {e}")
        print("   请检查爬虫文件是否存在")
    except Exception as e:
        print(f"❌ 节点执行错误: {e}")
        if args.debug:
            raise

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  用户中断节点")
        print("🔄 其他节点可以继续运行并处理剩余任务")
    except Exception as e:
        print(f"❌ 运行时错误: {e}")
        sys.exit(1)
```

## 运行分布式爬虫

### 单台机器多进程

终端 1：
```bash
python run.py myspider
```

终端 2（同时运行）：
```bash
python run.py myspider --concurrency 32
```

### 多机器部署

机器 A（Redis 服务器）：
```bash
python run.py myspider
```

机器 B：
```bash
python run.py myspider --redis-host 192.168.1.100 --concurrency 16
```

机器 C：
```bash
python run.py myspider --redis-host 192.168.1.100 --concurrency 24
```

## 监控分布式爬取

### Redis 监控

检查队列大小：
```bash
redis-cli llen myproject:requests
```

检查去重集合大小：
```bash
redis-cli scard myproject:fingerprint
```

### 内置统计

查看爬取统计：
```bash
crawlo stats myspider
```

## 分布式爬取的最佳实践

### 1. 网络配置

确保所有节点都能连接到 Redis 服务器：
- 配置防火墙规则
- 尽可能使用私有网络地址
- 考虑 Redis 安全设置

### 2. 资源管理

- 根据目标服务器容量调整并发数
- 监控每个节点的系统资源
- 在节点间平衡负载

### 3. 错误处理

- 实现适当的重试逻辑
- 优雅地处理网络超时
- 记录错误以供调试

### 4. 数据一致性

- 在节点间使用一致的数据模型
- 实现适当的数据去重
- 考虑使用分布式数据库进行存储

## 故障排除

### 常见问题

1. **Redis 连接失败**
   - 验证 Redis 服务器是否正在运行
   - 检查网络连接
   - 确认 Redis 凭据

2. **重复数据**
   - 确保 Redis 去重正确配置
   - 检查所有节点是否使用相同的 Redis 实例

3. **性能问题**
   - 监控 Redis 性能
   - 调整并发设置
   - 检查网络带宽

### 调试分布式爬取

启用调试模式：
```bash
python run.py myspider --debug
```

检查 Redis 连接：
```bash
python run.py myspider --check-redis
```

实时监控 Redis：
```bash
redis-cli monitor
```

## 扩展分布式爬虫

### 添加更多节点

只需在其他机器上运行相同的命令：
```bash
python run.py myspider --redis-host YOUR_REDIS_HOST --concurrency 20
```

### 删除节点

使用 Ctrl+C 优雅地停止节点。分布式系统将自动重新分配任务。

### 性能调优

1. 根据以下因素调整并发数：
   - 目标服务器容量
   - 网络带宽
   - 系统资源

2. 优化 Redis：
   - 对于大型部署使用 Redis 集群
   - 监控内存使用情况
   - 配置适当的持久性设置

本教程提供了使用 Crawlo 设置和运行分布式爬取的全面指南。通过适当的配置和监控，您可以高效地跨多台机器扩展爬取操作。