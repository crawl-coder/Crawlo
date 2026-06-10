# Crawlo 生产环境部署指南

> 适用：Linux 服务器（CentOS 7+ / Ubuntu 20.04+ / Debian 11+）

!!! tip "部署模式概览"
    本文档聚焦**服务器环境部署**（安装、systemd 守护、监控运维）。  
    三种运行模式（内存/多节点协作/分布式系统）的**配置差异**与**运行机制**详见 [部署模式详解](guides/configuration/run-modes.md)。

---

## 相关文档

- [部署模式详解](guides/configuration/run-modes.md) — 三种运行模式的配置与工作机制
- [分布式架构设计](distributed_architecture.md) — 集群架构、任务生命周期、故障恢复、协调退出
- [配置指南](guides/configuration/) — 全部配置项说明
- [故障排查](faq/troubleshooting.md) — 常见问题诊断

---

## 环境要求

| 组件 | 单机版 | 多节点协作 | 分布式系统 |
|------|--------|-----------|-----------|
| Python | ≥ 3.8 | ≥ 3.8 | ≥ 3.8 |
| Redis | — | ≥ 6.0 | ≥ 7.0 |
| MySQL | 可选 | 可选 | 推荐 |
| 内存 | ≥ 512MB | ≥ 1GB | ≥ 2GB / 节点 |
| 网络 | — | 内网互通 | 内网互通 |

---

## 一、基础环境

### 1. 安装 Python

```bash
# Ubuntu 22.04+（自带 Python 3.10+）
sudo apt update && sudo apt install -y python3 python3-venv python3-pip

# Ubuntu 20.04（需添加 PPA）
sudo apt update && sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt install -y python3.10 python3.10-venv python3-pip
```

### 2. 创建项目

```bash
# 创建虚拟环境
python3 -m venv /opt/crawlo/venv
source /opt/crawlo/venv/bin/activate

# 安装 Crawlo
pip install --upgrade pip
pip install crawlo

# 若需 MySQL 入库，安装 asyncmy
pip install asyncmy

# 创建项目
mkdir -p /opt/crawlo/projects
cd /opt/crawlo/projects
crawlo startproject myproject
cd myproject

# 创建爬虫
crawlo genspider news example.com
```

### 3. 项目结构

```
myproject/
├── crawlo.cfg                      # 项目配置（指向 settings 模块）
├── run.py                          # 入口脚本
└── myproject/
    ├── __init__.py
    ├── items.py                    # Item 定义
    ├── middlewares.py              # 自定义中间件
    ├── pipelines.py                # 数据管道
    ├── settings.py                 # 主配置（CrawloConfig.auto()）
    ├── settings_distributed.py     # 分布式配置模板
    ├── settings_gentle.py          # 温和模式配置模板
    ├── settings_high_performance.py # 高性能配置模板
    └── spiders/
        ├── __init__.py
        └── news.py                 # 爬虫
```

> **提示**：`crawlo startproject` 会自动生成多套 settings 模板，可根据场景选择或修改。`settings_distributed.py` 已预配置分布式参数。

### 4. 运行命令

```bash
# 运行指定爬虫
crawlo run news

# 运行所有爬虫
crawlo run all

# 定时调度模式
crawlo run schedule
# 或
crawlo schedule

# 常用参数
crawlo run news --concurrency 32        # 覆盖并发数
crawlo run news --log-level DEBUG       # 覆盖日志级别
crawlo run news --fresh                 # 忽略检查点，从头开始
crawlo run news --clean-checkpoint      # 清除检查点后运行

# 调试命令
crawlo list                             # 列出所有已注册爬虫
crawlo check                            # 检查项目配置
```

### 5. 使用 run.py

项目模板自带 `run.py`，支持普通和定时两种模式：

```bash
python run.py               # 运行默认爬虫
python run.py --schedule    # 启动定时调度
```

---

## 二、模式一：单机版

### 适用场景

- 数据量 < 10 万页
- 单机开发调试
- 无需 Redis / 多节点

### 配置

