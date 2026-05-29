# 分布式系统边界与极端场景测试计划

## 测试环境

| 配置项 | 值 |
|--------|-----|
| Python | 3.10+ |
| Redis | 5.0+（推荐 7.x 测试 XAUTOCLAIM） |
| Worker 数量 | 1~10（视场景调整） |
| 测试爬虫 | `examples/ofweek_distributed`（max_page=200） |
| 日志目录 | `examples/ofweek_distributed/logs/` |

### 关键配置默认值

```python
CLUSTER_HEARTBEAT_INTERVAL = 15       # 心跳间隔（秒）
CLUSTER_WORKER_TIMEOUT = 90            # Worker 超时判定（秒）
CLUSTER_FAILOVER_CHECK_INTERVAL = 30   # 故障检测周期（秒）
DISTRIBUTED_WORKER_IDLE_TIMEOUT = 120  # Worker 空闲退出兜底（秒）
delivery_count_limit = 3               # 最大投递次数
suspect_timeout = 30                   # suspect 二次确认等待（秒）
```

---

## 一、正常操作测试（基线）

### TC-1.1：单 Worker 正常爬取并退出

| 项目 | 内容 |
|------|------|
| **目标** | 验证单 Worker 从启动到任务完成再到协调退出的完整流程 |
| **步骤** | 1. 启动 1 个 Worker<br>2. 等待爬取完成<br>3. 观察退出日志 |
| **预期** | - 所有页面爬取成功<br>- Leader 选举自己<br>- Coordinated shutdown 触发<br>- exit code 0 |
| **验证点** | `Coordinated shutdown: all tasks complete`、`Cluster shutdown complete`、`reason='finished'` |

### TC-1.2：5 Worker 多节点负载均衡

| 项目 | 内容 |
|------|------|
| **目标** | 验证多 Worker 任务分配均匀性与去重正确性 |
| **步骤** | 1. 清理 Redis<br>2. 启动 5 个 Worker（间隔 5s）<br>3. 等待全部完成 |
| **预期** | - 各 Worker 处理量差异 < 20%<br>- 跨 Worker 零重复<br>- 总 Item 数 = 预期值<br>- Leader 触发协调退出 |
| **验证点** | 各 Worker 日志中 `Item processed` 数量 + URL 去重检查 |

### TC-1.3：Leader 重新选举

| 项目 | 内容 |
|------|------|
| **目标** | 验证 Leader 锁过期后其他 Worker 能接任 |
| **步骤** | 1. 启动 3 个 Worker<br>2. 等 Leader 锁建立后，手动删除 Redis 锁 Key<br>3. 观察 Leader 行为 |
| **预期** | - 原 Leader 续期锁失败后降级为普通 Worker<br>- 另一个 Worker 获取锁成为新 Leader<br>- 协调退出仍正常触发 |
| **验证点** | 日志中 Leader 锁切换过程 |

---

## 二、Worker 生命周期测试

### TC-2.1：Worker 正常注册与注销

| 项目 | 内容 |
|------|------|
| **目标** | 验证 Worker 注册、心跳、注销生命周期 |
| **步骤** | 1. 启动 1 个 Worker<br>2. 查看 Redis 中的注册表<br>3. Worker 正常退出后检查 |
| **预期** | - Worker 启动后 HSET 注册 + ZADD 心跳<br>- Worker 退出后 HDEL 注销 + ZREM 心跳<br>- 无残留 Key |
| **Redis Key** | `crawlo:{project}:{spider}:registry:workers`<br>`crawlo:{project}:{spider}:registry:heartbeats` |

### TC-2.2：Worker 优雅退出（Ctrl+C）

| 项目 | 内容 |
|------|------|
| **目标** | 验证 Worker 收到 SIGINT 后的优雅退出流程 |
| **步骤** | 1. 启动 2 个 Worker<br>2. 爬取中按 Ctrl+C 中断 Worker 1<br>3. 观察 Worker 1 和 Worker 2 的行为 |
| **预期** | - Worker 1 执行 `_shutdown_cluster()` 流程<br>- Worker 1 注销自身、释放 Leader 锁、Drain 在途任务<br>- Worker 2 继续运行，任务通过 failover 回收 |

