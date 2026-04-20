# 智能背压系统 (Intelligent Backpressure System)

## 概述

Crawlo智能背压系统是一个**多维度自适应**的背压控制机制，基于队列、吞吐、性能三大维度综合评估系统负载，动态计算最优背压延迟，有效防止队列过载和系统崩溃。

## 核心特性

### 1. 多维度指标采集

系统实时采集三大类指标：

#### 队列指标
- **队列大小** (queue_size): 当前队列中的请求数量
- **使用率** (queue_usage_ratio): 队列使用百分比
- **增长速率** (queue_growth_rate): 队列每秒增长量

#### 吞吐指标
- **入队速率** (enqueue_rate): 每秒入队请求数
- **出队速率** (dequeue_rate): 每秒出队请求数
- **速率差** (rate_difference): 入队速率 - 出队速率

#### 性能指标
- **平均响应时间** (avg_response_time): 请求平均处理时间
- **超时率** (timeout_rate): 超时请求占比
- **成功率** (success_rate): 成功处理请求占比

### 2. 综合评分机制

基于三大维度指标计算0-100的综合评分：

```python
overall_score = (
    queue_score * 0.4 +        # 队列权重 40%
    throughput_score * 0.3 +   # 吞吐权重 30%
    perf_score * 0.3           # 性能权重 30%
)
```

### 3. 四级分类响应

| 级别 | 评分范围 | 背压状态 | 延迟范围 | 建议动作 |
|------|---------|---------|---------|---------|
| **Normal** | 0-50 | OFF | 0s | 正常运行 |
| **Warning** | 50-70 | ON | 0.3-1.0s | 记录日志，监控 |
| **Danger** | 70-85 | ON | 1.0-2.5s | 降低并发，告警 |
| **Critical** | 85-100 | ON | 2.5-5.0s | 暂停入队，紧急处理 |

### 4. 智能延迟计算

延迟计算公式：

```python
delay = (base_delay * adjustment + prediction) * smoothing

其中：
- base_delay: 基础延迟（根据级别）
- adjustment: 调整因子（根据细分指标）
  - 队列使用率 > 90%: 1.5倍
  - 速率差 > 50/s: 1.5倍
  - 超时率 > 30%: 1.3倍
  - 成功率 < 70%: 1.4倍
- prediction: 预测补偿（根据增长趋势）
- smoothing: 平滑处理（避免延迟剧烈波动）
```

### 5. 资源优化

#### CPU优化
- **延迟缓存机制**: 0.1秒TTL，避免重复计算
- **采样频率**: 1秒采集一次指标
- **实测效果**: 100次调用 < 1ms

#### 内存优化
- **可配置历史记录**: 默认1000条
- **响应时间记录**: 默认1000条
- **实测开销**: ~34KB (配置100条历史记录)

## 架构设计

### 核心组件

```
crawlo/backpressure/
├── __init__.py                  # 背压控制器（原有）
├── interfaces.py                # 策略接口（原有）
├── strategies.py                # 背压策略（原有）
├── metrics_collector.py         # 多维度指标采集器 ⭐新增
├── intelligent_calculator.py    # 智能延迟计算器 ⭐新增
└── monitor.py                   # 背压监控器 ⭐新增
```

### 组件职责

#### 1. BackpressureMetricsCollector (指标采集器)
- 实时采集队列、吞吐、性能三大维度指标
- 计算综合评分和级别
- 维护指标历史记录
- 提供外部调用接口（record_enqueue, record_dequeue, record_response）

#### 2. IntelligentBackpressureCalculator (智能延迟计算器)
- 根据综合评分计算基础延迟
- 根据细分指标计算调整因子
- 根据增长趋势预测补偿
- 平滑处理避免延迟波动
- 缓存机制优化CPU开销

#### 3. BackpressureMonitor (背压监控器)
- 实时监控背压状态变化
- 分级告警（warning/danger/critical）
- 维护告警历史记录
- 支持告警回调

## 配置说明

### 基础配置

```python
# 背压触发阈值（队列使用率）
MEMORY_BACKPRESSURE_RATIO = 0.5  # 50%触发

# 延迟范围
MEMORY_BACKPRESSURE_DELAY_BASE = 0.5  # 基础延迟0.5秒
MEMORY_BACKPRESSURE_DELAY_MAX = 5.0   # 最大延迟5.0秒
```