```python
# myproject/settings.py
from crawlo.config import CrawloConfig

config = CrawloConfig.standalone(
    project_name='myproject',
    concurrency=16,
    download_delay=0.5,
)
locals().update(config.to_dict())

# 可选项：启用断点续爬（默认关闭）
CHECKPOINT_ENABLED = True
# CHECKPOINT_DIR 默认为 None，实际存储路径为 .checkpoints/{project}/{spider}

# 可选项：启用定时调度
SCHEDULER_ENABLED = True
SCHEDULER_JOBS = [
    {
        'spider': 'news',
        'cron': '0 2 * * *',   # 每天凌晨 2 点
        'enabled': True,
        'priority': 5,
        'max_retries': 3,
    },
]

# 可选项：MySQL 入库（需 pip install asyncmy）
ITEM_PIPELINES = {
    'crawlo.pipelines.MySQLPipeline': 300,
}
MYSQL_HOST = '127.0.0.1'
MYSQL_PORT = 3306
MYSQL_USER = 'crawlo'
MYSQL_PASSWORD = 'your_password'
MYSQL_DB = 'crawlo_db'
MYSQL_TABLE = 'news'          # 默认为 {spider_name}_items
MYSQL_BATCH_SIZE = 500         # 批量入库条数，默认 500
MYSQL_USE_BATCH = True

# 可选项：生产日志
LOG_FILE = 'logs/crawlo.log'   # 日志目录自动创建
LOG_FILE_ENABLED = True
LOG_RETENTION_DAYS = 7
```

### 运行

```bash
# 单次运行
crawlo run news

# 定时调度
crawlo run schedule
```

### systemd 守护（单机定时）

```ini
# /etc/systemd/system/crawlo-news.service
[Unit]
Description=Crawlo News Spider
After=network.target

[Service]
Type=simple
User=crawlo
WorkingDirectory=/opt/crawlo/projects/myproject
ExecStart=/opt/crawlo/venv/bin/python /opt/crawlo/projects/myproject/run.py --schedule
Restart=always
RestartSec=10
# 框架自带 LOG_FILE 日志，StandardOutput 仅记录框架外输出
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now crawlo-news

# 查看日志
sudo journalctl -u crawlo-news -f
# 或查看框架日志文件
tail -f /opt/crawlo/projects/myproject/logs/crawlo.log
```

---

## 三、模式二：多节点协作

### 适用场景

- 数据量 10 万 ~ 100 万页
- 多台机器共享 Redis 队列
- 可接受任务级别的容错

### 架构

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   节点 A      │  │   节点 B      │  │   节点 C      │
│  Crawlo Auto  │  │  Crawlo Auto  │  │  Crawlo Auto  │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         │
                   ┌─────▼─────┐
                   │   Redis    │  ← ZSET 队列 + SET 去重
                   │  BZPOPMIN  │
                   └───────────┘
```

### 1. 安装 Redis

```bash
# 在队列服务器上安装
sudo apt install -y redis-server

# 配置远程访问
sudo sed -i 's/bind 127.0.0.1/bind 0.0.0.0/' /etc/redis/redis.conf
sudo sed -i 's/protected-mode yes/protected-mode no/' /etc/redis/redis.conf
echo "requirepass your_redis_password" | sudo tee -a /etc/redis/redis.conf
sudo systemctl restart redis
sudo systemctl enable redis

# 验证（使用 REDISCLI_AUTH 避免密码暴露在命令历史）
REDISCLI_AUTH=your_redis_password redis-cli -h 127.0.0.1 ping
```

### 2. 配置爬虫（所有节点相同）

```python
# myproject/settings.py
from crawlo.config import CrawloConfig

config = CrawloConfig.auto(
    project_name='myproject',
    concurrency=16,
    download_delay=1.0,
)
locals().update(config.to_dict())

# Redis 配置（指向队列服务器）
REDIS_HOST = '10.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = 'your_redis_password'
REDIS_DB = 0

# 生产日志
LOG_FILE = 'logs/crawlo.log'
LOG_FILE_ENABLED = True
```

> **说明**：`CrawloConfig.auto()` 会自动检测 Redis 可用性——若 Redis 可连接，切换为分布式队列；否则回退到内存队列。

### 3. 部署到所有节点

```bash
# 方式一：手动部署
# 将项目复制到每个节点的 /opt/crawlo/projects/myproject
cd /opt/crawlo/projects/myproject
python run.py

