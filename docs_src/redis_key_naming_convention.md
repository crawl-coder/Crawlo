# Redis Key 命名规范

## 1. 概述

为了提高Redis key的可读性、可维护性和一致性，我们制定了统一的Redis key命名规范。所有Redis key都遵循以下格式：

```
crawlo:{project_name}:{component}:{sub_component}
```

## 2. 命名规范说明

### 2.1 基本结构

| 部分 | 说明 | 示例 |
|------|------|------|
| `crawlo` | 固定前缀，标识为Crawlo框架 | crawlo |
| `{project_name}` | 项目名称，从配置中获取 | books_distributed, api_data_collection |
| `{component}` | 组件类型 | filter, queue, item |
| `{sub_component}` | 子组件或功能 | fingerprint, requests, processing, failed |

### 2.2 具体命名规则

#### 2.2.1 请求去重过滤器 (Filter)

- 请求指纹存储: `crawlo:{project_name}:filter:fingerprint`

#### 2.2.2 队列管理器 (Queue)

- 请求队列: `crawlo:{project_name}:queue:requests`
- 处理中队列: `crawlo:{project_name}:queue:processing`
- 失败队列: `crawlo:{project_name}:queue:failed`

#### 2.2.3 数据项去重 (Item)

- 数据项指纹存储: `crawlo:{project_name}:item:fingerprint`

## 3. 示例

### 3.1 Books分布式爬虫项目

```
crawlo:books_distributed:filter:fingerprint
crawlo:books_distributed:queue:requests
crawlo:books_distributed:queue:processing
crawlo:books_distributed:queue:failed
crawlo:books_distributed:item:fingerprint
```

### 3.2 API数据采集项目

```
crawlo:api_data_collection:filter:fingerprint
crawlo:api_data_collection:queue:requests
crawlo:api_data_collection:queue:processing
crawlo:api_data_collection:queue:failed
crawlo:api_data_collection:item:fingerprint
```

## 4. 配置方式

### 4.1 在settings.py中配置项目名称

```python
PROJECT_NAME = 'your_project_name'
```

### 4.2 Redis URL配置

```python
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = ''
REDIS_DB = 0
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
```

## 5. 优势

1. **一致性**: 所有项目使用相同的命名规范
2. **可读性**: 通过key名称可以清楚知道其用途和所属项目
3. **可维护性**: 便于管理和清理特定项目的Redis数据
4. **扩展性**: 支持添加新的组件和子组件

## 6. 各组件说明

### 6.1 请求去重过滤器 (Filter)
- **作用**: 防止发送重复的网络请求
- **实现位置**: 框架核心层
- **处理时机**: 发送请求前
- **去重依据**: 请求指纹（URL、方法、参数等）

### 6.2 队列管理器 (Queue)
- **作用**: 管理爬虫任务队列
- **实现位置**: 框架核心层
- **包含队列**:
  - requests: 待处理请求队列
  - processing: 正在处理的请求队列
  - failed: 处理失败的请求队列

### 6.3 数据项去重 (Item)
- **作用**: 防止保存重复的数据结果
- **实现位置**: 数据管道层（用户自定义）
- **处理时机**: 保存数据前
- **去重依据**: 数据内容（数据项字段）

## 7. Key验证工具

Crawlo框架提供了Redis Key验证工具，用于验证Redis Key是否符合命名规范。

### 7.1 使用配置验证器验证Redis Key

```python
from crawlo.config_validator import ConfigValidator

# 创建配置验证器
validator = ConfigValidator()

# 验证配置（包括Redis Key）
config = {
    'PROJECT_NAME': 'test_project',
    'QUEUE_TYPE': 'redis',
    'SCHEDULER_QUEUE_NAME': 'crawlo:test_project:queue:requests',
    'REDIS_HOST': '127.0.0.1',
    'REDIS_PORT': 6379
}

is_valid, errors, warnings = validator.validate(config)
if not is_valid:
    print("配置验证失败:")
    for error in errors:
        print(f"  - {error}")
```

### 7.2 Redis Key命名规范验证函数

