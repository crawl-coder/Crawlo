# Crawlo框架Redis集群使用指南

## 概述

Crawlo框架支持Redis单实例和集群模式的智能切换。用户无需修改代码，只需通过配置即可在单实例和集群模式之间切换。

## 配置方式

### 1. 通过配置文件配置

在项目的`settings.py`文件中，使用`CrawloConfig.distributed()`方法创建分布式配置：

#### 单实例Redis配置
```python
from crawlo.config import CrawloConfig

# 单实例Redis配置
config = CrawloConfig.distributed(
    project_name='my_project',
    redis_host='127.0.0.1',
    redis_port=6379,
    redis_password='',
    redis_db=0,
    concurrency=16,
    download_delay=1.0
)

locals().update(config.to_dict())
```

#### Redis集群配置
```python
from crawlo.config import CrawloConfig

# Redis集群配置 - 方式1：使用逗号分隔的节点列表
config = CrawloConfig.distributed(
    project_name='my_project',
    redis_host='192.168.1.100:7000,192.168.1.101:7000,192.168.1.102:7000',
    redis_password='your_password',
    concurrency=16,
    download_delay=1.0
)

locals().update(config.to_dict())
```

```python
from crawlo.config import CrawloConfig

# Redis集群配置 - 方式2：使用集群URL格式
config = CrawloConfig.distributed(
    project_name='my_project',
    redis_host='redis-cluster://192.168.1.100:7000,192.168.1.101:7000,192.168.1.102:7000',
    redis_password='your_password',
    concurrency=16,
    download_delay=1.0
)

locals().update(config.to_dict())
```

### 2. 通过环境变量配置

```bash
# 设置运行模式为分布式
export CRAWLO_MODE=distributed

# 设置项目名称
export PROJECT_NAME=my_project

# 单实例Redis配置
export REDIS_HOST=127.0.0.1
export REDIS_PORT=6379
export REDIS_PASSWORD=your_password
export REDIS_DB=0

# Redis集群配置 - 使用逗号分隔的节点列表
export REDIS_HOST=192.168.1.100:7000,192.168.1.101:7000,192.168.1.102:7000
export REDIS_PASSWORD=your_password
```

### 3. 通过命令行参数配置

```bash
# 使用CLI工具运行爬虫时指定参数
crawlo run myspider --config settings.py --redis-host "192.168.1.100:7000,192.168.1.101:7000,192.168.1.102:7000" --redis-password "your_password"
```

## 智能模式检测

Crawlo框架会自动检测Redis连接URL的格式来决定使用单实例模式还是集群模式：

1. **单实例模式**：
   - URL格式：`redis://host:port/db`
   - 示例：`redis://127.0.0.1:6379/0`

2. **集群模式**：
   - URL包含多个节点（逗号分隔）：`redis://host1:port1,host2:port2,host3:port3`
   - 使用集群协议：`redis-cluster://host:port` 或 `rediss-cluster://host:port`
   - 显式指定集群节点列表

## Redis Key命名规范

无论使用单实例还是集群模式，框架都会自动使用统一的Redis Key命名规范：

- 请求去重：`crawlo:{PROJECT_NAME}:filter:fingerprint`
- 请求队列：`crawlo:{PROJECT_NAME}:queue:requests`
- 处理中队列：`crawlo:{PROJECT_NAME}:queue:processing`
- 失败队列：`crawlo:{PROJECT_NAME}:queue:failed`

在集群模式下，框架会自动使用哈希标签确保相关键在同一个slot中。

## 集群模式特性

### 1. 自动故障转移
Redis集群支持自动故障转移，当主节点故障时，从节点会自动接管。

### 2. 数据分片
数据分布在多个节点上，提高性能和可扩展性。

### 3. 高可用性
即使部分节点故障，系统仍可正常运行。

## 配置参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| redis_host | str | '127.0.0.1' | Redis服务器地址或集群节点列表 |
| redis_port | int | 6379 | Redis端口（单实例模式） |
| redis_password | str | None | Redis密码 |
| redis_db | int | 0 | Redis数据库编号（单实例模式） |
| project_name | str | 'crawlo' | 项目名称，用于命名空间 |
| concurrency | int | 16 | 并发数 |
| download_delay | float | 1.0 | 下载延迟 |

## 使用示例

### 完整的分布式项目配置示例

```python
# settings.py
from crawlo.config import CrawloConfig

# Redis集群配置示例
config = CrawloConfig.distributed(
    project_name='distributed_crawler',
    redis_host='192.168.1.100:7000,192.168.1.101:7000,192.168.1.102:7000',
    redis_password='strong_password',
    concurrency=32,
    download_delay=0.5
)

locals().update(config.to_dict())

# 其他配置
SPIDER_MODULES = ['my_project.spiders']
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/distributed_crawler.log'
```

### 启动多个爬虫节点

```bash
# 终端1
crawlo run myspider --config settings.py

# 终端2
crawlo run myspider --config settings.py

# 终端3
crawlo run myspider --config settings.py
```

## 注意事项

1. **集群模式要求**：
   - Redis版本 >= 3.0
   - 集群模式已启用
   - 节点间网络连通

2. **兼容性**：
   - 单实例和集群模式API完全兼容
   - 无需修改爬虫代码即可切换模式

3. **性能优化**：
   - 集群模式下建议使用哈希标签优化键分布
   - 合理设置并发数避免节点过载

4. **监控和维护**：
   - 定期检查集群健康状态
   - 监控各节点内存使用情况
   - 及时处理节点故障

## 故障排除

### 1. 连接问题
```bash
# 检查Redis集群状态
redis-cli -h 192.168.1.100 -p 7000 ping
```

### 2. 集群模式检测
框架会自动记录集群初始化日志：
```
INFO: Redis集群连接池初始化成功: 3 个节点
```

### 3. 常见错误
- `Redis Cluster cannot be connected`: 集群模式未启用或节点不可达
- `MOVED` or `ASK` errors: 键重定向问题，框架会自动处理

通过以上配置方式，用户可以轻松在单实例和集群模式之间切换，享受Crawlo框架带来的透明化Redis集群支持。