# 方式二：使用环境变量（推荐，无需修改 settings.py）
export CRAWLO_MODE=auto
export CRAWLO_REDIS_HOST=10.0.0.1
export CRAWLO_REDIS_PASSWORD=your_redis_password
export CRAWLO_PROJECT_NAME=myproject
export CRAWLO_CONCURRENCY=16
python run.py
```

> **环境变量支持**：`CrawloConfig.from_env()` 可读取所有 `CRAWLO_` 前缀的环境变量，适合容器化部署。

### systemd 守护（多节点）

```ini
# /etc/systemd/system/crawlo-worker.service
[Unit]
Description=Crawlo Worker
After=network.target

[Service]
Type=simple
User=crawlo
WorkingDirectory=/opt/crawlo/projects/myproject
ExecStart=/opt/crawlo/venv/bin/python /opt/crawlo/projects/myproject/run.py
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal

# 环境变量方式（可选）
# Environment=CRAWLO_MODE=auto
# Environment=CRAWLO_REDIS_HOST=10.0.0.1
# Environment=CRAWLO_REDIS_PASSWORD=your_redis_password

[Install]
WantedBy=multi-user.target
```

---

## 四、模式三：分布式系统

### 适用场景

- 数据量 > 100 万页
- 要求 24 小时内完成
- 数据不能丢
- 需要故障转移和死信重试

### 架构

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Worker 1     │  │  Worker 2     │  │  Worker 3     │  │  Worker N     │
│  conc=12      │  │  conc=12      │  │  conc=12      │  │  conc=12      │
│  Heartbeat    │  │  Heartbeat    │  │  Heartbeat    │  │  Heartbeat    │
│  Failover     │  │  Failover     │  │  Failover     │  │  Failover     │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │                 │
       └─────────────────┼─────────────────┼─────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                                 │
   ┌────▼─────┐  ┌──────────┐  ┌─────────▼──┐
   │  Redis    │  │  MySQL   │  │  Monitoring │
   │  Stream   │  │ （存储）  │  │  Cluster    │
   │  HASH     │  └──────────┘  │  Monitor    │
   │  ZSET     │                └────────────┘
   │  SET      │
   │  PubSub   │
   └──────────┘
```

> **说明**：分布式模式无独立 Master 进程，所有 Worker 对等运行。协调机制通过 Redis Stream（任务分发）+ HASH（Worker 注册/心跳）+ PubSub（控制指令）实现，故障转移由每个 Worker 的 `FailoverManager` 自主执行。

### 1. 安装 Redis 7+

```bash
# 方式一：Docker（推荐）
docker run -d --name redis \
  --restart=always \
  -p 6379:6379 \
  redis:7-alpine redis-server --requirepass your_password

# 方式二：官方 APT 源
curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list
sudo apt update && sudo apt install -y redis
```

### 2. 安装 MySQL

```bash
# Docker 方式
docker run -d --name mysql \
  --restart=always \
  -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=root123 \
  -e MYSQL_DATABASE=crawlo_db \
  -e MYSQL_USER=crawlo \
  -e MYSQL_PASSWORD=crawlo123 \
  mysql:8.0

# 创建表
docker exec -i mysql mysql -ucrawlo -pcrawlo123 crawlo_db <<'SQL'
CREATE TABLE IF NOT EXISTS news (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(512),
    publish_time VARCHAR(64),
    url VARCHAR(1024) NOT NULL UNIQUE,
    source VARCHAR(128),
    content LONGTEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_url (url),
    INDEX idx_publish_time (publish_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
SQL
```

### 3. 配置爬虫

```python
# myproject/settings.py
from crawlo.config import CrawloConfig

config = CrawloConfig.distributed(
    project_name='myproject',
    redis_host='10.0.0.1',
    redis_port=6379,
    redis_password='your_password',
    redis_db=0,
    concurrency=12,
    download_delay=1.0,
)
locals().update(config.to_dict())

# 断点续爬
CHECKPOINT_ENABLED = True
# CHECKPOINT_DIR 默认存储在 .checkpoints/{project}/{spider}

# MySQL 入库
ITEM_PIPELINES = {
    'crawlo.pipelines.MySQLPipeline': 300,
}
MYSQL_HOST = '10.0.0.1'
MYSQL_PORT = 3306
MYSQL_USER = 'crawlo'
MYSQL_PASSWORD = 'crawlo123'
MYSQL_DB = 'crawlo_db'
MYSQL_TABLE = 'news'
MYSQL_BATCH_SIZE = 500
MYSQL_USE_BATCH = True

# 背压控制
ENABLE_CONTROLLED_REQUEST_GENERATION = True
REDIS_BACKPRESSURE_RATIO = 0.6       # Redis 队列背压阈值（推荐 0.5~0.8）
BACKPRESSURE_STRATEGY = 'queue_size'  # queue_size | adaptive

# 生产日志
LOG_FILE = 'logs/crawlo.log'
LOG_FILE_ENABLED = True
LOG_RETENTION_DAYS = 7
```

