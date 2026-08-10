# Redis 高可用与生产验证指南

> 覆盖四类生产验证：**Redis HA 实测 / 长跑稳定性 / 性能基准 / 故障注入**。
> 工具全部在 `scripts/` 下，可直接复跑并产出报告。

## 1. Redis Sentinel 高可用

### 架构

```text
 +------------------+
                |  Crawlo Worker   |
                |  (redis_stream)  |
 +--------+---------+
                         | Sentinel 感知 master
 +----------------+-----------------+
        |                |                 |
 sentinel-1 sentinel-2 sentinel-3 (26379, 法定 2/3)
        |                |                 |
 +-----v-----+ +-----v-----+
  |   master  |<---|  replica  |          (6379, 主从复制)
 +-----------+ +-----------+
```

### 启动与演练

```bash
cd scripts/redis_ha
docker compose up -d
python scripts/benchmark/mock_site.py --port 9300 # 终端 1
python scripts/redis_ha/failover_test.py # 终端 2
```

演练自动执行：启动 3 Sentinel + master + replica → 分布式爬虫持续抓取 →
`docker stop redis-master` → 断言 Sentinel 在阈值内提升 replica →
爬虫无中断、DLQ 不误报 → 输出报告。

### 实测记录（2026-08-10，本地 Docker）

```text
初始 master: 172.28.0.10:6379
触发: docker stop crawlo-redis-master（R3 完成后）
故障切换: 172.28.0.10 → 172.28.0.11（15.4s，含 5s down-after + 选举/同步）
爬虫 5 轮（R1–R5）全部 ok，故障切换窗口内 R4/R5 无中断、无重复、DLQ 无误报
```

> 已知坑：`docker stop` 必须用**完整容器名**`crawlo-redis-master`（短名静默失败）；
> Sentinel 7.x 需配置文件落盘（`sentinel.conf` 挂载），且不能用 `:ro`（Sentinel 要写状态）；
> 本地已有 Redis 占用 6379 时，master 端口映射改为 `6380:6379`。

### 生产配置

```python
REDIS_SENTINEL_URLS = ["redis://10.0.0.1:26379", "redis://10.0.0.2:26379", "redis://10.0.0.3:26379"]
REDIS_SENTINEL_SERVICE = "mymaster"
QUEUE_TYPE = "redis_stream"
```

## 2. 24 小时长跑稳定性

```bash
python scripts/benchmark/mock_site.py --port 9200 # 终端 1
python scripts/stress_run.py --rounds 8640 --interval 10 \
 --report /tmp/stress_24h.json # 终端 2（约 24h）
```

报告含：RSS 曲线、对象泄漏斜率（ResourceScope）、事件循环延迟、Redis 连接数、FD 数。
验收阈值：RSS 增长 < 200 MB、泄漏斜率 < 0.05/轮、延迟 P99 < 100 ms。
短验证：`--rounds 5 --interval 2`。

## 3. 性能基准

```bash
python scripts/benchmark/mock_site.py --port 9200 --delay-ms 20
python scripts/benchmark/benchmark.py --pages 100
```

同站点同并发对比 Crawlo 与 Scrapy（Scrapy 未装时自动跳过）。输出
req/s、延迟 P50/P95/P99、RSS。归档：`docs/releases/perf-vs-scrapy.md`。

## 4. 故障注入

```bash
python scripts/failure_inject.py --scenario redis-down --recover 5
python scripts/failure_inject.py --scenario network-partition --recover 5
```

预期行为：

| 故障 | 预期 | 验证点 |
|---|---|---|
| Redis 宕机 | 单机模式自动回退内存队列，任务不丢 | crawl 完成 |
| 网络分区 | 下载重试（默认 3 次），恢复后继续 | 统计 retry_count |
| Worker 崩溃 | 任务 XCLAIM/XAUTOCLAIM 回收 | 分布式演练 |
| 磁盘写满 | 管道写失败 → DLQ / 错误日志（需容器环境） | 文档记录 |

## 5. 演练记录模板

每次演练后把报告归档到 `docs/releases/stability-YYYY-MM-DD.md`：

```markdown
# 稳定性演练 2026-MM-DD

- 场景：Redis 故障切换 / 24h 长跑 / 基准 / 故障注入
- 结果摘要：
- 恢复时间：
- 发现的问题与修复：
```