### 智能背压配置

```python
INTELLIGENT_BACKPRESSURE_ENABLED = True

INTELLIGENT_BACKPRESSURE_CONFIG = {
    # 指标采集配置
    'window_size': 30,              # 采样窗口（秒）
    'collect_interval': 1,          # 采集间隔（秒）
    
    # 指标权重配置（队列:吞吐:性能）
    'queue_weights': (0.4, 0.3, 0.3),
    
    # 评分阈值配置（警告, 危险, 严重）
    'score_thresholds': (50, 70, 85),
    
    # 延迟配置
    'base_delay': 0.5,              # 基础延迟（秒）
    'max_delay': 5.0,               # 最大延迟（秒）
    
    # 功能开关
    'enable_prediction': True,      # 启用预测补偿
    'enable_smoothing': True,       # 启用平滑处理
    
    # 监控配置
    'monitor_interval': 10,         # 监控检查间隔（秒）
    
    # 资源优化配置
    'max_history': 1000,            # 最大历史记录数
    'max_response_times': 1000,     # 最大响应时间记录数
    'cache_ttl': 0.1,               # 延迟计算缓存有效期（秒）
}
```

## 使用示例

### MemoryQueue自动集成

智能背压系统已自动集成到MemoryQueue，无需手动配置：

```python
from crawlo.queue.memory_queue import MemoryQueue

# 创建队列（智能背压默认启用）
queue = MemoryQueue(
    max_size=3000,
    backpressure_enabled=True,
    intelligent_backpressure=True,
    backpressure_config={
        'window_size': 30,
        'collect_interval': 1,
        'base_delay': 0.5,
        'max_delay': 5.0,
    }
)

await queue.open()

# 背压系统自动运行
# - 指标采集器每秒采集一次
# - 入队/出队时自动记录
# - 背压触发时自动延迟
```

### 手动使用指标采集器

```python
from crawlo.backpressure.metrics_collector import BackpressureMetricsCollector

# 创建采集器
collector = BackpressureMetricsCollector(
    window_size=30,
    collect_interval=1,
    queue_size_func=lambda: queue.size(),
    queue_max_size_func=lambda: queue.max_size
)

await collector.start()

# 记录操作
collector.record_enqueue()
collector.record_dequeue()
collector.record_response(
    response_time=0.5,
    is_timeout=False,
    is_success=True
)

# 获取当前指标
metrics = collector.get_current_metrics()
print(f"评分: {metrics.overall_score}")
print(f"级别: {metrics.level}")

await collector.stop()
```

### 手动使用智能延迟计算器

```python
from crawlo.backpressure.intelligent_calculator import IntelligentBackpressureCalculator

# 创建计算器
calculator = IntelligentBackpressureCalculator(
    metrics_collector=collector,
    base_delay=0.5,
    max_delay=5.0,
    enable_prediction=True,
    enable_smoothing=True,
    cache_ttl=0.1
)

# 计算延迟
delay = await calculator.calculate_delay()
print(f"建议延迟: {delay:.2f}s")
```

## 日志输出

### LogIntervalExtension背压日志

间隔日志中会显示背压状态：

```
# 背压关闭
[LogIntervalExtension] - INFO: Crawled 720 pages (at 70 pages/min), 
Got 18 items (at 2 items/min), Queue: 1450 pending, BP: off (48%)

# 背压激活
[LogIntervalExtension] - INFO: Crawled 854 pages (at 39 pages/min), 
Got 20 items (at 0 items/min), Queue: 1712 pending, BP: ON (0.74s, 57%)
```

**格式说明**：
- `BP: off (48%)`: 背压关闭，队列使用率48%
- `BP: ON (0.74s, 57%)`: 背压激活，延迟0.74秒，使用率57%

### 背压告警日志

当背压级别变化时，会记录告警日志：

```
[QueueManager] - INFO: 背压WARNING | 评分:53.0 | 队列:1560/3020(52%) | 速率差:120.0/s | 超时率:5.0%
[QueueManager] - INFO: 背压DANGER | 评分:75.0 | 队列:2100/3020(70%) | 速率差:150.0/s | 超时率:15.0%
```

