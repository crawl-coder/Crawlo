# Crawlo 稳定性长跑报告

> 工具：`scripts/stress_run.py`（轮次压测：RSS / ResourceScope 对象斜率 / 事件循环延迟 / Redis 连接数）
> 验收标准（ROADMAP E2）：24h 后 RSS 增长 < 阈值、无泄漏告警、事件循环延迟 P99 达标。

## 状态

| 项目 | 状态 |
|---|---|
| 短跑验证 | ✅ 2026-08-24 通过（下表） |
| **24h 正式执行** | ⏳ 待发布窗口执行并回填 |

## 短跑实测（2026-08-24，本地）

```text
命令: python scripts/stress_run.py --rounds 6 --interval 2 --warmup 1 \
        --report /tmp/stress_short.json
结果: RSS 增长 13.3 MB | 泄漏斜率 {CrawlerProcess: 0.0, Crawler: 0.0}
      事件循环延迟 p50=0.016ms p95=0.034ms p99=0.034ms
```

结论：预热后对象计数零增长，短窗口内无资源泄漏迹象；RSS 首轮抬升属
解释器/连接池常驻开销，后续轮次平稳。

## 24h 正式执行（待回填）

```bash
# 建议在独立机器/容器执行，避免开发负载干扰采样
python scripts/stress_run.py --rounds 8640 --interval 10 --warmup 12 \
    --report /tmp/stress_24h.json
```

### 结果占位（执行后填写）

```text
执行日期：
轮次/间隔：8640 × 10s
RSS 起始 → 结束：
RSS 净增长：
泄漏斜率（CrawlerProcess / Crawler）：
事件循环延迟 p50 / p95 / p99：
Redis 连接数变化：
异常/告警记录：
结论（通过/不通过 + 依据）：
```

## 附：基准补充指标（v1.7.5 A5）

分布式模式每请求 Redis 命令数基线（`benchmark.py --distributed`，
2026-08-24 本地 11 请求冒烟）：**20.5 ops/request**。
该值是后续"入队管道化"优化（1.8+ 候选）的对照基线；优化目标为显著降低
该比值且不改变可靠性语义（SADD 去重与 XACK 均不可省略或合并到丢失语义）。
