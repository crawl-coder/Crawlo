# 监控与告警指南

> 把 Crawlo 爬虫接入生产可观测性：Prometheus 指标 → Grafana 面板 →
> 告警规则 → 钉钉/飞书/企微通知。本文把分散在各指南的能力整合为
> 一份"生产运维视图"。

## 1. 指标接入（Prometheus）

### 1.1 配置

```python
# settings.py
STATS_BACKEND = 'prometheus' # 启用 Prometheus 统计后端
PROMETHEUS_METRICS_PORT = 9100 # 指标暴露端口（多 Worker 同机用 0 自动分配）
PROMETHEUS_LABELS = {'env': 'production', 'team': 'crawler'}

# 扩展（按需）
EXTENSIONS = [
 'crawlo.extensions.HealthCheckExtension', # 健康检查 + duplicate_rps
 'crawlo.extensions.EventloopLagProbe', # 事件循环延迟 P50/P95/P99
 'crawlo.extensions.LogStats', # 周期统计
]
MEMORY_MONITOR_ENABLED = True # 内存/线程指标（memory_rss_mb 等）
```

完整配置与指标名见 [Prometheus 集成](../guides/prometheus-integration.md)。

### 1.2 核心指标清单

| 类别 | 指标（Prometheus 名） | 含义 | 生产关注 |
|---|---|---|---|
| **吞吐**| `crawlo_items_per_minute` | 每分钟产出 Item 数 | 趋势：骤降 = 站点改版/被封 |
| | `crawlo_pages_per_minute` | 每分钟处理页数 | 同上 |
| **质量**| `crawlo_item_discard_count_total` | 丢弃 Item 数 | 异常增高 = 解析规则失效 |
| | `crawlo_retry_count_total` | 重试次数 | 突增 = 网络/反爬 |
| **错误**| `crawlo_downloader_exception_count_total` | 下载异常 | 突增 = 站点变化/代理故障 |
| | `crawlo_response_status_code_5xx_total` | 5xx 计数 | 站点异常 |
| **资源**| `crawlo_memory_rss_mb` | 进程 RSS | 泄漏检测（配合长跑压测） |
| | `crawlo_queue_size` | 队列深度 | 背压是否生效 |
| | `crawlo_queue_pending_count` | Stream 已读未 ACK 消息数（分布式） | **消费积压：持续 >0 说明有 Worker 崩溃或回收未触发** |
| | `crawlo_resource_eventloop_lag_ms_p99` | 事件循环延迟 P99 | > 阈值 = 阻塞/死锁风险 |

## 2. Grafana 面板

### 2.1 数据源

```yaml
# prometheus.yml
scrape_configs:
  - job_name: crawlo
 static_configs:
      - targets: ["crawler:9100"]
```

### 2.2 建议面板

| 面板 | 查询 | 类型 |
|---|---|---|
| 吞吐趋势 | `rate(crawlo_items_per_minute[5m])` | 时间序列 |
| 错误率 | `rate(crawlo_downloader_exception_count_total[5m])` | 时间序列 |
| 状态码分布 | `sum by (code) (crawlo_response_status_code_*_total)` | 柱状 |
| 资源使用 | `crawlo_memory_rss_mb` / `crawlo_queue_size` | Gauge |
| 事件循环健康 | `crawlo_resource_eventloop_lag_ms_p99` | Gauge + 阈值线 |

## 3. 告警规则

```yaml
# prometheus-alerts.yml
groups:
  - name: crawlo
 rules:
 # 吞吐骤降：5 分钟产出 < 阈值 50%（站点改版 / 被封）
      - alert: CrawloThroughputDrop
 expr: rate(crawlo_items_per_minute[5m]) < 50
 for: 5m
 labels: { severity: critical }
 annotations:
 summary: "爬虫吞吐骤降"

 # 下载异常突增
      - alert: CrawloDownloadErrors
 expr: rate(crawlo_downloader_exception_count_total[5m]) > 10
 for: 3m
 labels: { severity: warning }

 # 5xx 比例过高
      - alert: CrawloHigh5xx
 expr: |
 rate(crawlo_response_status_code_5xx_total[5m])
 / clamp_min(rate(crawlo_response_status_code_success_count_total[5m]), 1) > 0.1
 for: 5m
 labels: { severity: warning }

 # 事件循环延迟过高（可能阻塞）
      - alert: CrawloEventLoopLag
 expr: crawlo_resource_eventloop_lag_ms_p99 > 200
 for: 3m
 labels: { severity: warning }

 # 内存持续增长（泄漏嫌疑）
      - alert: CrawloMemoryLeak
 expr: |
 delta(crawlo_memory_rss_mb[30m]) > 100
 for: 30m
 labels: { severity: warning }

 # Redis 断连（分布式模式）
      - alert: CrawloRedisDown
 expr: up{job="redis"} == 0
 for: 1m
 labels: { severity: critical }
```

## 4. 通知（钉钉/飞书/企微/邮件/短信）

Prometheus Alertmanager 负责触发，Crawlo 通知系统负责主动推送任务状态：

```python
# settings.py
NOTIFICATION_ENABLED = True
NOTIFICATION_CHANNELS = ["dingtalk"] # dingtalk | feishu | wecom | email | sms
DINGTALK_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=xxx"
```

代码内主动告警：

```python
from crawlo.extensions.notifications import send_crawler_alert

send_crawler_alert(
 title="【告警】解析规则疑似失效",
 content=f"列表页无产物持续 10 分钟: {spider.name}",
 channel=ChannelType.DINGTALK,
)
```

可用函数：`send_crawler_status` / `send_crawler_alert` / `send_crawler_progress`
（各渠道配置见 [通知指南](../guides/notification-guide.md)）。

> **职责分工**：Prometheus + Alertmanager 负责"指标异常"自动告警；
> Crawlo 通知系统负责"任务生命周期/业务事件"主动推送。两者互补，
> 不重复。

## 5. 运维检查清单

- [ ] `STATS_BACKEND='prometheus'` 且 `/metrics` 可被 Prometheus 拉取
- [ ] Grafana 有吞吐/错误/资源 3 类面板
- [ ] 告警规则已部署（吞吐骤降 / 异常突增 / 5xx / 事件循环 / 内存 / Redis）
- [ ] 通知渠道已配置且测试消息可到达
- [ ] 长跑压测（`scripts/stress_run.py`）基线已归档，作为泄漏判断依据

## 6. 排障速查

| 现象 | 查什么 | 常见原因 |
|---|---|---|
| 吞吐骤降 | `crawlo_response_status_code_4xx_total` / 站点 DOM | 被反爬 / 改版 |
| 重试突增 | `crawlo_retry_count_total` / 代理日志 | 代理失效 / 网络抖动 |
| 事件循环延迟高 | `eventloop_lag_ms_p99` / 堆栈 | 同步阻塞 / 连接池耗尽 |
| 内存持续涨 | `crawlo_memory_rss_mb` 曲线 | 对象泄漏（用 ResourceScope 定位） |
| 分布式无产出 | `crawlo_queue_size` / Redis 连接 | 队列积压 / Worker 失联 |