### TC-2.3：Worker 进程 Kill -9 强制杀死

| 项目 | 内容 |
|------|------|
| **目标** | 验证 Worker 被强制杀死后 failover 能正常回收任务 |
| **步骤** | 1. 启动 3 个 Worker<br>2. 爬取中 taskkill /F 杀死 Worker 2<br>3. 观察 failover 行为 |
| **预期** | - Worker 2 注册信息残留<br>- ~90s 后 failover 标记 Worker 2 为 suspect<br>- ~120s 后二次确认，XCLAIM 回收 Worker 2 的 pending 任务<br>- Worker 2 注销 |
| **验证点** | 日志 `Detected worker X as suspect`、`Claimed N pending tasks from worker X` |

---

## 三、故障转移测试

### TC-3.1：Single Worker 崩溃 + 任务丢失恢复

| 项目 | 内容 |
|------|------|
| **目标** | 验证单 Worker 崩溃后 pending 任务被其他 Worker 正确回收 |
| **步骤** | 1. 启动 2 个 Worker<br>2. 爬取过程中强制杀死 Worker A<br>3. 观察 Worker B 是否回收任务并完成 |
| **预期** | - Worker B 在 90~120s 内检测到 Worker A 死亡<br>- Worker B XCLAIM 回收 Worker A 的 pending 任务<br>- 所有任务最终完成，无遗漏 |
| **限界条件** | 任务投递超过 `delivery_count_limit=3` 次后进入死信队列 |

### TC-3.2：投递超限进入死信队列

| 项目 | 内容 |
|------|------|
| **目标** | 验证超过 `delivery_count_limit` 的任务进入死信队列 |
| **步骤** | 1. 设置 `delivery_count_limit=1`<br>2. 启动 1 个 Worker<br>3. 强制杀死 Worker（让任务未 ACK）多次 |
| **预期** | - 任务因投递次数超限进入 `stream:failed`<br>- `get_dead_letter_stats()` 返回正确计数<br>- 通过 `retry_dead_letters()` 可重新投递 |
| **验证点** | 检查 `crawlo:{ns}:stream:failed` Stream 长度 |

### TC-3.3：所有 Worker 同时崩溃

| 项目 | 内容 |
|------|------|
| **目标** | 验证极端情况下数据持久性 |
| **步骤** | 1. 启动 3 个 Worker<br>2. 处理大量任务时同时强制杀死所有 Worker<br>3. 重新启动新 Worker |
| **预期** | - 所有已入队但未 ACK 的任务保留在 Stream PENDING 列表<br>- 重新启动后 XCLAIM 回收所有 pending 任务继续处理<br>- 去重过滤器防止 URL 被多次处理 |
| **验证点** | XLEN + XPENDING 验证数据完整性 |

---

## 四、Leader 协调退出测试

### TC-4.1：Leader 正常协调退出

| 项目 | 内容 |
|------|------|
| **目标** | 验证 Leader 在所有任务完成后广播 shutdown |
| **步骤** | 1. 启动 3 个 Worker<br>2. 等待所有任务完成 |
| **预期** | - Leader 检测到 `_start_requests_source is None`<br>- `async_idle()` 返回 True<br>- 所有 Worker 的 `tasks_processing == 0`<br>- broadcast shutdown → 所有 Worker 退出 |
| **验证点** | `Coordinated shutdown: all tasks complete` 日志 + 进程退出 |

### TC-4.2：Leader 被杀死后协调退出仍工作

| 项目 | 内容 |
|------|------|
| **目标** | 验证 Leader 死亡后新 Leader 仍能协调退出 |
| **步骤** | 1. 启动 3 个 Worker（各间隔 5s）<br>2. 任务快完成时杀死 Leader（第一个启动的 Worker）<br>3. 观察剩余 Worker |
| **预期** | - 剩余 Worker 中有一个成为新 Leader<br>- 新 Leader 检测到条件满足后广播 shutdown |
| **验证点** | 新 Leader 的 `Coordinated shutdown` 日志 |