```python
from crawlo.utils.redis_key_validator import validate_redis_key_naming

# 验证单个Redis Key
key = "crawlo:my_project:queue:requests"
is_valid = validate_redis_key_naming(key, "my_project")
print(f"Key '{key}' 命名规范验证: {'通过' if is_valid else '失败'}")

# 验证多个Redis Key
keys = [
    "crawlo:my_project:filter:fingerprint",
    "crawlo:my_project:queue:requests",
    "crawlo:my_project:queue:processing",
    "crawlo:my_project:item:fingerprint"
]

for key in keys:
    is_valid = validate_redis_key_naming(key, "my_project")
    print(f"Key '{key}' 命名规范验证: {'通过' if is_valid else '失败'}")
```

### 7.3 命令行工具

Crawlo还提供了命令行工具来验证Redis Key命名规范：

```bash
# 验证项目配置中的Redis Key
crawlo validate-config --project-path /path/to/your/project

# 验证特定的Redis Key
crawlo validate-redis-key "crawlo:my_project:queue:requests" --project-name my_project
```

## 8. 修改记录

### 8.1 从旧配置迁移到新规范

#### 8.1.1 已移除的旧配置项
- `REDIS_KEY` 配置项已从所有配置文件中移除

#### 8.1.2 已修改的文件
1. **框架核心文件**:
   - `crawlo/filters/aioredis_filter.py`: 使用统一的Redis key命名规范
   - `crawlo/queue/redis_priority_queue.py`: 使用统一的Redis key命名规范
   - `crawlo/queue/queue_manager.py`: 正确传递module_name参数
   - `crawlo/pipelines/redis_dedup_pipeline.py`: 使用统一的Redis key命名规范
   - `crawlo/mode_manager.py`: 移除旧的REDIS_KEY配置

2. **模板文件**:
   - `crawlo/templates/project/settings.py.tmpl`: 更新Redis key配置说明

3. **示例项目**:
   - `examples/books_distributed/books_distributed/settings.py`: 更新Redis key配置说明
   - `examples/api_data_collection/api_data_collection/settings.py`: 更新Redis key配置说明
   - `examples/telecom_licenses_distributed/telecom_licenses_distributed/settings.py`: 更新Redis key配置说明

### 8.2 配置迁移指南

#### 8.2.1 旧配置方式
```python
# 旧的配置方式（已废弃）
REDIS_KEY = 'project_name:fingerprint'
```

#### 8.2.2 新配置方式
```python
# 新的配置方式（自动处理）
# Redis key配置已移至各组件中，使用统一的命名规范
# crawlo:{PROJECT_NAME}:filter:fingerprint (请求去重)
# crawlo:{PROJECT_NAME}:item:fingerprint (数据项去重)
```

## 9. 最佳实践

1. **使用PROJECT_NAME配置项**：在settings.py中明确设置项目名称
2. **避免手动配置Redis key**：让框架自动处理Redis key的生成
3. **定期清理Redis数据**：根据需要清理过期的Redis数据
4. **监控Redis使用情况**：关注Redis内存使用和性能指标
5. **使用验证工具**：在部署前使用Redis Key验证工具确保命名规范正确

## 10. 故障排除

### 10.1 常见问题

1. **Key命名不规范**：
   - 症状：Redis操作失败或数据混乱
   - 解决方案：使用验证工具检查Key命名并修正

2. **项目名称不匹配**：
   - 症状：不同项目的数据混淆
   - 解决方案：确保每个项目的PROJECT_NAME配置唯一

3. **组件类型错误**：
   - 症状：功能异常或数据丢失
   - 解决方案：检查组件类型是否正确（filter, queue, item）

### 10.2 调试技巧

1. **使用Redis CLI查看Key**：
   ```bash
   redis-cli KEYS "crawlo:*"
   ```

2. **监控Redis内存使用**：
   ```bash
   redis-cli INFO memory
   ```

3. **启用调试日志**：
   ```python
   FILTER_DEBUG = True
   LOG_LEVEL = 'DEBUG'
   ```