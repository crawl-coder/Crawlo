# 5 Worker 分布式测试

本文以 `examples/ofweek_distributed` 为例，演示如何启动 5 个 Worker 进行分布式爬取，
并验证负载均衡、去重效果和协调退出。

## 环境准备

```bash
# 确保 Redis 运行中
redis-cli ping

# 进入示例项目
cd examples/ofweek_districted

# 确认 max_page 配置（分布在式模式使用 Redis Streams，自动创建 Consumer Group）
```

## 启动脚本

项目已提供 `run_5_workers.py`，自动启动 5 个子进程，每个子进程运行 `run.py`。

```python
WORKER_COUNT = 5          # Worker 数量
time.sleep(5)              # 每个 Worker 间隔 5 秒启动
```

### 运行

```bash
cd examples/ofweek_distributed
python run_5_workers.py
```

输出示例：

```
============================================================
  5 Worker Distributed Test
  max_page=200, ~4000 Requests
  RUN_MODE=distributed, QUEUE_TYPE=redis_stream
============================================================

  Worker 1 started (PID=26428)
  Waiting 5s before next worker...
  Worker 2 started (PID=7284)
  Waiting 5s before next worker...
  Worker 3 started (PID=3372)
  ...
  All 5 workers started

  Worker 1 (PID=26428) exited with code 0
  Worker 2 (PID=7284) exited with code 0
  ...
  Test complete
```

### 手动启动（不依赖启动脚本）

也可以手动在多个终端启动：

```bash
# 终端 1
cd examples/ofweek_distributed
python run.py

# 终端 2（5 秒后）
python run.py

# 终端 3-5（依次间隔 5 秒）
python run.py
```

## 测试结果范例

### Worker 统计

| Worker | 运行时长 | Item | Pages/min | 启动时间 |
|--------|----------|:----:|:---------:|---------|
| Worker 1 | 323s | 814 | 164 | +0s |
| Worker 2 | 317s | 800 | 161 | +5s |
| Worker 3 | 313s | 780 | 159 | +10s |
| Worker 4 | 308s | 790 | 160 | +15s |
| Worker 5 | 303s | 810 | 161 | +20s |
| **合计** | **~5.3min** | **3,994** | **avg 161** | |

### 去重验证

5 个 Worker 共处理 **3,994 条 Item**，跨 Worker 检查 URL 唯一性：

```
Worker 1: 814 items, 814 unique  ✅
Worker 2: 800 items, 800 unique  ✅
...
Total:    3994 items, 3994 unique  ✅  零重复
```

> 分布式去重（`RedisDedupPipeline` + `AioRedisFilter`）确保同一个 URL
> 不会被多个 Worker 重复处理。

### 协调退出

Leader Worker（启动最早的 Worker 通过 SETNX 选举产生）
在检测到队列空 + 所有 Worker 空闲后自动广播 shutdown：

```
[Engine] WARNING: Coordinated shutdown: all tasks complete,
                  all workers idle, broadcasting shutdown signal
[DynamicConfig] WARNING: Cluster shutdown signal sent
[WorkerRegistry] INFO: Worker deregistered: ...
[Engine] INFO: Cluster shutdown complete: ...
```

## 各 Worker 日志位置

| 内容 | 位置 |
|------|------|
| Worker 日志（`run_5_workers.py` 自动生成） | `examples/ofweek_distributed/worker_{1..5}.log` |
| 爬虫日志（每个 Worker 自动创建） | `examples/ofweek_distributed/logs/zlzp_jobs_crawler_*.log` |

查看单个 Worker 统计：

```bash
# 统计 Worker 1 的处理量
grep "Item processed" logs/zlzp_jobs_crawler_*.log | wc -l

# 查看最终统计
grep "stats:" logs/zlzp_jobs_crawler_135248.log
```

## Redis Key 状态

运行期间可用 Redis CLI 查看：

```bash
# 查看所有 crawlo 相关 Key
redis-cli keys 'crawlo:*'

# 查看当前队列长度
redis-cli xlen crawlo:ofweek_distributed:of_week_distributed:stream:tasks

# 查看 Consumer Group 状态
redis-cli xinfo groups crawlo:ofweek_distributed:of_week_distributed:stream:tasks

# 查看已注册 Worker
redis-cli hgetall crawlo:ofweek_distributed:of_week_distributed:registry:workers

# 查看 Leader
redis-cli get crawlo:ofweek_distributed:of_week_distributed:cluster:leader
```

## 参数调整

```python
# run_5_workers.py
WORKER_COUNT = 10     # 增加到 10 个 Worker
time.sleep(3)          # 间隔改为 3 秒

# 蜘蛛本中调整任务量（of_week_distriduted.py）
max_page = 500        # 增加到 500 页
```
