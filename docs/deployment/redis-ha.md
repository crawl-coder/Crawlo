# Redis 高可用与生产验证指南

> 覆盖路线图 P4 四项：**Redis HA 实测 / 24h 长跑 / 性能基准 / 故障注入**。
> 工具全部在 `scripts/` 下，可直接复跑并产出报告。

## 1. Redis Sentinel 高可用（P4-E1）

### 架构

```text
                +------------------+
                |  Crawlo Worker   |
                |  (redis_stream)  |
                +--------+---------+
                         | Sentinel 感知 master
        +----------------+-----------------+
        |                |                 |
  sentinel-1        sentinel-2        sentinel-3   (26379, 法定 2/3)
        |                |                 |
  +-----v-----+    +-----v-----+
  |   master  |<---|  replica  |          (6379, 主从复制)
  +-----------+    +-----------+
```

### 启动与演练

```bash
cd scripts/redis_ha
docker compose up -d
python scripts/benchmark/mock_site.py --port 9300        # 终端 1
python scripts/redis_ha/failover_test.py                 # 终端 2
```

演练自动执行：启动 3 Sentinel + master + replica → 分布式爬虫持续抓取 →
`docker stop redis-master` → 断言 Sentinel 在阈值内提升 replica →
爬虫无中断、DLQ 不误报 → 输出报告。

### 生产配置

```python
REDIS_SENTINEL_URLS = ["redis://10.0.0.1:26379", "redis://10.0.0.2:26379", "redis://10.0.0.3:26379"]
REDIS_SENTINEL_SERVICE = "mymaster"
QUEUE_TYPE = "redis_stream"
```

## 2. 24 小时长跑稳定性（P4-E2）

```bash
python scripts/benchmark/mock_site.py --port 9200          # 终端 1
python scripts/stress_run.py --rounds 8640 --interval 10 \
    --report /tmp/stress_24h.json                          # 终端 2（约 24h）
```

报告含：RSS 曲线、对象泄漏斜率（ResourceScope）、事件循环延迟、Redis 连接数、FD 数。
验收阈值：RSS 增长 < 200 MB、泄漏斜率 < 0.05/轮、延迟 P99 < 100 ms。
短验证：`--rounds 5 --interval 2`。

## 3. 性能基准（P4-E3）

```bash
python scripts/benchmark/mock_site.py --port 9200 --delay-ms 20
python scripts/benchmark/benchmark.py --pages 100
```

同站点同并发对比 Crawlo 与 Scrapy（Scrapy 未装时自动跳过）。输出
req/s、延迟 P50/P95/P99、RSS。归档：`docs/releases/perf-vs-scrapy.md`。

## 4. 故障注入（P4-E4）

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
