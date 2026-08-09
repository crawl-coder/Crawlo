# 视频脚本：《Crawlo 分布式设计哲学——不是把内存队列换成 Redis 就完事》

> 配套文档：[distributed-philosophy.md](../design/distributed-philosophy.md)
> 技术细节：[distributed_architecture.md](../distributed_architecture.md)
> 目标时长：8~10 分钟
> 受众：用过 Scrapy / Celery、写过爬虫、想搞清楚"分布式爬虫到底和分布式函数调用有什么不一样"的工程师

---

## 总览结构（全片 5 段）

| 段 | 主题 | 时长 |
|---|---|---|
| ① 开场 | 一个问题：你以为的分布式爬虫，其实是错的 | 45s |
| ② 反设计 | Scrapy-Redis 和 Celery 到底哪不好 | 2min |
| ③ 四条哲学 | 正确性 / 无中心 / 三段式配置 / 两阶段故障检测 | 3min |
| ④ 三层架构 | Queue / Dedup / Coordination，每一层都不能少 | 2min |
| ⑤ 收尾 | 一句话记全 + 什么时候别用 | 1min |

---

## ① 开场（45s）

### 镜 1 — 标题卡

| 画面 | 旁白 |
|---|---|
| 深色背景 + 大标题：**《分布式爬虫不是把内存队列换成 Redis List》**；副标题：Crawlo 分布式设计哲学 | （沉稳男声）"很多人第一次做分布式爬虫，想的都是：把 Scrapy 里的 `deque` 换成 Redis `LPUSH / BRPOP`，不就完事了？**做完上线三天就后悔。**" |

### 镜 2 — 三种用户踩坑场景（快剪 3 个 gif）

| 画面 | 旁白 |
|---|---|
| gif 1：`crawlo run spiderA` 跑完 → 第二天复盘发现少抓了 10% 的 URL，Worker 崩溃过一次，没任何错误信息 | "坑一：Worker 崩了一次，**在途的请求就永久丢了**——因为 `BRPOP` 拿出来就算 Redis 不管了，你本地进程也没了。一周下来相当于随机丢一批数据。" |
| gif 2：3 个 Worker 同时启动 → 每个人都执行 `start_requests` → dedup 里瞬间涌进 3 万条重复指纹，Redis 控制台 QPS 狂飙 | "坑二：3 台机器一起 `start_requests`，大家都在生成种子 URL，最后靠 dedup SET 兜住——CPU 和带宽先烧一波，再全部扔掉。" |
| gif 3：一次网络抖动 500ms → Worker 被踢下线 → 另一个 Worker 回收重放 → 两边同一条请求都 ACK 前写 DB → MySQL 主键冲突日志刷屏 | "坑三：网络抖了一下就误判 Worker 挂了，结果**两边同时处理同一条消息**。数据库唯一键报错刷屏，你还得翻日志看有没有漏。" |

### 镜 3 — 抛出问题（画面定格 3 秒）

| 画面 | 旁白 |
|---|---|
| 屏幕中央白色大字：**"分布式爬虫的正确性，从来不是靠换存储介质，而是靠把单机里的不变量，显式搬到 Redis 里重新实现一遍。"** | "今天我们用 Crawlo 的设计思路告诉你：为什么分布式爬虫**不等于**把内存队列换成 Redis List，为什么 Scrapy-Redis 和 Celery 都不是最优选，以及 Crawlo 的四条设计原则 + 三层架构到底解决了什么。" |

---

## ② 反设计：Scrapy-Redis 和 Celery 到底哪不好（2min）

### 镜 4 — Scrapy-Redis 经典架构图（一张扁平图）

