# 10 个 Worker 实战：Crawlo 分布式爬取 1,851 页全记录

> 一台机器不够？加机器。代码？不用改。今天就加 10 个。

---

## 测试目标

用一个真实的生产场景，验证 Crawlo 分布式爬虫的核心能力：

- 10 个 Worker 并行协作
- Redis Stream + Consumer Group 任务分发
- 双 Stream 优先级路由（高优/普通）
- ACK 语义 + XACK 确认
- 种子去重（只有一个 Worker 生成 start_requests）
- 跨 Worker 去重 + 死信队列
- Leader 协调退出 + MySQL 批量入库

---

## 测试配置

```python
# settings.py
from crawlo.config import CrawloConfig

config = CrawloConfig.distributed(
    project_name='ofweek_distributed',
    redis_host='127.0.0.1',
    redis_port=6379,
    concurrency=12,         # 每个 Worker 12 并发
    download_delay=1.0,     # 请求间隔 1 秒
)

# Pipeline + MySQL
PIPELINES = {
    'crawlo.pipelines.MySQLPipeline': 400,
}
MYSQL_HOST = '127.0.0.1'
MYSQL_USER = 'crawlo'
MYSQL_PASSWORD = 'crawlo123'
MYSQL_DB = 'crawlo_deployer'
MYSQL_TABLE = 'ofweek_news'
MYSQL_BATCH_SIZE = 100
MYSQL_USE_BATCH = True
```

| 参数 | 值 |
|------|----|
| 目标网站 | ee.ofweek.com |
| 列表页数 | **1,851** |
| 预估总任务 | ~37,000（1,851 列表页 + 约 35,000 详情页） |
| Worker 数 | **10** |
| 每 Worker 并发 | 12 |
| 总并发力 | **120** |
| 任务队列 | Redis Stream + Consumer Group |
| 存储 | MySQL（crawlo_deployer.ofweek_news） |
| 去重 | Redis Set |

---

## 测试流程

```
1. 清空 Redis（FLUSHALL，16 个 db 全部清零）
2. 清空 ofweek_news 表（确保干净起点）
3. 启动 run_10_workers.py → 10 个子进程，间隔 2 秒错峰
4. 每个 Worker 自动注册、启动心跳、加入 Consumer Group
5. 观察任务分发和消费进度
6. 等待全部完成，收集统计
```

### 启动命令

```bash
cd examples/ofweek_distributed
python run_10_workers.py
```

### Worker 启动脚本

```python
WORKER_COUNT = 10
for i in range(WORKER_COUNT):
    p = subprocess.Popen([sys.executable, 'run.py'])
    processes.append(p)
    time.sleep(2)  # 错峰启动
```

---

## Redis 数据结构

测试中 Redis 自动创建了多类 Key：

```
crawlo:{project}:{spider}:stream:tasks          ← 普通优先级 Stream
crawlo:{project}:{spider}:stream:tasks:high     ← 高优 Stream（priority < 0）
crawlo:{project}:{spider}:stream:failed         ← 死信队列
crawlo:{project}:{spider}:registry:workers      ← HASH Worker 注册表
crawlo:{project}:{spider}:registry:heartbeats   ← ZSET 心跳
crawlo:{project}:{spider}:lock:leader           ← Leader 选举锁
crawlo:{project}:{spider}:dedup:request         ← SET 去重指纹
crawlo:{project}:{spider}:seed:generator        ← 种子生成器互斥锁
```

---

## Worker 注册表

10 Worker 全部注册，运行期间 Consumer Group 实时状态：

```
consumers: 10         ← 全部加入
pending:   ~2,800     ← in-flight
lag:      ~1,000      ← 等待消费
total:    36,947      ← 任务总量
```

Worker ID 格式为 `{hostname}-{pid}-{uuid[:8]}`，确保全局唯一：