> **配置说明**：
> - `CrawloConfig.distributed()` 默认 `concurrency=16`，此处覆盖为 12
> - 背压阈值应使用 `REDIS_BACKPRESSURE_RATIO`（分布式模式），而非已废弃的 `BACKPRESSURE_RATIO`
> - `MYSQL_BATCH_SIZE` 默认 500，可根据入库性能调整

### 4. 部署 Worker

#### 单机单 Worker

```bash
cd /opt/crawlo/projects/myproject
python run.py
```

#### 单机多 Worker（推荐脚本）

```python
# run_workers.py
import subprocess
import sys
import time

NUM_WORKERS = 10

for i in range(NUM_WORKERS):
    p = subprocess.Popen(
        [sys.executable, 'run.py'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"Worker {i+1}/{NUM_WORKERS} started PID={p.pid}")
    time.sleep(2)

print(f"\nAll {NUM_WORKERS} workers started.")
print("Use 'ps aux | grep run.py' to monitor.")
```

> **说明**：不需要为每个 Worker 创建单独的日志文件，框架的 `LOG_FILE` 机制会自动处理日志输出。

### 5. systemd 模板（多 Worker）

```ini
# /etc/systemd/system/crawlo-worker@.service
[Unit]
Description=Crawlo Worker %i
After=network.target

[Service]
Type=simple
User=crawlo
WorkingDirectory=/opt/crawlo/projects/myproject
ExecStart=/opt/crawlo/venv/bin/python /opt/crawlo/projects/myproject/run.py
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
# 启动 10 个 Worker
sudo systemctl daemon-reload
for i in $(seq 1 10); do
    sudo systemctl enable --now crawlo-worker@$i
done

# 查看状态
sudo systemctl status crawlo-worker@{1..10}

# 停止所有 Worker
for i in $(seq 1 10); do
    sudo systemctl stop crawlo-worker@$i
done
```

---

## 五、监控与运维

### CLI 运维命令

```bash
# 列出已注册爬虫
crawlo list

# 检查项目配置
crawlo check

# 查看统计信息
crawlo stats
```

### Redis 监控

```bash
# 设置密码环境变量（避免密码暴露在命令历史）
export REDISCLI_AUTH=your_password

# Worker 注册表
redis-cli HGETALL crawlo:myproject:news:registry:workers

# Consumer Group 状态
redis-cli XINFO GROUPS crawlo:myproject:news:queue:requests

# 待处理任务数
redis-cli XPENDING crawlo:myproject:news:queue:requests crawlo:myproject:news:group:workers

# 队列长度
redis-cli ZCARD crawlo:myproject:news:queue:requests

# 去重指纹数量
redis-cli SCARD crawlo:myproject:news:filter:fingerprint

# Worker 心跳
redis-cli ZRANGE crawlo:myproject:news:registry:heartbeats 0 -1 WITHSCORES
```

> **键名规则**：`crawlo:{project}:{spider}:{category}:{name}`，若未指定 spider 则为 `crawlo:{project}:{category}:{name}`。实际键名以项目配置为准。

### 日志检查

```bash
# 框架日志（推荐）
tail -f /opt/crawlo/projects/myproject/logs/crawlo.log

# systemd 日志
journalctl -u crawlo-worker@1 -f

# 统计错误数
grep -c "ERROR" /opt/crawlo/projects/myproject/logs/crawlo.log

# 统计完成情况
grep "reason.*finished" /opt/crawlo/projects/myproject/logs/crawlo.log | wc -l
```

### MySQL 监控

```sql
-- 入库量
SELECT COUNT(*) FROM news;

-- 最近入库
SELECT title, publish_time, created_at FROM news ORDER BY created_at DESC LIMIT 10;

-- 检查连接
SHOW PROCESSLIST;
```

---

## 六、性能调优