| 画面 | 旁白 |
|---|---|
| 左侧 Redis List `crawlo:requests` → 箭头从 LPUSH 进，3 个 Worker 各自 BRPOP。每个 Worker 旁边写："取完就丢"，Redis 上打一个大红叉：❌ **没有 Pending List**。 | "先看 Scrapy-Redis。它的架构非常朴素：Redis List 当队列，LPUSH 进、BRPOP 出。问题有三—— |
| | **第一，没 Pending Entry List。** 消息拿出来以后 Redis 侧就不记得了。Worker OOM 杀掉？消息永久丢。跑一周丢一批，你根本不知道丢了哪些。 |
| | **第二，没 Consumer Group。** 三个 Worker 都在 BRPOP 抢，Redis 不知道谁拿了哪条消息，**自然也没法回收超时未 ACK 的任务**。 |
| | **第三，种子生成没有锁。** 要么单独跑一个外部 publisher（这就是单点 Master），要么所有 Worker 同时 `start_requests`，靠 dedup SET 兜着——这是浪费，不是架构。" |

### 镜 5 — Celery 架构图（Broker / Result Backend / Worker）

| 画面 | 旁白 |
|---|---|
| 上方 "Celery Broker / Result Backend"，下方 Worker 池，任务是 `send_email() / resize_image()` 这种小函数。旁边并列 Crawlo 的任务：`Request{headers, cookies, callback, meta, depth=27}` 对比。 | "再看 Celery。很多公司想复用现成 Celery 集群，结果削足适履。为什么？因为 Celery 从根上就是**面向函数调用的调度器**： |
| | 任务是 `def add(a, b)` 这种小函数；生命周期秒级；产出是一个 return value。而爬虫任务——一个 Request 对象就带 headers、cookies、callback、meta、深度；生命周期分钟~小时级；更关键的是，**一条 Request 处理完会产出 N 条新 Request，递归无穷无尽**。 |
| | 把爬虫切成一个个函数调用，等于把 Engine 里的背压、连接池复用、per-domain 队列、Playwright 上下文**全部扔掉**。这不叫分布式，这叫拆碎了再粘起来。" |

### 镜 6 — 总结表（全屏对比表）

| 画面 | 旁白 |
|---|---|
| 三列表：需求 / Scrapy-Redis / Celery。勾叉快速扫过：不丢消息？× / ✓；种子只生成一次？× / ✓；跨 Worker Dedup？✓ / ×；故障回收？× / ✓；协调退出？× / ×；死信？× / ✓ | "一张表对比：**不丢在途消息** Scrapy-Redis 是 ×；**跨 Worker Dedup** Celery 是 ×；**协调退出**两者都 ×。都不完美。" |

---

## ③ 四条设计哲学（3min，核心段）

### 镜 7 — 总纲卡

| 画面 | 旁白 |
|---|---|
| 四个大字分四角：**正确性 · 无中心 · 三段式 · 两阶段**。中间小字：Crawlo Distributed — 4 Principles。 | "所以 Crawlo 怎么选？四条设计哲学，一条一条说。" |

### 镜 8 — 原则一：正确性 > 性能（5 格时间线动画）

| 画面 | 旁白 |
|---|---|
| 时间线 5 个节点：①消息在 Stream → ②Worker 消费（PEL 记录）→ ③Worker 下载中（仍 PEL）→ ④Worker 崩 → ⑤XAUTOCLAIM 回收重新入队。每个节点打一个"不丢 ✓"。最右加一个死信箭头：stream:failed。 | "原则一：**正确性 > 性能**。长驻爬虫一周崩一次返工的成本，远比单小时多抓 30% 数据贵。所以 Crawlo 宁可慢一点也要做到： |
| | 不丢在途消息（靠 Stream PEL + XAUTOCLAIM）；不重生成种子（靠 SETNX + 续期 + 死锁检测）；**至少一次**语义靠 ACK/XDEL 原子化；死信走 `stream:failed` 永不丢，留 CLI 手动排查。 |
| | 这里唯一承认的风险是**重复消费**：Worker 写完 MySQL 但 ACK 前崩 → 消息会被回收重放。但数据库唯一键兜底，不会产生脏数据——**这是幂等的最后一道防线。**" |

### 镜 9 — 原则二：无中心 Worker（图：对等节点）

