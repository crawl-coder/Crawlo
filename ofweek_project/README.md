# Ofweek 项目使用说明

本项目演示了如何使用 Crawlo 框架的两种运行模式：standalone（单机模式）和 distributed（分布式模式）。

## 项目结构

```
ofweek_project/
├── crawlo.cfg                 # 项目配置文件
├── run_standalone.py          # standalone 模式运行脚本
├── run_distributed.py         # distributed 模式运行脚本
├── run_spider.py              # 基本运行脚本
├── logs/                      # 日志目录
└── ofweek_project/            # 项目包
    ├── __init__.py
    ├── settings.py            # 项目配置
    ├── items.py               # 数据结构定义
    ├── middlewares.py         # 中间件
    ├── pipelines.py           # 数据管道
    └── spiders/               # 爬虫目录
        ├── __init__.py
        └── OfweekSpider.py    # Ofweek 爬虫实现
```

## 运行模式说明

### Standalone 模式（单机模式）

Standalone 模式适用于单机运行，使用内存队列和去重过滤器。

**特点：**
- 使用内存队列管理请求
- 使用内存去重过滤器
- 适合小规模数据采集
- 配置简单，易于调试

**运行方法：**
```bash
python run_standalone.py
```

**配置说明：**
- 并发数：8
- 下载延迟：1.0 秒
- 使用内存队列和去重过滤器

### Distributed 模式（分布式模式）

Distributed 模式适用于分布式部署，使用 Redis 队列和去重过滤器。

**特点：**
- 使用 Redis 队列管理请求
- 使用 Redis 去重过滤器
- 支持多节点协同工作
- 适合大规模数据采集

**运行方法：**
```bash
python run_distributed.py
```

**配置说明：**
- 并发数：16（比单机模式更高）
- 下载延迟：0.5 秒（比单机模式更短）
- 使用 Redis 队列和去重过滤器
- 需要 Redis 服务器支持

## 环境准备

### Standalone 模式

Standalone 模式不需要额外的环境准备，直接运行即可。

### Distributed 模式

Distributed 模式需要准备 Redis 环境：

1. **安装 Redis**
   ```bash
   # Windows (使用 Docker)
   docker run -d -p 6379:6379 --name redis-crawlo redis:alpine
   
   # Linux
   sudo apt-get install redis-server
   
   # macOS
   brew install redis
   ```

2. **启动 Redis**
   ```bash
   # Windows (Docker)
   docker start redis-crawlo
   
   # Linux/macOS
   redis-server
   ```

3. **验证连接**
   ```bash
   redis-cli ping
   # 应该返回 PONG
   ```

## 配置文件说明

### settings.py

项目的主要配置文件，包含网络请求、并发、数据存储等配置。

### crawlo.cfg

框架配置文件，指定默认设置模块。

## 爬虫说明

### OfweekSpider

爬取 Ofweek 网站的爬虫，支持以下功能：
- 并发爬取
- 自动去重过滤
- 错误重试机制
- 数据管道处理

## 使用示例

### 单机模式运行
```bash
cd ofweek_project
python run_standalone.py
```

### 分布式模式运行
```bash
cd ofweek_project
python run_distributed.py
```

### 多节点分布式运行
```bash
# 节点1
python run_distributed.py

# 节点2（在另一台机器上）
python run_distributed.py

# 节点3（在另一台机器上）
python run_distributed.py
```

## 性能调优

### Standalone 模式调优
- 调整 `CONCURRENCY` 参数控制并发数
- 调整 `DOWNLOAD_DELAY` 参数控制请求频率

### Distributed 模式调优
- 增加节点数量提升整体性能
- 调整 `CONCURRENCY` 参数控制每个节点的并发数
- 调整 `DOWNLOAD_DELAY` 参数控制请求频率
- 优化 Redis 配置提升性能

## 故障排除

### Redis 连接问题
1. 检查 Redis 服务是否启动
2. 检查 Redis 配置是否正确
3. 检查防火墙设置

### 爬虫运行问题
1. 查看日志文件定位问题
2. 检查网络连接
3. 验证目标网站是否可访问

## 最佳实践

1. **开发阶段**：使用 Standalone 模式进行开发和调试
2. **测试阶段**：使用 Standalone 模式进行小规模测试
3. **生产阶段**：使用 Distributed 模式进行大规模数据采集
4. **监控**：定期检查日志和统计数据
5. **维护**：定期清理 Redis 数据避免内存溢出