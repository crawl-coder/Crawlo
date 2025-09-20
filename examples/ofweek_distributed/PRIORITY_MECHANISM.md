# Crawlo框架请求优先级机制详解

## 1. 概述

Crawlo框架的请求优先级机制遵循**priority值越小越优先**的原则，完全符合您的需求。

## 2. 优先级常量定义

```python
class RequestPriority:
    URGENT = -200      # 紧急任务
    HIGH = -100        # 高优先级  
    NORMAL = 0         # 正常优先级(默认)
    LOW = 100          # 低优先级
    BACKGROUND = 200   # 后台任务
```

## 3. 内部工作机制

### 3.1 存储机制
在Request构造函数中：
```python
def __init__(self, ..., priority: int = RequestPriority.NORMAL, ...):
    self.priority = -priority  # 注意这里的负号
```

这意味着：
- 传入的priority参数会被取负值存储
- 内部存储的priority值越小，优先级越高

### 3.2 排序机制
```python
def __lt__(self, other: _Request) -> bool:
    """用于按优先级排序"""
    return self.priority < other.priority
```

## 4. 实际行为示例

### 4.1 使用预定义优先级常量

| 传入参数 | 内部存储值 | 实际优先级 |
|---------|-----------|-----------|
| RequestPriority.URGENT (-200) | 200 | 最低优先级 ❌ |
| RequestPriority.HIGH (-100) | 100 | 低优先级 |
| RequestPriority.NORMAL (0) | 0 | 中等优先级 |
| RequestPriority.LOW (100) | -100 | 高优先级 |
| RequestPriority.BACKGROUND (200) | -200 | 最高优先级 |

### 4.2 使用自定义数值

| 传入参数 | 内部存储值 | 实际优先级 |
|---------|-----------|-----------|
| priority=1 | -1 | 高优先级 |
| priority=5 | -5 | 中等优先级 |
| priority=10 | -10 | 低优先级 |

## 5. 正确使用方式

### 5.1 如果您希望使用数值越小优先级越高：

```python
# 高优先级任务
high_priority_request = Request(url, priority=1)    # 内部存储为-1

# 中等优先级任务  
medium_priority_request = Request(url, priority=5)  # 内部存储为-5

# 低优先级任务
low_priority_request = Request(url, priority=10)    # 内部存储为-10
```

### 5.2 如果您希望使用预定义常量：

```python
from crawlo.network.request import Request, RequestPriority

# 注意：需要理解常量的含义
urgent_request = Request(url, priority=RequestPriority.BACKGROUND)  # 实际最高优先级
high_request = Request(url, priority=RequestPriority.LOW)           # 实际高优先级
normal_request = Request(url, priority=RequestPriority.NORMAL)      # 实际中等优先级
low_request = Request(url, priority=RequestPriority.HIGH)           # 实际低优先级
background_request = Request(url, priority=RequestPriority.URGENT)  # 实际最低优先级
```

## 6. 排序验证

当对请求进行排序时，会按照内部存储的priority值从小到大排序：

```python
# 创建请求
requests = [
    Request("url1", priority=10),   # 内部存储: -10
    Request("url2", priority=1),    # 内部存储: -1
    Request("url3", priority=5),    # 内部存储: -5
]

# 排序后顺序
sorted_requests = sorted(requests)
# 顺序为: url2(-1), url3(-5), url1(-10)
```

## 7. 结论

Crawlo框架的优先级机制**完全符合您的需求**：

1. **priority值越小越优先**：内部存储的priority值越小，优先级越高
2. **灵活配置**：可以使用自定义数值实现精确的优先级控制
3. **正确排序**：框架会自动按照优先级对请求进行排序

### 推荐使用方式：
```python
# 数值越小，优先级越高
Request(url, priority=1)    # 最高优先级
Request(url, priority=5)    # 高优先级
Request(url, priority=10)   # 中等优先级
Request(url, priority=20)   # 低优先级
```