| 参数 | 建议值 | 说明 |
|------|--------|------|
| `concurrency` | 8-32 | 单 Worker 并发数，`CrawloConfig.distributed()` 默认 16 |
| `download_delay` | 0.5-2.0 | 请求间隔（秒），防封 |
| `MYSQL_BATCH_SIZE` | 100-500 | 批量入库条数，默认 500 |
| `REDIS_BACKPRESSURE_RATIO` | 0.5-0.8 | Redis 队列背压阈值 |
| `MEMORY_BACKPRESSURE_RATIO` | 0.4-0.7 | 内存队列背压阈值（单机模式） |
| `SCHEDULER_MAX_QUEUE_SIZE` | 200-10000 | 队列容量限制 |
| `DISTRIBUTED_WORKER_IDLE_TIMEOUT` | 120-300 | Worker 空闲超时（秒） |
| `STREAM_DELIVERY_COUNT_LIMIT` | 3-5 | 消息最大投递次数 |
| Redis `maxmemory` | 1-4GB | 根据 fingerprint 量调整 |
| Worker 数 | CPU 核数 × 2 | 单机 Worker 数建议 |

### 调优建议

- **单机版**：`concurrency=16` + `MEMORY_BACKPRESSURE_RATIO=0.5` + `MYSQL_BATCH_SIZE=500`
- **多节点协作**：`concurrency=16` + `REDIS_BACKPRESSURE_RATIO=0.6` + `DOWNLOAD_DELAY=1.0`
- **分布式系统**：10 Worker × `concurrency=12` + `REDIS_BACKPRESSURE_RATIO=0.6` + `ENABLE_CONTROLLED_REQUEST_GENERATION=True`

---

## 七、安全建议

```bash
# 1. Redis 必须设密码
# /etc/redis/redis.conf
requirepass your_strong_password

# 2. 绑定内网 IP
bind 10.0.0.1

# 3. 防火墙规则
sudo ufw allow from 10.0.0.0/24 to any port 6379  # 仅内网访问 Redis
sudo ufw allow from 10.0.0.0/24 to any port 3306  # 仅内网访问 MySQL

# 4. 文件权限
chmod 600 /opt/crawlo/projects/myproject/settings.py
chown -R crawlo:crawlo /opt/crawlo/

# 5. 使用环境变量管理敏感配置（避免密码硬编码）
export CRAWLO_REDIS_PASSWORD=your_password
export MYSQL_PASSWORD=your_password
```

---

## 八、故障排查

| 问题 | 排查方法 |
|------|---------|
| Worker 无响应 | `journalctl -u crawlo-worker@1 -f` 或查看 `logs/crawlo.log` |
| Redis 连接失败 | `REDISCLI_AUTH=password redis-cli -h 10.0.0.1 ping` |
| MySQL 入库失败 | 检查 `MYSQL_*` 配置 + `SHOW PROCESSLIST` |
| 任务不消费 | `redis-cli XINFO GROUPS crawlo:{project}:{spider}:queue:requests` 检查 lag |
| 死信堆积 | `redis-cli ZCARD crawlo:{project}:{spider}:queue:failed` |
| 检查点恢复异常 | `crawlo run news --fresh` 忽略检查点从头开始 |
| Worker 频繁掉线 | 检查 `CLUSTER_HEARTBEAT_INTERVAL` 和网络延迟 |
| 内存占用过高 | 降低 `concurrency` + 启用 `ENABLE_CONTROLLED_REQUEST_GENERATION` |
| 数据重复入库 | 确认 `MYSQL_INSERT_IGNORE=True`（默认）或启用去重 Pipeline |

---

## 附录：环境变量参考

`CrawloConfig.from_env()` 支持以下环境变量，适合 Docker / Kubernetes 部署：

| 环境变量 | 对应配置 | 说明 |
|---------|---------|------|
| `CRAWLO_MODE` | `RUN_MODE` | standalone / auto / distributed |
| `CRAWLO_REDIS_HOST` | `REDIS_HOST` | Redis 地址 |
| `CRAWLO_REDIS_PORT` | `REDIS_PORT` | Redis 端口 |
| `CRAWLO_REDIS_PASSWORD` | `REDIS_PASSWORD` | Redis 密码 |
| `CRAWLO_REDIS_DB` | `REDIS_DB` | Redis 数据库 |
| `CRAWLO_PROJECT_NAME` | `PROJECT_NAME` | 项目名称 |
| `CRAWLO_CONCURRENCY` | `CONCURRENCY` | 并发数 |
| `CRAWLO_LOG_LEVEL` | `LOG_LEVEL` | 日志级别 |
