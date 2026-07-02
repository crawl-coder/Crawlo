# Prometheus + Grafana 集成指南

> 为 Crawlo 爬虫添加原生 Prometheus 指标暴露和 Grafana 可视化能力。

---

## 快速开始（5 分钟）

### 1. 安装依赖

```bash
pip install crawlo[monitoring]
# 或单独安装：pip install prometheus-client>=0.19.0
```

### 2. 配置爬虫

在 `settings.py` 中设置：

```python
STATS_BACKEND = 'prometheus'          # 启用 Prometheus 统计后端
PROMETHEUS_METRICS_PORT = 9100        # 指标暴露端口
```

### 3. 运行爬虫

```bash
crawlo run myspider
```

启动日志中应看到：

```
Prometheus metrics endpoint started on http://0.0.0.0:9100/metrics (labels={'spider': 'myspider', 'worker_id': 'oscar-mbp-12345'})
```

### 4. 验证指标

```bash
curl http://localhost:9100/metrics
```

输出示例：

```
# HELP crawlo_response_received_count_total Auto-generated from "response_received_count"
# TYPE crawlo_response_received_count_total counter
crawlo_response_received_count_total{spider="myspider",worker_id="oscar-mbp-12345"} 1427
# HELP crawlo_item_successful_count_total Auto-generated from "item_successful_count"
# TYPE crawlo_item_successful_count_total counter
crawlo_item_successful_count_total{spider="myspider",worker_id="oscar-mbp-12345"} 138
# HELP crawlo_memory_rss_mb Auto-generated from "memory_rss_mb"
# TYPE crawlo_memory_rss_mb gauge
crawlo_memory_rss_mb{spider="myspider",worker_id="oscar-mbp-12345"} 256.5
# HELP crawlo_queue_size Auto-generated from "queue_size"
# TYPE crawlo_queue_size gauge
crawlo_queue_size{spider="myspider",worker_id="oscar-mbp-12345"} 0
```

---

## 配置参考

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `STATS_BACKEND` | `'memory'` | 统计后端类型。设为 `'prometheus'` 启用 |
| `PROMETHEUS_METRICS_PORT` | `9100` | 指标暴露端口。设为 `0` 自动分配可用端口（多 worker 同机部署时使用） |
| `PROMETHEUS_LABELS` | `{}` | 额外标签，如 `{'env': 'production', 'dc': 'shanghai'}`。注意不会覆盖 `spider`/`worker_id` 内置标签 |
| `MEMORY_MONITOR_ENABLED` | `False` | 启用内存监控（建议开启以暴露 `memory_rss_mb` 指标） |
| `MEMORY_MONITOR_INTERVAL` | `60` | 内存监控采样间隔（秒） |

### 完整配置示例

```python
# settings.py
STATS_BACKEND = 'prometheus'

# Prometheus 裸端口（单机模式）
PROMETHEUS_METRICS_PORT = 9100

# 额外标签
PROMETHEUS_LABELS = {'env': 'staging', 'team': 'crawler'}

# 开启内存监控（暴露 memory_rss_mb / memory_percent / thread_count）
MEMORY_MONITOR_ENABLED = True
MEMORY_MONITOR_INTERVAL = 60
```

---

## 指标参考

### 自动暴露的计数器（Counter）