### TC-4.3：DISTRIBUTED_WORKER_IDLE_TIMEOUT 兜底机制

| 项目 | 内容 |
|------|------|
| **目标** | 验证 Leader 失效时 Worker 靠超时兜底退出 |
| **步骤** | 1. 设置 `DISTRIBUTED_WORKER_IDLE_TIMEOUT=60`<br>2. 启动 2 个 Worker<br>3. 任务完成后手动删除 Leader 锁和相关 Key<br>4. 观察 Worker 行为 |
| **预期** | - Leader 协调退出未触发（因为 Key 被删除导致广播失效）<br>- Worker 在持续空闲 60s 后自行退出 |
| **验证点** | `Worker idle timeout reached` 日志 |

### TC-4.4：DISTRIBUTED_COORDINATED_SHUTDOWN_ENABLED=False

| 项目 | 内容 |
|------|------|
| **目标** | 验证关闭协调退出时仅靠超时兜底退出 |
| **步骤** | 1. 设置 `DISTRIBUTED_COORDINATED_SHUTDOWN_ENABLED=False`<br>2. 设置 `DISTRIBUTED_WORKER_IDLE_TIMEOUT=60`<br>3. 启动 1 个 Worker，任务完成后观察 |
| **预期** | - Leader 协调退出 loop 不启动<br>- 60s 空闲超时后 worker 退出 |
| **验证点** | 无 `Coordinated shutdown` 日志，仅有 `Worker idle timeout` |

---

## 五、Redis 故障测试

### TC-5.1：Redis 连接中断

| 项目 | 内容 |
|------|------|
| **目标** | 验证 Redis 不可达时 Worker 的行为 |
| **步骤** | 1. 启动 1 个 Worker<br>2. 爬取中停止 Redis 服务<br>3. 观察 Worker 行为 |
| **预期** | - Worker 在尝试出队/心跳时抛出 Redis 连接异常<br>- `_failover_loop` 在 try/except 中捕获异常，每 5s 重试<br>- Pub/Sub 监听循环异常后 2s 自动重连<br>- Redis 恢复后 Worker 继续工作 |
| **风险点** | 爬虫可能因请求下载超时 + Redis 异常双重失败而卡死 |

### TC-5.2：Redis 高延迟（网络抖动）

| 项目 | 内容 |
|------|------|
| **目标** | 验证 Redis 响应慢（>500ms）时集群不误判 |
| **步骤** | 1. 通过 tc/防火墙模拟 Redis 端口 50ms~2s 延迟<br>2. 启动 3 个 Worker |
| **预期** | - 心跳可能延迟但不应触发 suspect 误判<br>- suspect 二次确认机制（30s）过滤假阳性 |
| **验证点** | 无 `suspect` 误报日志 |

### TC-5.3：Redis 内存耗尽

| 项目 | 内容 |
|------|------|
| **目标** | 验证队列积压导致 Redis OOM 时的行为 |
| **步骤** | 1. 设置 Redis `maxmemory=10MB`<br>2. 启动超大爬取任务 |
| **预期** | - XADD 因 OOM 失败<br>- Stream 内建的 `MAXLEN` 修剪机制尽力控制内存<br>- Worker 入队操作抛出异常 |
| **验证点** | 观察日志中 OOM 相关错误及爬虫恢复行为 |

---

## 六、极端场景测试

### TC-6.1：种子 URL 数量极大（10 万级）

| 项目 | 内容 |
|------|------|
| **目标** | 验证大量种子 URL 入队时的性能 |
| **步骤** | 1. 爬虫 `start_urls` 生成 10 万个种子 URL<br>2. 启动 3 个 Worker |
| **预期** | - 入队速度不成为瓶颈<br>- 去重过滤器正确处理大量 URL<br>- 各 Worker 消费速率稳定 |
| **验证点** | 入队耗时、Stream 长度、去重 QPS |

### TC-6.2：单个详情页耗时极长（慢速网站）