```
Oscar-MacPro-6673-7ce406b0  (pending: 312)
Oscar-MacPro-6682-f5a3d2ab  (pending: 300)
Oscar-MacPro-6686-36bd09f0  (pending: 312)
Oscar-MacPro-6691-b1ef3b77  (pending: 300)
Oscar-MacPro-6701-6fa3e79f  (pending: 276)
Oscar-MacPro-6710-79cea06c  (pending: 288)
Oscar-MacPro-6723-40cea3ea  (pending: 276)
Oscar-MacPro-6725-6bf6d2c2  (pending: 276)
Oscar-MacPro-6727-7f165e4f  (pending: 264)
Oscar-MacPro-6739-6139ec43  (pending: 264)
```

每个 Worker 平均持有 ~286 个 pending 任务，与 12 并发 + 下载延迟相匹配。

---

## 去重验证

Redis SET 实际去重指纹数：

```bash
$ redis-cli SCARD crawlo:ofweek_distributed:of_week_distributed:dedup:request
36947     ← 请求去重指纹
$ redis-cli SCARD crawlo:ofweek_distributed:of_week_distributed:dedup:item
35096     ← Item 去重指纹
```

36,947 个唯一 URL 被调度，35,096 条数据写入 MySQL，去重率精确。

---

## Worker 日志采样

Worker 正在解析列表页并产出详情页任务：

```
[of_week_distributed] 在页面 .../CATList-2800-8100-ee-2.html 中找到 20 个条目
[of_week_distributed] 提取到详情页链接: .../ART-8300-2800-30567244.html, 标题: 如何鉴别苹果充电器真伪？
[of_week_distributed] 提取到详情页链接: .../ART-8300-2800-30567496.html, 标题: FORESEE新一代UFS 3.1高速闪存
[of_week_distributed] 提取到详情页链接: .../ART-8110-2801-30567483.html, 标题: 美国造芯背后的博弈
```

每个列表页约提取 20 条详情页链接，180 × 21 ≈ 3,780，与实际 3,775 吻合。

---

## 10 Worker 完成统计

所有 Worker 以 `reason: 'finished'` 正常退出。运行时间：15:34:56 → 15:57:02，**总耗时约 22 分钟**。

| Worker | items | 响应数 | pages/min | MySQL 入库 |
|--------|-------|--------|-----------|-----------|
| 1 | 3,495 | 3,707 | 168 | 3,495 |
| 2 | 3,509 | 3,710 | 168 | 3,509 |
| 3 | 3,477 | 3,670 | 167 | 3,477 |
| 4 | 3,536 | 3,740 | 170 | 3,536 |
| 5 | 3,523 | 3,710 | 169 | 3,523 |
| 6 | 3,528 | 3,710 | 169 | 3,528 |
| 7 | 3,529 | 3,710 | 170 | 3,529 |
| 8 | 3,506 | 3,680 | 169 | 3,506 |
| 9 | 3,491 | 3,650 | 167 | 3,491 |
| 10 | 3,502 | 3,660 | 168 | 3,502 |
| **合计** | **35,096** | **37,107** | **~168** | **35,096** |

---

## 结果总结

| 验证项 | 结果 | 状态 |
|--------|------|------|
| 10 Worker 启动 | 全部注册 + 加入 Consumer Group | ✅ |
| Stream 任务分发 | 36,947 任务入队，0 残留 | ✅ |
| ACK 语义 + XACK | 全部消费确认 | ✅ |
| 跨 Worker 去重 | 36,947 指纹共享，无重复爬取 | ✅ |
| MySQL 入库 | 35,096 条批量写入 | ✅ |
| 完成原因 | 10 个 Worker 全部 `finished`（协调退出） | ✅ |
| 死信队列 | 0 | ✅ |
| 负载均衡 | 3,491-3,536 items/Worker（极均衡） | ✅ |
| 总耗时 | ~22 分钟（1,326s） | ✅ |
| 平均速率 | ~168 pages/min / Worker | ✅ |
| 退出时间差 | Coordinator → 最后 Worker 退出 ≤ 24s | ✅ |

---

## 代码改动量

从单机到 10 Worker 分布式，**仅需改配置，爬虫代码零改动**：

```diff
- config = CrawloConfig.standalone()
+ config = CrawloConfig.distributed(
+     redis_host='127.0.0.1',
+     redis_port=6379,
+     concurrency=12,
+ )
```

---

*关注公众号，获取更多 Crawlo 技术干货和爬虫实战经验。*
