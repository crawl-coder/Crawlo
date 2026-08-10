# Docker 部署指南

> 把 Crawlo 爬虫容器化的标准做法：Dockerfile 多阶段构建 + docker-compose
> 编排（爬虫 + Redis + 可选 MySQL/Prometheus），并支持与
> [Redis 高可用](redis-ha.md) 方案配合。

## 1. 镜像构建（Dockerfile）

```dockerfile
# ── 构建阶段：只装依赖，生成 wheel 缓存 ──
FROM python:3.12-slim AS builder

WORKDIR /build

# 系统依赖：lxml/curl-cffi 编译所需
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# 先装 crawlo（含常用 extras），利用层缓存
COPY requirements.txt .
RUN pip install --prefix=/install \
    "crawlo[monitoring,mcp]" \
    asyncmy aiosqlite \
    -r requirements.txt

# ── 运行阶段：瘦身 ──
FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /install /usr/local

# 非 root 运行（安全基线）
RUN useradd --create-home crawler
USER crawler

# 项目文件：crawlo.cfg + 项目包 + 入口
COPY --chown=crawler:crawler crawlo.cfg .
COPY --chown=crawler:crawler myproject/ myproject/
COPY --chown=crawler:crawler run.py .

# 默认命令：单机爬虫（分布式模式用 --distributed / 环境变量切换）
CMD ["python", "run.py"]
```

构建：

```bash
docker build -t my-crawler:1.7.3 .
```

## 2. docker-compose 编排

```yaml
services:
  crawler:
    build: .
    image: my-crawler:1.7.3
    environment:
      CRAWLO_MODE: standalone          # standalone | distributed
      LOG_LEVEL: INFO
      REDIS_HOST: redis
      # 分布式模式：
      # QUEUE_TYPE: redis_stream
      # REDIS_SENTINEL_URLS: redis://sentinel-1:26379,redis://sentinel-2:26379
      # REDIS_SENTINEL_SERVICE: mymaster
    volumes:
      - ./output:/app/output           # 抓取结果
      - ./logs:/app/logs               # 日志
      - ./jobs:/app/jobs               # 检查点/断点续爬
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: ["redis-server", "--appendonly", "yes"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10
    volumes:
      - redis-data:/data

  # 可选：MySQL 存储管道
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-change-me}
      MYSQL_DATABASE: crawlo
    volumes:
      - mysql-data:/var/lib/mysql

  # 可选：Prometheus 指标采集
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    ports:
      - "9090:9090"

volumes:
  redis-data:
  mysql-data:
```

启动：

```bash
docker compose up -d
docker compose logs -f crawler
```

## 3. 优雅停机与断点续爬

Crawlo 支持 Ctrl+C 优雅保存检查点（`CHECKPOINT_ENABLED=True`）：

```yaml
services:
  crawler:
    stop_grace_period: 60s   # 给在途请求排空时间
    environment:
      CHECKPOINT_ENABLED: "True"
      CHECKPOINT_DIR: /app/jobs
```

`docker stop` 会发 SIGTERM → 爬虫排空在途请求并保存检查点 → 下次启动
自动恢复。长任务场景建议配合
[断点续爬](../concepts/checkpoint-guide.md) 与 `jobs/` 卷持久化。

## 4. 与 Redis HA 配合

生产环境不要用单点 Redis。先按
[Redis 高可用](redis-ha.md) 起 3 Sentinel + master + replica，再让爬虫
容器通过 Sentinel 接入：

```yaml
services:
  crawler:
    environment:
      QUEUE_TYPE: redis_stream
      REDIS_SENTINEL_URLS: redis://sentinel-1:26379,redis://sentinel-2:26379,redis://sentinel-3:26379
      REDIS_SENTINEL_SERVICE: mymaster
```

Sentinel 集群容器可直接复用 `scripts/redis_ha/docker-compose.yml`
（`docker compose -f scripts/redis_ha/docker-compose.yml up -d`），
或把它并入本文件。

## 5. 生产注意事项

| 事项 | 建议 |
|---|---|
| **非 root 运行** | Dockerfile 已用 `USER crawler`；文件卷属主需 `--chown` |
| **日志** | `LOG_FILE` 指向 `/app/logs`，配合 `docker logs` 或日志采集 |
| **密钥** | webhook / DB 密码用环境变量或 Docker Secrets，勿写进镜像 |
| **资源限制** | `deploy.resources.limits.memory` 与 `CONCURRENCY` 匹配，防止 OOM |
| **健康检查** | 给 crawler 加 `HEALTHCHECK`（`crawlo check` 或自定义探活） |
| **多 Worker** | 分布式模式起 N 个 crawler 副本（`docker compose up --scale crawler=5`） |

## 6. 进阶：多 Worker + 调度

分布式多 Worker + 定时任务：

```bash
# 3 个 Worker 组成集群（种子由 Leader 生成）
docker compose up -d --scale crawler=3

# 定时任务模式（--schedule 入口，需单独镜像或入口参数）
docker compose run --rm crawler python run.py --schedule
```

> 定时任务依赖 `SCHEDULER_ENABLED` 配置；容器内 cron 不如外部调度器
> （如 systemd timer / K8s CronJob）可靠，生产建议后者。