| 项目 | 内容 |
|------|------|
| **目标** | 验证某个请求长时间未完成时不影响其他 Worker |
| **步骤** | 1. 在爬虫 parse 中间人为 sleep(300)<br>2. 启动 2 个 Worker |
| **预期** | - 慢请求不阻塞其他 Worker<br>- 队列中的其他任务正常被其他 Worker 消费<br>- 无任务丢失 |
| **验证点** | 其他 Worker 继续处理新任务，XPENDING 中只有慢任务 |

### TC-6.3：所有请求均失败（目标网站不可达）

| 项目 | 内容 |
|------|------|
| **目标** | 验证目标网站完全不可达时的退避和退出行为 |
| **步骤** | 1. 将 start_urls 设为不可达的域名<br>2. 启动 2 个 Worker |
| **预期** | - 所有请求因超时/连接错误失败<br>- RetryMiddleware 重试若干次后放弃<br>- 所有种子 URL 都已尝试（队列空）→ 触发协调退出<br>- 统计显示 `response_received_count = 0` |
| **验证点** | 日志中大量 Retry、最终 `Coordinated shutdown` 触发 |

### TC-6.4：爬虫动态生成无限 URL

| 项目 | 内容 |
|------|------|
| **目标** | 验证页面无限分页（`next_page` 永不为空）时 Leader 不触发退出 |
| **步骤** | 1. 爬虫 parse 中始终 yield 下一页<br>2. 启动 1 个 Worker |
| **预期** | - `_start_requests_source` 在初始种子入队后即变为 None<br>- 但因有无限 `next_page` 生成新请求，队列永不空<br>- Leader 检测 `async_idle()=False`，不广播 shutdown<br>- Worker 持续运行（或靠用户终止） |
| **验证点** | `conditions_met=False` 持续显示、Worker 不退出 |

---

## 七、竞态条件测试

### TC-7.1：两个 Worker 同时启动（同时争夺 Leader 锁）

| 项目 | 内容 |
|------|------|
| **目标** | 验证同时启动的多个 Worker 能否正确选举 Leader |
| **步骤** | 1. 清理 Redis<br>2. **同时**启动 2 个 Worker（间隔 < 0.1s） |
| **预期** | - 只有一个 Worker 获取到 Leader 锁（SETNX 原子性保证）<br>- 另一个 Worker 正常降级<br>- 任务处理正常 |
| **验证点** | Leader 锁只被一个 Worker 持有 |

### TC-7.2：Worker 退出竞态——Leader 锁刚释放时其他 Worker 检查

| 项目 | 内容 |
|------|------|
| **目标** | 验证 Leader 退出释放锁到新 Leader 接手之间的间隙无异常 |
| **步骤** | 1. 启动 3 个 Worker<br>2. 任务快完成时杀死 Leader<br>3. 观察锁切换过程 |
| **预期** | - 锁释放后最多 10s（`check_interval`）另一个 Worker 获取锁<br>- 间隙期间无重复广播或数据损坏 |
| **验证点** | 锁切换平滑、无重复 shutdown |

### TC-7.3：心跳和 failover 并发

| 项目 | 内容 |
|------|------|
| **目标** | 验证心跳更新与 failover 检测之间的时序竞争 |
| **步骤** | 1. 设置 `CLUSTER_HEARTBEAT_INTERVAL=30`，`CLUSTER_WORKER_TIMEOUT=30`（相同）<br>2. 启动 3 个 Worker |
| **预期** | - 心跳可能刚好在 timeout 阈值附近<br>- suspect 二次确认机制防止误判<br>- 不会出现活着的 Worker 被误杀 |
| **验证点** | 无 suspect 误报 |

---

## 八、监控与观测性测试

### TC-8.1：死信队列监控

```bash
# 查询死信统计
python -c "
import asyncio, redis.asyncio as r
async def main():
    c = r.from_url('redis://127.0.0.1:6379/0')
    stats = await c.xlen('crawlo:ofweek:zlzp_jobs_crawler:stream:failed')
    print(f'Dead letter queue length: {stats}')
    await c.aclose()
asyncio.run(main())
"
```

### TC-8.2：Redis Key 清理验证