| 画面 | 旁白 |
|---|---|
| 4 个完全一样的 Worker 方块围一圈，中间是一个 Redis 方块。每个 Worker 框里都写着：WorkerRegistry / Heartbeat / FailoverManager（9 个组件同款）。上方标题：No Master, No Scheduler, No Leader Election Everywhere。 | "原则二：**无中心 Worker，只有一个 Redis 状态中心。** 很多框架一上来就搞三种角色 Master/Scheduler/Worker——运维第一反应就是：**Master 挂了我找谁？** |
| | Crawlo 反其道而行：**所有 Worker 完全对等。** 只要能连上 Redis，`crawlo run <spider>` 就加入集群；`crawlo cluster state / reset / pause / resume / shutdown` 全是直接写 Redis key，不用找 Master。部署成本就是一个 Redis，公司 SRE 都熟。 |
| | Leader 选举只在一个地方临时用：**所有 Worker idle 后决定是不是可以一起关**——SET NX PX 就能做，不用 Raft、不用 etcd。" |

### 镜 10 — 原则三：三段式配置（左侧 1 行代码 → 右侧爆炸式默认值）

| 画面 | 旁白 |
|---|---|
| 左半屏：`RUN_MODE = 'distributed'` 一行。点击后右半屏爆炸出 10 行默认配置：`QUEUE_TYPE=redis_stream`、`FILTER_CLASS=AioRedisFilter`、`CONCURRENCY=16`、`IDLE_TIMEOUT=120`、`DELIVERY_COUNT_LIMIT=5`、`CONSUMER_IDLE_TIMEOUT=90s`、`FAILOVER_CHECK_INTERVAL=15s`、`AUTO_CLEAR_SHUTDOWN=True`… | "原则三：**配置就是三段式。不要让用户猜。** Celery 要写 10+ 行 broker_url / acks_late / prefetch_multiplier 才能跑稳？Crawlo 里你只需要一行——`RUN_MODE = 'distributed'`。 |
| | 这一行背后自动切到 Redis Stream、AioRedisFilter、RedisDedupPipeline，并给故障恢复、死信、协调退出全部上合理默认值。如果你手贱改了 `QUEUE_TYPE=redis` 忘了改 RUN_MODE？QueueManager 直接给你自动升级成 `redis_stream`，还打一行 warning 告诉你——**用户不需要理解 List vs Stream 的区别。**" |

### 镜 11 — 原则四：两阶段故障检测（动画：suspect 30s）

| 画面 | 旁白 |
|---|---|
| 上方 heartbeat 心跳条 15s 一跳。突然断流 → 红条标记 suspect（左：90s 过期）；30s 后确认 → DistributedLock 持锁（只允许 1 个 Worker 执行）→ XAUTOCLAIM 回收 → deregister。中间用虚线框标：STATUS_STOPPING → 豁免，不回收。 | "原则四：**故障检测必须两阶段，别把网络抖动当 Worker 崩。** 太敏感抖一下就回收 → 重放 → 两边写脏；太迟钝真崩了等 10 分钟 → 用户以为任务结束了。 |
| | Crawlo 的方案：Phase 1 心跳 90s 过期先标 **suspect**，**什么都不做**；Phase 2 suspect 再挂 30s 才确认真崩了。之后抢一个 DistributedLock，保证同一时刻**只有一个 Worker** 做 XAUTOCLAIM 回收，避免惊群。 |
| | 还有一个细节：优雅退出的 STATUS_STOPPING 是**豁免**的，不然你 Ctrl+C 停 Worker 会被误判崩溃，任务被抢回去重放。这是很多分布式框架生产环境踩了好多年才补的一个判断。" |

---

## ④ 三层架构：Queue / Dedup / Coordination（2min）

### 镜 12 — 三层叠图（从上到下滚动揭示）