## 真实场景验证

### 上市公司高管爬虫

**场景信息**：
- 爬虫名称: `senior_executives`
- 目标公司: 5515家
- 队列容量: ~3020

**背压触发过程**：

```
时间      速率     队列    使用率   BP状态    延迟
10:53:45  70/min  1450    48%     OFF       0s      ← 触发前
10:54:45  56/min  1560    52%     ON        0.57s   ← 首次触发
10:55:45  39/min  1635    55%     ON        0.65s
10:56:45  39/min  1712    57%     ON        0.74s
10:57:45  29/min  1772    59%     ON        0.80s
```

**效果验证**：
- ✅ 触发判断准确：48%时OFF，52%时ON
- ✅ 延迟动态调整：0.57s → 0.80s
- ✅ 降速效果显著：速率下降59%
- ✅ 系统稳定运行：无异常，无崩溃

## 性能测试

### 资源开销

| 指标 | 数值 | 说明 |
|------|------|------|
| **内存开销** | ~34KB | 配置100条历史记录 |
| **CPU开销** | < 0.1ms/次 | 100次调用 < 1ms |
| **缓存命中率** | > 90% | 0.1s TTL |

### 测试覆盖

运行完整测试：

```bash
python tests/test_intelligent_backpressure.py
```

**测试结果**：13/13 全部通过 ✅

测试覆盖：
1. ✅ 指标采集器基础功能
2. ✅ 多维度指标采集
3. ✅ 综合评分和级别判断
4. ✅ 智能延迟计算器
5. ✅ 延迟缓存优化
6. ✅ 背压监控器
7. ✅ MemoryQueue基础背压
8. ✅ MemoryQueue高负载
9. ✅ 动态负载变化
10. ✅ 资源开销测试
11. ✅ 边界条件测试
12. ✅ 异常处理测试
13. ✅ 配置参数测试

## 最佳实践

### 1. 配置调优

**高频爬虫** (>1000 req/s):
```python
INTELLIGENT_BACKPRESSURE_CONFIG = {
    'window_size': 60,              # 更长采样窗口
    'collect_interval': 2,          # 降低采集频率
    'max_history': 500,             # 减少历史记录
    'cache_ttl': 0.2,               # 增加缓存时间
}
```

**低频爬虫** (<100 req/s):
```python
INTELLIGENT_BACKPRESSURE_CONFIG = {
    'window_size': 30,              # 标准采样窗口
    'collect_interval': 1,          # 标准采集频率
    'max_history': 1000,            # 更多历史记录
    'cache_ttl': 0.1,               # 标准缓存时间
}
```

### 2. 监控建议

- 关注日志中的 `BP:` 状态
- 监控队列使用率趋势
- 观察背压延迟变化
- 设置告警阈值

### 3. 故障排查

**背压频繁触发**：
- 检查队列容量是否过小
- 提高并发处理能力
- 调整触发阈值

**背压不触发但队列满**：
- 检查背压是否启用
- 验证阈值配置
- 查看日志确认状态

**延迟过高**：
- 检查评分计算逻辑
- 调整权重配置
- 优化出队速率

## 版本历史

### v1.6.4 (2026-04-20)
- ✨ 新增多维度自适应背压系统
- ✨ 新增指标采集器（队列、吞吐、性能）
- ✨ 新增智能延迟计算器
- ✨ 新增背压监控器
- ✨ 新增延迟缓存优化
- ✨ 新增资源开销优化
- ✅ 完整测试覆盖（13/13通过）
- ✅ 真实场景验证（上市公司高管爬虫）

## 相关文件

- `crawlo/backpressure/metrics_collector.py` - 指标采集器
- `crawlo/backpressure/intelligent_calculator.py` - 智能延迟计算器
- `crawlo/backpressure/monitor.py` - 背压监控器
- `crawlo/queue/memory_queue.py` - MemoryQueue集成
- `crawlo/extension/log_interval.py` - 日志扩展
- `crawlo/settings/default_settings.py` - 默认配置
- `tests/test_intelligent_backpressure.py` - 完整测试