```bash
# 检查所有 crawlo 开头的 Key
python -c "
import asyncio, redis.asyncio as r
async def main():
    c = r.from_url('redis://127.0.0.1:6379/0')
    keys = await c.keys('crawlo:*')
    for k in sorted(keys):
        ttl = await c.ttl(k)
        t = await c.type(k)
        print(f'{k.decode()} | type={t.decode()} | ttl={ttl}')
    await c.aclose()
asyncio.run(main())
"
```

---

## 九、测试优先级矩阵

| 测试用例 | 优先级 | 耗时估计 | 关键程度 | 说明 |
|---------|:------:|:--------:|:--------:|------|
| TC-1.1 单 Worker 正常流程 | P0 | ~2min | 必过 | 基线测试 |
| TC-1.2 5 Worker 负载均衡 | P0 | ~6min | 必过 | 核心功能 |
| TC-2.2 Worker Ctrl+C 退出 | P0 | ~3min | 必过 | 用户高频操作 |
| TC-3.1 Worker 崩溃 + 任务回收 | P0 | ~3min | 必过 | 分布式核心价值 |
| TC-4.1 Leader 协调退出 | P0 | ~5min | 必过 | 核心功能 |
| TC-1.3 Leader 重新选举 | P1 | ~3min | 重要 | Leader HA |
| TC-2.3 Kill -9 强制杀死 | P1 | ~3min | 重要 | 异常恢复 |
| TC-4.2 Leader 被杀后协调退出 | P1 | ~5min | 重要 | Leader HA |
| TC-3.2 死信队列 | P1 | ~3min | 重要 | 数据可靠性 |
| TC-3.3 所有 Worker 同时崩溃 | P1 | ~3min | 重要 | 极端恢复 |
| TC-5.1 Redis 连接中断 | P1 | ~3min | 重要 | 容错 |
| TC-5.2 Redis 高延迟 | P2 | ~3min | 一般 | 网络抖动容错 |
| TC-6.3 全部请求失败 | P2 | ~2min | 一般 | 边界情况 |
| TC-6.4 无限 URL 生成 | P2 | ~2min | 一般 | 边界情况 |
| TC-4.3 超时兜底退出 | P2 | ~3min | 一般 | 备用机制 |
| TC-4.4 关闭协调退出 | P2 | ~2min | 一般 | 配置验证 |
| TC-5.3 Redis OOM | P3 | ~5min | 低 | 极端资源耗尽 |
| TC-6.1 10 万种子 URL | P3 | ~10min | 低 | 大规模 |
| TC-6.2 单个请求超长 | P3 | ~5min | 低 | 边界情况 |
| TC-7.1/7.2/7.3 竞态条件 | P3 | ~5min | 低 | 时序验证 |
| TC-8.1/8.2 监控验证 | P3 | ~2min | 低 | 可观测性 |

> **P0**：核心功能，必须全过才能发布<br>
> **P1**：重要功能，建议全部通过<br>
> **P2**：边界场景，酌情测试<br>
> **P3**：极端/低概率场景，有时间再测

---

## 十、测试运行命令

### 启动 5 Worker 测试（5s 间隔）

```bash
cd examples/ofweek_distributed
python run_5_workers.py
```

### 手动启动单个 Worker

```bash
cd examples/ofweek_distributed
python run.py
```

### 清理 Redis

```bash
python -c "import asyncio,redis.asyncio as r;async def f():c=r.from_url('redis://127.0.0.1:6379/0');[await c.delete(k) for k in await c.keys('crawlo:*')];await c.aclose();asyncio.run(f())"
```

### 监控 Redis Key

```bash
# 每 10s 轮询 Key 数量
python -c "
import asyncio,redis.asyncio as r
async def f():
    c = r.from_url('redis://127.0.0.1:6379/0')
    while True:
        keys = await c.keys('crawlo:*')
        stats = {}
        for k in keys:
            t = await c.type(k)
            t = t.decode() if isinstance(t, bytes) else t
            stats[t] = stats.get(t, 0) + 1
        print(f'Keys: {len(keys)} | {stats}')
        await asyncio.sleep(10)
asyncio.run(f())
"
```