| 画面 | 旁白 |
|---|---|
| 三层堆叠架构图：<br>Layer 3 Coordination（WorkerRegistry / Heartbeat / Failover / DynamicConfig / PubSub）<br>Layer 2 Dedup（AioRedisFilter + RedisDedupPipeline，两个 Redis SET）<br>Layer 1 Queue（Redis Stream / Pending Entry List / XAUTOCLAIM）<br>每一层都是独立可开关的。 | "很多人理解分布式爬虫只有一层'队列'。Crawlo 是**三层独立的能力**，每一层都不能少。" |

### 镜 13 — Layer 1 Queue：Stream 不是 List（两张图对比）

| 画面 | 旁白 |
|---|---|
| 左：Redis List：`LPUSH → BRPOP`，画一条消息从队列里消失，旁边 × 没 PEL。<br>右：Redis Stream：`XADD id=152698481` → `XREADGROUP GROUP workers consumer-1 >`，除了把消息给 consumer-1，还在 PEL（Pending Entry List）登记一笔；然后 `XACK` 才移除 PEL。底部列 5 条命令：XADD/XREADGROUP/XACK/XDEL/XAUTOCLAIM。 | "Layer 1 Queue：为什么是 Stream 不是 List？因为 Stream 自带消息 ID、自带 Consumer Group、**自带 Pending Entry List**——这才是故障回收的物理基础。BRPOP 取完就忘，Stream 取完会一直记得'谁拿了消息多久没 ACK'，90s 后还没 ACK 就可以被 XAUTOCLAIM 收走。" |

### 镜 14 — Layer 2 Dedup：请求 + 条目双 SET

| 画面 | 旁白 |
|---|---|
| 请求在入队前经 AioRedisFilter（`dedup:request SET`），命中就不入；条目在 pipeline 经 RedisDedupPipeline（`dedup:item SET`）命中就 drop。中间文字：**"双重兜底 = 防重放 + 防重复指纹漏判"**。 | "Layer 2 Dedup：很多团队上线后发现 DB 里全是重复行，就是这层没搞分布式。Crawlo 做两次——**请求去重**在 enqueue 之前，先看是不是别的 Worker 已经见过同 URL；**条目去重**在 pipeline 最末尾，ACK 前崩溃重放的也直接 drop。双保险之后才写 MySQL。" |

### 镜 15 — Layer 3 Coordination（9 个组件，每一个点亮对应功能）

| 画面 | 旁白 |
|---|---|
| 9 格宫格：WorkerRegistry、HeartbeatDaemon、DistributedLock、FailoverManager、ProgressReport、DynamicConfig、ClusterMessenger（PubSub+Key 双通道）、Leader Epoch（临时）、Control State（pause/resume/shutdown）。每个点亮时对应一小段动画：<br>Heartbeat → 15s ± 20% 波形；<br>Failover → 120s 进度条；<br>Pub/Sub → 闪电立即；Key → 存盘图。 | "Layer 3 Coordination：**这一层大部分框架根本没有，但缺了就运维痛苦。** Queue + Dedup 解决'能不能跑'；Coordination 解决'跑完能不能停、能不能动态改限速、加新 Worker 是不是零配置、空集群 shutdown 状态残留能不能一键 reset'。 |
| | Crawlo 里它有 9 个组件，其中最有意思的是配置同步的**双通道设计**：Pub/Sub 即时生效，但会丢消息；Redis Key 持久化兜底，重连也不会漏 shutdown。结合起来才稳。" |

### 镜 16 — 三档 RUN_MODE（渐进阶梯）

| 画面 | 旁白 |
|---|---|
| 阶梯图三档：<br>1 档 standalone → 标注：本地开发 / 5k URL / 0 Redis 依赖<br>2 档 协作模式 → 标注：单 Worker 持久化断点 / 多 Worker 共享 dedup / 不启 Heartbeat Failover<br>3 档 distributed → 标注：生产深爬 / 严格故障回收 / 即插即用扩缩容。 | "顺带一提：Crawlo 不是只有单机和分布式两档，而是**三档渐进式**。standalone 本地跑、协作模式（standalone + QUEUE_TYPE=redis_stream）用来做断点续爬持久化、distributed 才是严格故障回收 + 协调退出。很多团队要的只是'重启后能接着抓'，不想搞心跳日志——直接停在协作模式就行，别上 distributed。" |