| Prometheus 指标名 | 框架统计 key | 说明 |
|-------------------|-------------|------|
| `crawlo_response_received_count_total` | `response_received_count` | 收到的响应总数 |
| `crawlo_item_successful_count_total` | `item_successful_count` | 成功产出 Item |
| `crawlo_item_discard_count_total` | `item_discard_count` | 丢弃 Item |
| `crawlo_request_scheduler_count_total` | `request_scheduler_count` | 调度请求数（不含重试） |
| `crawlo_retry_count_total` | `retry_count` | 重试次数 |
| `crawlo_response_total_bytes_total` | `response_total_bytes` | 响应总字节 |
| `crawlo_downloader_exception_count_total` | `downloader/exception_count` | 下载异常总数 |
| `crawlo_response_status_code_success_count_total` | `response_status_code/success_count` | 2xx 成功计数 |
| `crawlo_response_status_code_error_count_total` | `response_status_code/error_count` | 错误状态码计数 |
| `crawlo_offsite_request_count_total` | `offsite_request_count` | 域外请求 |
| `crawlo_request_ignore_count_total` | `request_ignore_count` | 被忽略请求 |
| `crawlo_response_status_code_3xx_total` | `response_status_code/3xx` | 3xx 重定向 |
| `crawlo_response_status_code_4xx_total` | `response_status_code/4xx` | 4xx 客户端错误 |
| `crawlo_response_status_code_5xx_total` | `response_status_code/5xx` | 5xx 服务端错误 |

> 以上指标名由框架 key 自动生成，`crawlo_` 前缀可通过 `STATS_PREFIX` 配置修改。
> 含中文/特殊字符的 key（如 `request_ignore_count/reason/状态码 403`）会被自动清洗为合法指标名。

### 自动暴露的瞬时值（Gauge）

| Prometheus 指标名 | 框架统计 key | 写入时机 |
|-------------------|-------------|---------|
| `crawlo_concurrency_limit` | `concurrency_limit` | 爬虫关闭时 |
| `crawlo_max_concurrent_seen` | `max_concurrent_seen` | 爬虫关闭时 |
| `crawlo_concurrency_utilization` | `concurrency_utilization` | 爬虫关闭时 |
| `crawlo_avg_response_time_ms` | `avg_response_time_ms` | 爬虫关闭时 |
| `crawlo_items_per_minute` | `items_per_minute` | 爬虫关闭时 |
| `crawlo_pages_per_minute` | `pages_per_minute` | 爬虫关闭时 |

### 需开启扩展后暴露的指标

以下指标需要对应的扩展启用后才会出现在 `/metrics` 中：

| Prometheus 指标名 | 框架统计 key | 依赖扩展/开关 |
|-------------------|-------------|--------------|
| `crawlo_memory_rss_mb` | `memory_rss_mb` | `MEMORY_MONITOR_ENABLED = True` |
| `crawlo_memory_percent` | `memory_percent` | 同上 |
| `crawlo_thread_count` | `thread_count` | 同上 |
| `crawlo_queue_size` | `queue_size` | 默认启用的 `LogIntervalExtension`（内置） |

> `queue_size` 由 `LogIntervalExtension` 每周期自动写入，该扩展默认启用，无需额外配置。
> 注意：爬虫空闲（无请求、无产出、队列为空）时跳过写入，此时队列指标在 Prometheus 中保留上一周期值。

---

## Docker Compose 完整部署

```yaml
version: '3.8'

services:
  crawlo-worker:
    build: .
    command: crawlo run myspider
    ports:
      - "9100:9100"
    environment:
      - STATS_BACKEND=prometheus
      - PROMETHEUS_METRICS_PORT=9100
      - MEMORY_MONITOR_ENABLED=true

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
```

`prometheus.yml`：

```yaml
scrape_configs:
  - job_name: 'crawlo'
    scrape_interval: 15s
    static_configs:
      - targets: ['crawlo-worker:9100']
```

---

## 多 Worker 部署

同一台机器运行多个 worker 时，**每个 worker 必须使用不同端口**。

```python
# worker 1 settings.py
PROMETHEUS_METRICS_PORT = 9101

# worker 2 settings.py
PROMETHEUS_METRICS_PORT = 9102
```

或使用 `PROMETHEUS_METRICS_PORT = 0` 让框架自动分配可用端口（需从启动日志查看实际端口）。

`prometheus.yml` 中配置所有 worker：

```yaml
scrape_configs:
  - job_name: 'crawlo'
    scrape_interval: 15s
    static_configs:
      - targets:
        - 'worker1-host:9101'
        - 'worker2-host:9102'
```

