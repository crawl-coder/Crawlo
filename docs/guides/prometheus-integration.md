# Prometheus + Grafana 集成开发方案

> 为 Crawlo 添加原生 Prometheus 指标暴露和 Grafana 可视化能力。
> 状态：规划中 · 优先级：中 · 预估工时：2-3 天

> 本方案已对照 `crawlo/stats/backends.py`、`collector.py`、`interfaces.py`、
> `extension/memory_monitor.py`、实际统计 key 与 `setup.cfg` 逐项核对，
> 修正了初版中指标名错配、非法指标名崩溃、端口冲突、`clear()` 重复注册等问题。

---

## 目录

1. [背景与动机](#背景与动机)
2. [设计目标](#设计目标)
3. [整体架构](#整体架构)
4. [详细实现](#详细实现)
5. [框架埋点补充](#框架埋点补充)
6. [配置文件变更](#配置文件变更)
7. [依赖管理](#依赖管理)
8. [Grafana 看板](#grafana-看板)
9. [指标参考](#指标参考)
10. [文档计划](#文档计划)
11. [实施路线图](#实施路线图)
12. [验收标准](#验收标准)

---

## 背景与动机

### 现状

Crawlo 现有的监控体系由三部分组成：

| 组件 | 方式 | 定位 |
|------|------|------|
| `StatsBackend`（Memory / Redis / File） | 采集 → 存储 key-value 快照 | 爬虫运行结束时输出统计 |
| 内置扩展（MemoryMonitor / HealthCheck 等） | 定时 → 输出到日志 | 运行中状态监控 |
| 通知系统（钉钉 / 飞书 / 企微 / 邮件） | 事件驱动 → 推送告警 | 异常即时通知 |

这套组合在单机、低频率场景下够用。但在以下场景中存在明显缺口：

- **趋势不可见**：快照只告诉你"最终是多少"，看不到"怎么涨上来的"。并发从 100 涨到 500 的过程是线性的还是阶梯式的？内存是在 2 小时内缓慢泄漏还是最后 10 分钟突然飙升？这些信息快照不包含，Prometheus 时间序列天然能回答。
- **分布式下无法聚合**：10 个 worker 各自往内存/Redis 写统计，想看全局请求速率、队列积压、各节点健康状态，只能逐台登录。
- **与标准可观测性栈脱节**：大多数互联网公司已经标配 Prometheus + Grafana，Crawlo 的指标无法接入这个体系，意味着爬虫监控游离于公司统一的可观测平台之外。
- **接口注释与实现不一致**：`IStatsCollector`（`crawlo/interfaces.py:498`）注释写明"支持内存、Redis、Prometheus 等后端"，但 `prometheus` 后端实际不存在。

### 设计原则

1. **只做加法，不改现有架构**——`StatsBackend` 抽象（`crawlo/stats/backends.py:25`）+ 工厂模式（`StatsBackendFactory.from_settings()`）已预留扩展点，Prometheus 后端作为 `StatsBackend` 的一个实现接入，不改任何现有子类或 `StatsCollector` 接口。
2. **可选依赖**——`prometheus-client` 作为 `[monitoring]` extra，不增加核心包体积。
3. **与现有通知系统互补**——Prometheus 负责长期的拉模式可观测性，通知系统负责短平快的推模式告警，两者共存。
4. **健壮优先**——框架内部统计 key 形态多样（含 `/`、中文 reason、带点 hostname、字符串值），后端必须能优雅处理非法指标名与非数值，绝不能因为某条统计而拖垮爬虫。

---

## 设计目标

1. 实现 `PrometheusStatsBackend`，把框架内部所有数值类统计 key 自动映射为 Prometheus 指标（Counter / Gauge）
2. 内嵌 HTTP server 在指定端口暴露 `/metrics` 端点，支持端口自动分配避免多 worker 冲突
3. 支持 `spider`、`worker_id` 等标签，多 worker 场景下不冲突
4. 在 `setup.cfg` 新增 `[monitoring]` 可选依赖
5. 提供预置 Grafana Dashboard JSON，面板 PromQL 全部对齐真实生成的指标名
6. 提供完整的使用文档

---

## 整体架构

```
┌──────────────────────────────────────────────────────────┐
│                  Crawlo Engine                            │
│                                                          │
│  Spider → Middleware → Downloader → Pipeline              │
│              ↓ 统计写入                                    │
│         StatsCollector (crawler.stats)                    │
│              ↓                                            │
│  StatsBackendFactory.from_settings()                      │
│              ↓                                            │
│  ┌─────────────────────────────────────┐                  │
│  │   PrometheusStatsBackend            │  ← 新增          │
│  │                                     │                  │
│  │  inc_value → Counter                │                  │
│  │  set_value → Gauge (仅数值)          │                  │
│  │  labels: {spider, worker_id, ...}   │                  │
│  └──────────────┬──────────────────────┘                  │
│                 │ stdlib http.server (独立线程)            │
└─────────────────┼────────────────────────────────────────┘
                  │ GET /metrics
                  ▼
         ┌────────────────┐
         │  Prometheus     │  scrape interval: 15s
         │  Server         │
         └───────┬────────┘
                 │ PromQL
                 ▼
         ┌────────────────┐
         │  Grafana        │  导入 crawlo-dashboard.json
         │  Dashboard      │
         └────────────────┘
```

### 数据流

```
框架内部 inc_value / set_value 调用
        ↓
PrometheusStatsBackend 适配为 Counter / Gauge
   · inc_value  → Counter（累计型）
   · set_value  → Gauge（仅数值；字符串值如 reason/end_time 自动跳过）
        ↓
prometheus_client CollectorRegistry
        ↓
内嵌 HTTP server（prometheus_client.start_http_server，独立线程）
        ↓
Prometheus 定期 scrape（默认 15s）
        ↓
Grafana 查询 PromQL 展示面板
```

---

## 详细实现

### 文件：`crawlo/stats/prometheus_backend.py`（新增，约 180 行）

```python
"""
Prometheus 统计后端

将 Crawlo 框架内部统计 key 自动映射为 Prometheus 指标，
并在指定端口暴露 /metrics 端点供 Prometheus Server 拉取。

使用方式：
    # settings.py
    STATS_BACKEND = 'prometheus'
    PROMETHEUS_METRICS_PORT = 9100      # 设为 0 则自动分配可用端口

依赖：
    pip install crawlo[monitoring]
    # 或 pip install prometheus-client>=0.19.0
"""
import atexit
import logging
import os
import re
import socket
from typing import Any, Dict, Optional

from crawlo.stats.backends import StatsBackend

try:
    from prometheus_client import Counter, Gauge, CollectorRegistry
    from prometheus_client.exposition import start_http_server
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

logger = logging.getLogger(__name__)

# 任何非 [a-zA-Z0-9_] 字符统一替换为下划线。
# 这能正确处理：斜杠、连字符、点（hostname）、括号、中文 reason 等。
_INVALID_CHARS = re.compile(r'[^a-zA-Z0-9_]')


def _sanitize_metric_name(key: str, prefix: str = "crawlo") -> str:
    """将框架 key 转换为合法 Prometheus 指标名。

    示例：
        'response_received_count'              -> 'crawlo_response_received_count'
        'downloader/exception_count'           -> 'crawlo_downloader_exception_count'
        'offsite_request_count/www.example.com'-> 'crawlo_offsite_request_count_www_example_com'
        'request_ignore_count/reason/状态码 403'-> 'crawlo_request_ignore_count_reason_403'
    """
    name = _INVALID_CHARS.sub('_', key.lower())
    while '__' in name:
        name = name.replace('__', '_')
    name = name.strip('_')
    return f"{prefix}_{name}"


class PrometheusStatsBackend(StatsBackend):
    """Prometheus 统计后端

    映射规则（简单且可预测，不做后缀猜测）：
        - inc_value(key, count)  -> Counter（累计型，key 首次出现时创建）
        - set_value(key, value)  -> Gauge（仅当 value 可转为 float；字符串值自动跳过）

    为什么不做后缀自动判型：
        框架 key 命名并不统一（如 'response_total_bytes' 用 inc_value，
        'avg_response_time_ms' 用 set_value），靠后缀猜类型既不可靠也无必要——
        调用方已通过选择 inc_value / set_value 表达了语义。
    """

    def __init__(
        self,
        prefix: str = "crawlo",
        port: int = 9100,
        labels: Optional[Dict[str, str]] = None,
        registry: Optional[CollectorRegistry] = None,
    ):
        if not PROMETHEUS_AVAILABLE:
            raise ImportError(
                "prometheus-client is required for PrometheusStatsBackend.\n"
                "Install: pip install crawlo[monitoring]"
            )

        self._prefix = prefix
        self._labels = labels or {'spider': 'default', 'worker_id': 'default'}
        self._registry = registry or CollectorRegistry()

        # 指标对象缓存；值为 None 表示该 key 因指标名非法被跳过
        self._counters: Dict[str, Optional[Counter]] = {}
        self._gauges: Dict[str, Optional[Gauge]] = {}
        # 并行值缓存：用于 get_value / max_value / min_value，
        # 避免访问 prometheus_client 内部 _value 私有 API
        self._counter_values: Dict[str, float] = {}
        self._gauge_values: Dict[str, float] = {}

        # 启动 HTTP server（port=0 时由系统分配可用端口）
        self._httpd = None
        self._port = port
        try:
            self._httpd = start_http_server(port, registry=self._registry)
            # 解析实际监听端口（port=0 时为系统分配的临时端口）
            # start_http_server 返回 WSGIServer 本身，兼容可能存在的 wrapper
            srv = getattr(self._httpd, 'server', self._httpd)
            if hasattr(srv, 'server_address'):
                self._port = srv.server_address[1]
            logger.info(
                f"Prometheus metrics endpoint started on "
                f"http://0.0.0.0:{self._port}/metrics "
                f"(requested={port}, labels={self._labels})"
            )
        except OSError as e:
            logger.error(f"Failed to start Prometheus HTTP server on port {port}: {e}")
            raise

        atexit.register(self.close)

    def _label_names(self):
        return list(self._labels.keys())

    def _get_or_create_counter(self, name: str, key: str) -> Optional[Counter]:
        if name not in self._counters:
            try:
                self._counters[name] = Counter(
                    name, f'Auto-generated from "{key}"',
                    self._label_names(), registry=self._registry,
                )
            except ValueError:
                # 指标名仍不合法（理论上 _sanitize_metric_name 已处理，
                # 这里作为兜底），跳过该 key，不影响爬虫运行
                logger.debug(f"Skip non-prometheus metric key (invalid name): {key}")
                self._counters[name] = None
        return self._counters[name]

    def _get_or_create_gauge(self, name: str, key: str) -> Optional[Gauge]:
        if name not in self._gauges:
            try:
                self._gauges[name] = Gauge(
                    name, f'Auto-generated from "{key}"',
                    self._label_names(), registry=self._registry,
                )
            except ValueError:
                logger.debug(f"Skip non-prometheus metric key (invalid name): {key}")
                self._gauges[name] = None
        return self._gauges[name]

    # ── StatsBackend 接口实现 ──────────────────────────

    def inc_value(self, key: str, count: int = 1) -> None:
        try:
            amount = float(count)
        except (TypeError, ValueError):
            return
        name = _sanitize_metric_name(key, self._prefix)
        metric = self._get_or_create_counter(name, key)
        if metric is not None:
            metric.labels(**self._labels).inc(amount)
        self._counter_values[name] = self._counter_values.get(name, 0.0) + amount

    def set_value(self, key: str, value: Any) -> None:
        # 仅数值映射为 Gauge；字符串值（reason / spider_name / end_time /
        # start_time / elapsed_time 等）跳过，Prometheus 不表达文本
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return
        name = _sanitize_metric_name(key, self._prefix)
        metric = self._get_or_create_gauge(name, key)
        if metric is not None:
            metric.labels(**self._labels).set(numeric)
        self._gauge_values[name] = numeric

    def get_value(self, key: str, default: Any = None) -> Any:
        name = _sanitize_metric_name(key, self._prefix)
        if name in self._gauge_values:
            return self._gauge_values[name]
        if name in self._counter_values:
            return self._counter_values[name]
        return default

    def get_stats(self) -> Dict[str, Any]:
        return {
            'metrics_endpoint': f'http://0.0.0.0:{self._port}/metrics',
            'port': self._port,
            'labels': self._labels,
            'counter_count': sum(1 for v in self._counters.values() if v is not None),
            'gauge_count': sum(1 for v in self._gauges.values() if v is not None),
        }

    def clear(self) -> None:
        """从注册表注销所有指标，避免清空后再次 inc/set 时报 'Duplicated timeseries'。"""
        for metric in list(self._counters.values()):
            if metric is not None:
                try:
                    self._registry.unregister(metric)
                except Exception:
                    pass
        for metric in list(self._gauges.values()):
            if metric is not None:
                try:
                    self._registry.unregister(metric)
                except Exception:
                    pass
        self._counters.clear()
        self._gauges.clear()
        self._counter_values.clear()
        self._gauge_values.clear()

    def max_value(self, key: str, value: Any) -> None:
        try:
            v = float(value)
        except (TypeError, ValueError):
            return
        name = _sanitize_metric_name(key, self._prefix)
        current = self._gauge_values.get(name)
        if current is None or v > current:
            self.set_value(key, v)

    def min_value(self, key: str, value: Any) -> None:
        try:
            v = float(value)
        except (TypeError, ValueError):
            return
        name = _sanitize_metric_name(key, self._prefix)
        current = self._gauge_values.get(name)
        if current is None or v < current:
            self.set_value(key, v)

    def append_value(self, key: str, value: Any) -> None:
        """Prometheus 指标模型不表达列表；忽略以避免对非数值调用 set_value 报错。"""
        logger.debug(f"append_value ignored for '{key}' (Prometheus models scalars only)")

    def close(self) -> None:
        """停止内嵌 HTTP server 线程并释放端口。"""
        httpd = getattr(self, '_httpd', None)
        if httpd is not None:
            shutdown = getattr(httpd, 'shutdown', None)
            if callable(shutdown):
                try:
                    shutdown()
                except Exception:
                    pass
            self._httpd = None
        logger.debug("PrometheusStatsBackend closed.")
```

### 关键设计决策说明

**1. 动态自动映射，不做后缀判型**

方案选择**动态映射**（key 到达时按规则创建指标）。映射规则刻意简单：`inc_value` → Counter，`set_value` → Gauge。不做后缀猜测的原因：框架 key 命名不统一（`response_total_bytes` 走 `inc_value`，`avg_response_time_ms` 走 `set_value`），调用方已通过方法选择表达了语义，后缀猜测既不可靠也无必要。

动态映射的好处：用户自定义中间件/管道产生的新 key 也能自动暴露，无需逐一枚举。

**2. 指标名清洗必须覆盖非 ASCII 与点号**

框架存在大量"带上下文"的 key，例如：

| 真实 key | 问题字符 |
|----------|---------|
| `request_ignore_count/reason/状态码 403 不在允许列表中 - 403` | 中文、空格、连字符 |
| `offsite_request_count/www.example.com` | 点号 |
| `downloader/exception_type_count/TimeoutError` | 斜杠 |
| `cost_time(s)` | 括号（且是字符串值，set_value 会跳过） |

若仅替换 `/ - 空格`，中文与点号仍会导致 `Counter()` 抛 `ValueError`，进而拖垮爬虫。因此用正则 `[^a-zA-Z0-9_]` 统一替换为下划线，并对创建过程做 `try/except ValueError` 兜底。

**3. HTTP server：独立线程，端口可自动分配**

采用 `prometheus_client.start_http_server`（基于 stdlib `http.server`，独立线程），对 asyncio 事件循环无干扰。支持 `PROMETHEUS_METRICS_PORT = 0` 由系统分配可用端口——**同一台机器跑多个 worker 时，每个 worker 必须用不同端口**，否则第二个 worker 会因端口占用 `OSError` 崩溃。实际端口会写入日志与 `get_stats()`。

**4. `get_value` 用并行值缓存，不碰私有 API**

不使用 `metric._value.get()` 这类 prometheus_client 内部 API（跨版本可能失效），而是维护 `_counter_values` / `_gauge_values` 两份并行缓存，`inc_value` / `set_value` 时同步更新。`max_value` / `min_value` 也基于此缓存比较。

**5. `clear()` 必须注销指标**

`StatsCollector.clear_stats()` 会调用 `backend.clear()`。若只清空本地 dict 而 `CollectorRegistry` 仍保留指标对象，之后同名 key 再创建会报 `Duplicated timeseries`。因此 `clear()` 通过 `registry.unregister()` 真正移除指标。

**6. `close()` 真正停 server**

调用 `start_http_server` 返回对象的 `shutdown()` 停止 HTTP 线程、释放端口，避免同进程内重建 Crawler（如测试）时端口持续占用。

**7. labels 设计**

默认带 `spider` 和 `worker_id` 两个标签：

- `spider`：区分同一进程内的不同爬虫（取 `PROJECT_NAME`）
- `worker_id`：分布式模式下区分不同节点。取值优先级：`WORKER_ID` 配置 → `{hostname}-{pid}`（保证每进程唯一，不依赖默认不存在的 `HOSTNAME` 环境变量）

用户可通过 `PROMETHEUS_LABELS` 配置额外标签（如 `env`、`dc`）。

---

## 框架埋点补充

> **重要前提**：Prometheus 后端只能暴露"已经写入 `crawler.stats` 的指标"。
> 经核查，以下两类关键运行时指标**当前并未写入统计后端**，需要补充埋点才能在看板中展示。

### 1. 内存指标

`MemoryMonitorExtension`（`crawlo/extension/memory_monitor.py`）的 `_monitor_loop()` 已经周期性计算了 `process_rss`、`process_percent`、`thread_count`，但只用于日志输出，未写入 stats。在该循环中追加几行即可：

```python
# crawlo/extension/memory_monitor.py  _monitor_loop() 内，_log_memory_status(...) 之后
try:
    self.crawler.stats.set_value('memory_rss_mb', round(process_rss / 1024 / 1024, 2))
    self.crawler.stats.set_value('memory_percent', round(process_percent, 2))
    self.crawler.stats.set_value('thread_count', thread_count)
except Exception:
    pass
```

注意：该扩展受 `MEMORY_MONITOR_ENABLED` 开关控制（默认 `False`）。启用 Prometheus 监控时建议同时开启内存监控，或另起一个轻量周期任务写入这三项指标。

### 2. 队列大小指标

队列当前大小由队列对象通过 `await queue.size()` 异步获取，未写入 stats。建议在已有的周期性统计扩展（`LogIntervalExtension`）的定时回调中追加：

```python
# 在周期性回调中（已持有 crawler 引用）
try:
    engine = getattr(crawler, '_engine', None)
    if engine and getattr(engine, '_queue', None):
        size = await engine._queue.size()
        crawler.stats.set_value('queue_size', size)
except Exception:
    pass
```

这两处改动都很小，且对现有逻辑无侵入（都是追加 `set_value` 调用）。若不补充，对应的两块 Grafana 面板将为空——这是预期的，不算缺陷。

---

## 配置文件变更

### 文件：`crawlo/settings/default_settings.py`

在统计相关区块新增：

```python
# ---- 统计后端 ----
# 可选值: 'memory'（默认）| 'redis' | 'file' | 'prometheus'
STATS_BACKEND = 'memory'

# ---- Prometheus 监控（STATS_BACKEND='prometheus' 时生效） ----
PROMETHEUS_METRICS_PORT = 9100     # 指标暴露端口；设为 0 则自动分配可用端口
PROMETHEUS_LABELS = {}             # 额外标签，如 {'env': 'production', 'dc': 'shanghai'}
```

> 说明：选择 `STATS_BACKEND = 'prometheus'` 本身即表达了暴露端口的意图，不再额外设 `PROMETHEUS_ENABLED` 双开关。如需防止端口被外部访问，请在防火墙/安全组层面限制，而非靠框架开关。

### 文件：`crawlo/stats/backends.py`（修改 `StatsBackendFactory.from_settings()`）

在 `from_settings()` 末尾的 `elif backend_type == 'file':` 之后新增分支：

```python
elif backend_type == 'prometheus':
    try:
        from crawlo.stats.prometheus_backend import PrometheusStatsBackend
    except ImportError as e:
        get_logger(cls.__name__).warning(
            f"prometheus-client not installed, fallback to memory backend: {e}"
        )
        return MemoryStatsBackend()

    import os
    import socket
    worker_id = settings.get('WORKER_ID') or f"{socket.gethostname()}-{os.getpid()}"
    return PrometheusStatsBackend(
        prefix=settings.get('STATS_PREFIX', 'crawlo'),
        port=settings.get_int('PROMETHEUS_METRICS_PORT', 9100),
        labels={
            'spider': settings.get('PROJECT_NAME', 'crawlo'),
            'worker_id': worker_id,
            **settings.get_dict('PROMETHEUS_LABELS', {}),
        },
    )
```

同时把 `'prometheus'` 加入 `StatsBackendFactory._backends` 字典的文档/校验（可选，`from_settings` 已独立处理）。

> `get_bool` / `get_int` / `get_dict` 方法均存在于 `crawlo/settings/setting_manager.py:354-389`，可直接使用。

---

## 依赖管理

### 文件：`setup.cfg`

在 `[options.extras_require]` 中新增，并加入 `all`：

```ini
monitoring =
	prometheus-client>=0.19.0

all =
	bitarray>=1.5.3
	PyExecJS>=1.5.1
	pymongo>=3.10.1
	redis-py-cluster>=2.1.0
	%(database)s
	%(render)s
	%(stealth)s
	%(mcp)s
	%(db-all)s
	%(monitoring)s
```

### 使用方式

```bash
# 安装（推荐）
pip install crawlo[monitoring]

# 或单独安装
pip install "prometheus-client>=0.19.0"
```

安装后验证：

```bash
python -c "from prometheus_client import Counter, Gauge, start_http_server; print('OK')"
```

---

## Grafana 看板

### 文件：`assets/grafana/crawlo-dashboard.json`（新增）

预置一张 Grafana Dashboard，所有 PromQL 均对齐框架真实生成的指标名。
（`crawlo_` 前缀由 `STATS_PREFIX` 控制，默认即 `crawlo`。）

| 面板 | PromQL | 类型 | 数据来源 |
|------|--------|------|---------|
| 请求速率 | `rate(crawlo_response_received_count[1m])` | 时间序列 | `response_received_count`（Counter） |
| 状态码分布 | `increase(crawlo_response_status_code_success_count[5m])` / `_3xx` / `_4xx` / `_5xx` 堆叠 | 堆叠柱状 | `response_status_code/*`（Counter） |
| 成功率 | `crawlo_item_successful_count / clamp_min(crawlo_item_successful_count + crawlo_item_discard_count, 1)` | Stat | `item_*_count`（Counter） |
| 采集速率 | `rate(crawlo_item_successful_count[5m])` | 时间序列 | `item_successful_count`（Counter） |
| 内存趋势 | `crawlo_memory_rss_mb` | 时间序列 | 需框架埋点（见上文） |
| 并发水位 | `crawlo_concurrency_limit` + `crawlo_max_concurrent_seen` 叠加 | 面积图 | `concurrency_*`（Gauge，close 时写入） |
| 平均响应时间 | `crawlo_avg_response_time_ms` | 时间序列 | `avg_response_time_ms`（Gauge，close 时写入） |
| 队列积压 | `crawlo_queue_size` | 时间序列 | 需框架埋点（见上文） |
| 重试/异常率 | `rate(crawlo_retry_count[5m])` + `rate(crawlo_downloader_exception_count[5m])` | 时间序列 | `retry_count` / `downloader/exception_count` |
| 各 worker 请求数 | `sum by(worker_id)(crawlo_response_received_count)` | 柱状图 | 同上，按 worker_id 标签聚合 |

看板配置特性：

- **模板变量**：`spider` 和 `worker_id` 作为下拉筛选器，由一个面板控制全看板
- **刷新间隔**：默认 30s，与 Prometheus scrape interval 对齐
- **时间范围**：默认最近 6 小时，支持拖拽选择
- **告警联动**：面板阈值可一键转换为 Grafana Alerting 规则

> 注意：`concurrency_limit` / `max_concurrent_seen` / `avg_response_time_ms` 由 `StatsCollector.close_spider()` 在爬虫结束前写入（`crawlo/stats/collector.py:120-127`），因此这些面板主要反映运行结束时的快照值，而非全程实时。如需全程实时，可参考"框架埋点补充"一节，在周期回调中持续 `set_value`。

Dashboard JSON 通过标准的 Grafana 模型生成（`__inputs` + `__requires` 模板语法），导入时自动提示数据源选择。

---

## 指标参考

以下为框架内部**真实存在**的统计 key（按模块归类），Prometheus 指标名 = `crawlo_` + key 经清洗后的形式。

### 计数类（`inc_value` → Counter）

| 框架 key | 来源 | 说明 |
|----------|------|------|
| `response_received_count` | `middleware/middleware_manager.py:260` | 收到的响应总数 |
| `response_status_code/{code}` | 同上:262 | 按状态码计数（如 `response_status_code/200`） |
| `response_status_code/3xx` `4xx` `5xx` | 同上:264-268 | 非 2xx 分段聚合 |
| `response_status_code/success_count` | `middleware/response_code.py:120` | 2xx 成功计数 |
| `response_status_code/error_count` | 同上:122 | 错误状态码计数 |
| `response_total_bytes` | 同上:125 | 响应总字节 |
| `item_successful_count` | `extension/log_stats.py:42` | 成功产出 Item |
| `item_discard_count` | 同上:50 | 丢弃 Item |
| `request_scheduler_count` | 同上:64 | 调度请求（不含重试） |
| `retry_count` | `middleware/retry.py:168` | 重试次数 |
| `downloader/exception_count` | `core/engine.py:505` | 下载异常总数 |
| `downloader/exception_type_count/{Type}` | 同上:506 | 按异常类型计数 |
| `downloader/failed_urls_count` | 同上:508 | 失败 URL 数 |
| `request_ignore_count` | `middleware/request_ignore.py:54` | 被忽略请求 |
| `request_ignore_count/reason/{reason}` | 同上:59 | 按原因（可能含中文） |
| `offsite_request_count` | `middleware/offsite.py:98` | 域外请求 |
| `offsite_request_count/{hostname}` | 同上:104 | 按域名（含点号） |
| `download_error/{ExceptionName}` | `middleware/middleware_manager.py:250` | 下载错误分类 |
| `dedup/dropped_count` `new_count` 等 | `pipelines/base_pipeline.py` | 去重管道统计 |
| `{filter}/filtered_count` | `filters/__init__.py:112` | 过滤器计数 |

### 瞬时值类（`set_value` → Gauge，仅数值）

| 框架 key | 来源 | 说明 |
|----------|------|------|
| `concurrency_limit` | `stats/collector.py:120` | 并发上限（close 时写入） |
| `max_concurrent_seen` | 同上:121 | 峰值并发（close 时写入） |
| `concurrency_utilization` | 同上:122 | 并发利用率 |
| `avg_response_time_ms` | 同上:127 | 平均响应时间（ms） |
| `items_per_minute` | 同上:198 | 每分钟 Item 数 |
| `pages_per_minute` | 同上:199 | 每分钟页面数 |
| `memory_rss_mb` | 需新增埋点 | 进程 RSS（MB） |
| `queue_size` | 需新增埋点 | 当前队列大小 |

### 被跳过的 key（字符串值，不映射）

`reason`、`spider_name`、`start_time`、`end_time`、`elapsed_time`、`cost_time(s)` 等为字符串，`set_value` 会自动跳过，不会产生 Prometheus 指标。这是预期行为——Prometheus 不表达文本。

---

## 文档计划

### 新建文件：`docs/guides/prometheus-integration.md`

即本文件的"用户向"精简版（去掉设计论证，保留操作步骤）：

```
# Prometheus + Grafana 集成指南

## 快速开始（5 分钟验证）
1. pip install crawlo[monitoring]
2. settings.py: STATS_BACKEND = 'prometheus'; PROMETHEUS_METRICS_PORT = 9100
3. 运行爬虫
4. curl http://localhost:9100/metrics 验证指标输出

## 完整部署（docker-compose）
services:
  crawlo-worker   # 你的爬虫容器
  prometheus      # 镜像: prom/prometheus
  grafana         # 镜像: grafana/grafana

## Grafana 看板导入
1. Grafana → + → Import
2. 上传 assets/grafana/crawlo-dashboard.json
3. 选择 Prometheus 数据源 → 保存

## 多 worker 部署
- 每台机器多 worker 时设 PROMETHEUS_METRICS_PORT = 0 自动分配端口
- worker_id 标签自动取 WORKER_ID 或 hostname-pid

## 生产建议
- 端口安全（防火墙规则、反向代理认证）
- scrape interval 调优
- Alertmanager 告警规则示例
- 与现有通知系统并存的最佳实践
```

### 目录索引更新

在 `docs/guides/index.md` 中新增条目：

```markdown
- [Prometheus + Grafana 集成](prometheus-integration.md)：原生 Prometheus 指标暴露与 Grafana 可视化
```

---

## 实施路线图

### Phase 1：核心后端（1 天）

| 任务 | 产出 |
|------|------|
| 实现 `PrometheusStatsBackend` | `crawlo/stats/prometheus_backend.py` |
| 指标名正则清洗 + 非法名兜底 | 内置在 backend 中 |
| 内嵌 HTTP server（支持 port=0） | 同上 |
| 添加 `StatsBackendFactory` 分支 | 修改 `crawlo/stats/backends.py` |

### Phase 2：配置 + 依赖（0.5 天）

| 任务 | 产出 |
|------|------|
| 添加默认配置项 | 修改 `crawlo/settings/default_settings.py` |
| 添加 `[monitoring]` extra 并入 `all` | 修改 `setup.cfg` |

### Phase 3：框架埋点 + Grafana + 文档（0.5 天）

| 任务 | 产出 |
|------|------|
| 内存指标埋点 | 修改 `crawlo/extension/memory_monitor.py` |
| 队列大小埋点 | 修改周期统计扩展 |
| 导出 Grafana Dashboard JSON | `assets/grafana/crawlo-dashboard.json` |
| 编写集成指南 | `docs/guides/prometheus-integration.md`（用户向） |
| 更新文档索引 | 修改 `docs/guides/index.md` |

### Phase 4：测试与验证（0.5 天）

| 任务 | 细节 |
|------|------|
| 单元测试 | `inc_value` → Counter 映射正确 |
| 单元测试 | `set_value` 对数值建 Gauge、对字符串跳过 |
| 单元测试 | 含中文/点号的 key 不抛异常 |
| 单元测试 | `clear()` 后再 inc 不报 Duplicated timeseries |
| 单元测试 | `port=0` 自动分配并能 curl 到指标 |
| 集成测试 | 启动爬虫，`curl /metrics` 验证输出格式 |
| 集成测试 | 多 worker 同机，端口不冲突、worker_id 标签区分 |

---

## 验收标准

1. `STATS_BACKEND = 'prometheus'` 配置后，爬虫运行时 `curl localhost:9100/metrics` 返回合法的 Prometheus text 格式输出
2. 输出包含框架核心统计指标：`crawlo_response_received_count`、`crawlo_item_successful_count`、`crawlo_retry_count`、`crawlo_downloader_exception_count` 等
3. 含中文 reason、带点 hostname 的 key 不会导致爬虫崩溃（被清洗或跳过）
4. `set_value` 写入字符串值（如 `reason`）时静默跳过，不报错
5. 多 worker 同机部署时端口不冲突（`PROMETHEUS_METRICS_PORT = 0`），指标通过 `worker_id` 标签区分
6. `clear()` 后继续 `inc_value` 同名 key 不报 `Duplicated timeseries`
7. `close()` 释放 HTTP server 线程与端口
8. `pip install crawlo[monitoring]` 自动安装 `prometheus-client`
9. Grafana 导入看板后，对应真实指标的 8/10 面板数据正常展示（内存与队列面板依赖框架埋点）
10. 不修改任何现有的 `StatsBackend` 子类或 `StatsCollector` 接口
11. `STATS_BACKEND = 'memory'` 的现有用户不受任何影响

---

> 计划版本：v1.8.0（目标）
> 维护者：待定