---

## ⑤ 收尾：一句话记忆点 + 不要强行分布式（1min）

### 镜 17 — 权衡表（全屏，高亮 3 处）

| 画面 | 旁白 |
|---|---|
| 表格：选择 / 代价。其中高亮三行：<br>1. 消息语义：至少一次 + 幂等 / 放弃精确一次<br>2. 去重：enqueue 前 + pipeline 内双保险 / 两次 Redis RTT<br>3. 故障回收：心跳+PEL 双条件（~120s最坏） / 只靠 Stream idle 无法检测"心跳活着但业务死" | "最后看几个关键取舍。最重要的一点：我们**没有追求精确一次**——精确一次在纯 Redis 下要 2PC，复杂度爆炸；退一步'至少一次 + dedup + 唯一键幂等'是 99% 场景里最合理的工程选择。 |
| | 还有一个不直观的：故障回收不靠纯 Stream idle，而是叠加心跳 suspect。因为真实世界里有一种 GC 挂死但 heartbeat 线程还在发包的僵尸 Worker。纯 Stream idle 永远不回收。" |

### 镜 18 — 什么时候不该用分布式（× 清单）

| 画面 | 旁白 |
|---|---|
| 4 条 × 图标：<br>❌ < 5k URL 的小任务（内存队列更快）<br>❌ 单机 24h 内能跑完的（协作模式就够）<br>❌ 一个域名占 99% 请求（per-domain 节流单 Worker 更稳）<br>❌ IP + UA 强绑定登录态（多 Worker 互踢下线） | "以及四条**不要强行分布式**的信号：URL 少于 5k？用 standalone；单机一天能跑完？用协作模式做持久化断点；流量全部集中在同一个大域名？单机节流更准；cookie 绑 IP 绑 UA？要么单 Worker、要么先搞 Cookie 池 + 代理池。 |
| | 这些情况下硬上 distributed，除了日志噪音和配置复杂度，你什么也得不到。" |

### 镜 19 — 总结卡 + 引导链接

| 画面 | 旁白 |
|---|---|
| 居中大字：<br>**"Crawlo 分布式 = 把单机 Engine 里自然成立的不变量，变成 Redis 里显式维护的状态。没什么魔法，只是不偷懒。"**<br>下方小字：<br>docs/design/distributed-philosophy.md · docs/distributed_architecture.md<br>代码入口：crawlo/cluster/coordinator.py · queue/backends/redis_stream.py · commands/cluster.py | "一句话记住：**Crawlo 分布式不是多了什么魔法，而是把单机版 Engine 里'由 Python 解释器保证成立'的不变量——队列不丢、去重有效、种子一个、不脑裂——变成 Redis 里面显式维护的状态。**<br>完整文档和代码入口在屏幕下方，欢迎点赞收藏转发，下一期我们讲 Crawlo 里最反直觉的一个模块——**AioRedisFilter + BloomFilter 双重去重到底怎么选**。再见。" |

---

## 附：制作要求

- 字体：标题用 Inter / 思源黑体 Heavy；正文用 Regular；字号对比 ≥ 2.5
- 配色：深色（#0B1020）底 + Crawlo 品牌色青蓝（#20D3D3）作强调 + 暖黄（#FFC857）作警告
- 动画节奏：
  - 反设计段（镜 4-6）节奏稍快，每一个 ❌ 出现时伴随短促震动感
  - 四条哲学段（镜 8-11）每段一条字幕打大，停留 2s
  - 三层架构段（镜 12-15）逐层出，每层停留 5s，配合旁白
- 代码块高亮：
  - 出现 Redis 命令（XADD/XREADGROUP/XACK/XAUTOCLAIM）时用红色关键字
  - 出现配置（`RUN_MODE = 'distributed'`）时用青色高亮赋值号右侧
- 背景音乐：低鼓点、偏科技感，音量 -20dB 人声完全压住；转场处短暂推高再压回