各 worker 的指标通过 `worker_id` 标签区分，PromQL 中可用 `sum by(worker_id)(...)` 聚合。

---

## Grafana 看板

### 导入方式

1. 打开 Grafana → `+` → `Import`
2. 上传 `assets/grafana/crawlo-dashboard.json`（如仓库中尚未包含，参考下方 PromQL 手动创建）
3. 选择 Prometheus 数据源
4. 保存

### 推荐面板 PromQL

| 面板 | PromQL |
|------|--------|
| 请求速率（QPS） | `rate(crawlo_response_received_count_total[1m])` |
| 采集速率（Items/s） | `rate(crawlo_item_successful_count_total[5m])` |
| 成功率 | `crawlo_item_successful_count_total / clamp_min(crawlo_item_successful_count_total + crawlo_item_discard_count_total, 1) * 100` |
| 状态码分布 | `increase(crawlo_response_status_code_success_count_total[5m])` 与 `_4xx` `_5xx` 堆叠 |
| 内存趋势 | `crawlo_memory_rss_mb` |
| 并发水位 | `crawlo_concurrency_limit` + `crawlo_max_concurrent_seen` |
| 平均响应时间 | `crawlo_avg_response_time_ms` |
| 队列积压 | `crawlo_queue_size` |
| 重试/异常率 | `rate(crawlo_retry_count_total[5m])` + `rate(crawlo_downloader_exception_count_total[5m])` |
| 各 Worker 请求数 | `sum by(worker_id)(crawlo_response_received_count_total)` |

### 看板配置建议

- **模板变量**：`spider` 和 `worker_id` 作为下拉筛选器
- **刷新间隔**：30s（与 Prometheus scrape interval 对齐）
- **时间范围**：最近 6 小时

---

## 生产建议

### 端口安全

不建议将 `/metrics` 端口直接暴露到公网。推荐的方式：

1. **反向代理认证**：通过 Nginx/Caddy 添加 Basic Auth 或 IP 白名单
2. **防火墙规则**：仅允许 Prometheus Server IP 访问
3. **内网部署**：Prometheus 与爬虫部署在同一内网

### Alertmanager 告警规则示例

```yaml
groups:
  - name: crawlo_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(crawlo_response_status_code_4xx_total[5m]) / rate(crawlo_response_received_count_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "爬虫 {{ $labels.spider }} 错误率超过 10%"

      - alert: MemoryLeak
        expr: crawlo_memory_rss_mb > 1024
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "Worker {{ $labels.worker_id }} 内存超过 1GB"

      - alert: QueueBacklog
        expr: crawlo_queue_size > 10000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "队列积压 {{ $value }} 条"
```

### scrape interval 调优

- 爬虫运行中，15s 的 scrape interval 足够捕捉趋势
- 如需更高精度（如 < 5s），需同步减小 `MEMORY_MONITOR_INTERVAL` 和 `INTERVAL`
- 注意：过短的 interval 会增加 Prometheus server 和爬虫的负担

### 与通知系统共存

Prometheus 负责**拉模式**的长期可观测性，现有通知系统（钉钉/飞书/企微/邮件）负责**推模式**的短平快告警，两者互补，无需二选一。

---

## 兼容性说明

| 问题 | 说明 |
|------|------|
| `start_http_server` 返回 `None` | 部分 prometheus-client 版本中 `start_http_server` 返回 `None`，此时无法通过 `close()` 释放端口。端口在进程退出后自动释放，不会影响多轮爬虫。 |
| 端口 `0` 自动分配 | `port=0` 时框架自动查找空闲端口，实际端口号打印在启动日志中。 |
| 字符串值跳过 | `reason`/`spider_name`/`start_time` 等字符串 key 自动跳过，不产生 Prometheus 指标。不影响 `get_value()`。 |
| 含中文的 key | 自动清洗为合法指标名（如 `状态码 403` → `_403`），不影响指标值。 |
