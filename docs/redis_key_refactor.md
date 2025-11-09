# Redis Key 重构说明

## 背景

在 Crawlo 框架的早期版本中，Redis Key 的生成逻辑分散在多个文件中，缺乏统一管理。这导致了以下问题：

1. **Key生成逻辑分散**：Redis key的生成逻辑分散在多个文件中，缺乏统一管理
2. **Key命名规范不一致**：虽然有规范，但在不同组件中实现方式不一致
3. **缺少spider_name支持**：当前只使用project_name，对于一个项目下有多个爬虫的情况，无法有效区分
4. **processing队列数据清理问题**：在爬取结束后，processing和processing:data队列中的数据是否应该保留需要评估

## 解决方案

为了解决这些问题，我们引入了 `RedisKeyManager` 类来统一管理所有 Redis Key 的生成和验证。

### RedisKeyManager 类

`RedisKeyManager` 类提供了以下功能：

1. **统一的 Key 生成**：集中管理所有 Redis Key 的生成逻辑
2. **支持 spider_name**：支持在项目下区分不同的爬虫
3. **Key 验证集成**：与 `RedisKeyValidator` 集成，确保生成的 Key 符合命名规范

### Key 命名规范

新的 Key 命名规范支持两种格式：

1. **项目级别**：`crawlo:{project}:{component}:{sub_component}`
2. **爬虫级别**：`crawlo:{project}:{spider}:{component}:{sub_component}`

其中：
- `project`：项目名称
- `spider`：爬虫名称（可选）
- `component`：组件类型（queue, filter, item）
- `sub_component`：子组件类型

### 命名空间隔离

通过使用 `{project_name}` 前缀确保不同项目间的数据隔离，同时通过可选的 `{spider_name}` 支持同一项目下不同爬虫的数据隔离：

- **项目级别隔离**：`crawlo:project1:queue:requests` vs `crawlo:project2:queue:requests`
- **爬虫级别隔离**：`crawlo:project1:spider1:queue:requests` vs `crawlo:project1:spider2:queue:requests`

这种设计提供了灵活的命名空间隔离机制，既支持项目级别的隔离，也支持更细粒度的爬虫级别隔离。

### 组件和子组件类型

#### Queue 组件
- `requests`：请求队列
- `processing`：处理中队列（注意：当前实现已取消处理中队列）
- `failed`：失败队列

#### Filter 组件
- `fingerprint`：请求去重指纹

#### Item 组件
- `fingerprint`：数据项去重指纹

### 使用示例

```python
from crawlo.utils.redis_key_manager import RedisKeyManager

# 创建 Key 管理器（项目级别）
key_manager = RedisKeyManager("my_project")

# 创建 Key 管理器（爬虫级别）
key_manager = RedisKeyManager("my_project", "my_spider")

# 生成各种 Key
requests_queue_key = key_manager.get_requests_queue_key()
processing_queue_key = key_manager.get_processing_queue_key()
failed_queue_key = key_manager.get_failed_queue_key()
filter_fingerprint_key = key_manager.get_filter_fingerprint_key()
item_fingerprint_key = key_manager.get_item_fingerprint_key()

# 设置爬虫名称
key_manager.set_spider_name("another_spider")
```

## 修改的文件

1. **新增文件**：
   - `crawlo/utils/redis_key_manager.py`：Redis Key 管理器
   - `tests/test_redis_key_manager.py`：Redis Key 管理器测试
   - `tests/test_redis_key_integration.py`：Redis Key 管理器与验证器集成测试

2. **修改文件**：
   - `crawlo/queue/redis_priority_queue.py`：使用 RedisKeyManager 生成队列相关的 Key
   - `crawlo/filters/aioredis_filter.py`：使用 RedisKeyManager 生成过滤器相关的 Key
   - `crawlo/pipelines/redis_dedup_pipeline.py`：使用 RedisKeyManager 生成数据项去重相关的 Key
   - `crawlo/utils/redis_key_validator.py`：更新验证逻辑以支持包含 spider_name 的 Key 格式

## 处理队列数据清理

关于 `crawlo:ofweek_standalone:queue:processing` 和 `crawlo:ofweek_standalone:queue:processing:data` 的处理，在代码正常采集结束后，里面的数据已经消费，是否应该存在，需要评估。

在当前实现中，我们已经取消了处理中队列（processing queue）：
- 请求一旦从主队列取出即认为完成处理
- 不再使用处理中队列来跟踪正在处理的请求
- 简化了队列模型，提高了性能和可靠性

关于数据清理，在当前实现中，我们保留了原有的清理逻辑：

1. **默认行为**：默认情况下不清理 Redis 中的数据，以支持断点续爬
2. **清理选项**：可以通过配置 `CLEANUP_REDIS_DATA` 为 `True` 来启用数据清理

这种设计既保证了数据的持久性，又提供了清理选项以满足不同需求。

## 测试

我们添加了全面的测试来确保重构的正确性：

1. **单元测试**：测试 RedisKeyManager 的各个功能
2. **集成测试**：测试 RedisKeyManager 与 RedisKeyValidator 的集成

所有测试都已通过，确保了重构的正确性和稳定性。