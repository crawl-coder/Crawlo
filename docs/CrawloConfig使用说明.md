# CrawloConfig 使用说明

## 概述

CrawloConfig 是 Crawlo 框架提供的配置工厂类，用于简化爬虫项目的配置管理。它提供了一种优雅的方式来创建不同运行模式的配置，包括单机模式、分布式模式和自动检测模式。

## 类定义

```python
class CrawloConfig:
    """Crawlo 配置工厂类"""
    
    def __init__(self, settings: Dict[str, Any]):
        # 初始化配置对象
        pass
```

## 静态工厂方法

### 1. standalone()
创建单机模式配置，适用于开发调试和小规模数据采集。

```python
@staticmethod
def standalone(
    concurrency: int = 8,
    download_delay: float = 1.0,
    **kwargs
) -> 'CrawloConfig':
```

**参数说明：**
- `concurrency`: 并发数，默认为8
- `download_delay`: 下载延迟（秒），默认为1.0
- `**kwargs`: 其他配置项

**使用示例：**
```python
# 使用默认配置
config = CrawloConfig.standalone()

# 自定义并发数和延迟
config = CrawloConfig.standalone(concurrency=4, download_delay=2.0)

# 添加其他配置项
config = CrawloConfig.standalone(
    concurrency=4,
    download_delay=2.0,
    LOG_LEVEL='DEBUG'
)
```

### 2. distributed()
创建分布式模式配置，适用于大规模数据采集和多节点协同工作。

```python
@staticmethod
def distributed(
    redis_host: str = '127.0.0.1',
    redis_port: int = 6379,
    redis_password: Optional[str] = None,
    redis_db: int = 0,
    project_name: str = 'crawlo',
    concurrency: int = 16,
    download_delay: float = 1.0,
    **kwargs
) -> 'CrawloConfig':
```

**参数说明：**
- `redis_host`: Redis 服务器地址，默认为'127.0.0.1'
- `redis_port`: Redis 端口，默认为6379
- `redis_password`: Redis 密码，默认为None
- `redis_db`: Redis 数据库编号，默认为0
- `project_name`: 项目名称（用于命名空间），默认为'crawlo'
- `concurrency`: 并发数，默认为16
- `download_delay`: 下载延迟（秒），默认为1.0
- `**kwargs`: 其他配置项

**使用示例：**
```python
# 使用默认配置
config = CrawloConfig.distributed()

# 自定义Redis配置
config = CrawloConfig.distributed(
    redis_host='192.168.1.100',
    redis_port=6380,
    project_name='my_project'
)

# 添加其他配置项
config = CrawloConfig.distributed(
    redis_host='192.168.1.100',
    concurrency=32,
    download_delay=0.5,
    LOG_LEVEL='INFO'
)
```

### 3. auto()
创建自动检测模式配置，框架会根据环境自动选择最佳运行方式。

```python
@staticmethod
def auto(
    concurrency: int = 12,
    download_delay: float = 1.0,
    **kwargs
) -> 'CrawloConfig':
```

**参数说明：**
- `concurrency`: 并发数，默认为12
- `download_delay`: 下载延迟（秒），默认为1.0
- `**kwargs`: 其他配置项

**使用示例：**
```python
# 使用默认配置
config = CrawloConfig.auto()

# 自定义并发数和延迟
config = CrawloConfig.auto(concurrency=16, download_delay=1.0)
```

### 4. from_env()
从环境变量创建配置。

```python
@staticmethod
def from_env(default_mode: str = 'standalone') -> 'CrawloConfig':
```

**支持的环境变量：**
- `CRAWLO_MODE`: 运行模式 (standalone/distributed/auto)
- `REDIS_HOST`: Redis 主机
- `REDIS_PORT`: Redis 端口
- `REDIS_PASSWORD`: Redis 密码
- `CONCURRENCY`: 并发数
- `PROJECT_NAME`: 项目名称

**使用示例：**
```python
# 从环境变量创建配置
config = CrawloConfig.from_env()

# 指定默认模式
config = CrawloConfig.from_env(default_mode='distributed')
```

### 5. custom()
创建自定义配置。

```python
@staticmethod
def custom(settings: Dict[str, Any]) -> 'CrawloConfig':
```

**参数说明：**
- `settings`: 自定义配置字典

**使用示例：**
```python
# 创建自定义配置
custom_settings = {
    'CONCURRENCY': 10,
    'DOWNLOAD_DELAY': 1.5,
    'LOG_LEVEL': 'DEBUG'
}
config = CrawloConfig.custom(custom_settings)
```

## 实例方法

### get()
获取配置项的值。

```python
def get(self, key: str, default: Any = None) -> Any:
```

**使用示例：**
```python
config = CrawloConfig.standalone()
concurrency = config.get('CONCURRENCY', 8)
```

### set()
设置配置项的值（支持链式调用）。

```python
def set(self, key: str, value: Any) -> 'CrawloConfig':
```

**使用示例：**
```python
config = CrawloConfig.standalone()
config.set('CONCURRENCY', 10).set('DOWNLOAD_DELAY', 2.0)
```

### update()
更新多个配置项（支持链式调用）。

```python
def update(self, settings: Dict[str, Any]) -> 'CrawloConfig':
```

**使用示例：**
```python
config = CrawloConfig.standalone()
config.update({
    'CONCURRENCY': 10,
    'DOWNLOAD_DELAY': 2.0
})
```

### set_concurrency()
设置并发数。

```python
def set_concurrency(self, concurrency: int) -> 'CrawloConfig':
```

### set_delay()
设置请求延迟。

```python
def set_delay(self, delay: float) -> 'CrawloConfig':
```

### enable_debug()
启用调试模式。

```python
def enable_debug(self) -> 'CrawloConfig':
```

### enable_mysql()
启用 MySQL 存储。

```python
def enable_mysql(self) -> 'CrawloConfig':
```

### set_redis_host()
设置 Redis 主机。

```python
def set_redis_host(self, host: str) -> 'CrawloConfig':
```

### to_dict()
转换为字典。

```python
def to_dict(self) -> Dict[str, Any]:
```

**使用示例：**
```python
config = CrawloConfig.standalone()
settings_dict = config.to_dict()
```

### print_summary()
打印配置摘要。

```python
def print_summary(self) -> 'CrawloConfig':
```

### validate()
验证当前配置。

```python
def validate(self) -> bool:
```

## 预设配置

通过 `CrawloConfig.presets()` 可以获取预设配置对象。

### development()
开发环境配置。

```python
@staticmethod
def development() -> CrawloConfig:
```

### production()
生产环境配置。

```python
@staticmethod
def production() -> CrawloConfig:
```

### large_scale()
大规模分布式配置。

```python
@staticmethod
def large_scale(redis_host: str, project_name: str) -> CrawloConfig:
```

### gentle()
温和模式配置（避免被封）。

```python
@staticmethod
def gentle() -> CrawloConfig:
```

## 使用示例

### 基本使用
```python
from crawlo.config import CrawloConfig

# 创建单机模式配置
config = CrawloConfig.standalone(concurrency=8, download_delay=1.0)

# 获取配置字典
settings = config.to_dict()

# 在爬虫进程中使用
from crawlo.crawler import CrawlerProcess
process = CrawlerProcess(settings=settings)
```

### 分布式模式
```python
from crawlo.config import CrawloConfig

# 创建分布式模式配置
config = CrawloConfig.distributed(
    redis_host='192.168.1.100',
    project_name='my_crawler',
    concurrency=16,
    download_delay=0.5
)

# 获取配置并使用
settings = config.to_dict()
```

### 链式调用
```python
from crawlo.config import CrawloConfig

# 使用链式调用设置配置
config = (CrawloConfig.standalone()
          .set_concurrency(10)
          .set_delay(2.0)
          .enable_debug())

settings = config.to_dict()
```

### 配置验证
```python
from crawlo.config import CrawloConfig

config = CrawloConfig.standalone()
if config.validate():
    print("配置验证通过")
    settings = config.to_dict()
else:
    print("配置验证失败")
```

## 配置项说明

### 基本配置项
- `PROJECT_NAME`: 项目名称
- `CONCURRENCY`: 并发数
- `DOWNLOAD_DELAY`: 下载延迟
- `LOG_LEVEL`: 日志级别

### 网络配置项
- `DOWNLOADER`: 下载器类
- `DOWNLOAD_TIMEOUT`: 下载超时时间
- `CONNECTION_POOL_LIMIT`: 连接池限制

### 队列配置项
- `QUEUE_TYPE`: 队列类型 (memory/redis/auto)
- `SCHEDULER_MAX_QUEUE_SIZE`: 调度器队列最大大小
- `SCHEDULER_QUEUE_NAME`: 调度器队列名称

### Redis配置项
- `REDIS_HOST`: Redis主机
- `REDIS_PORT`: Redis端口
- `REDIS_PASSWORD`: Redis密码
- `REDIS_DB`: Redis数据库编号
- `REDIS_URL`: Redis连接URL

### 存储配置项
- `MYSQL_HOST`: MySQL主机
- `MYSQL_PORT`: MySQL端口
- `MYSQL_USER`: MySQL用户名
- `MYSQL_PASSWORD`: MySQL密码
- `MYSQL_DB`: MySQL数据库名

## 最佳实践

1. **选择合适的运行模式**：
   - 开发调试阶段使用 `standalone` 模式
   - 小规模数据采集使用 `standalone` 模式
   - 大规模数据采集使用 `distributed` 模式
   - 不确定环境时使用 `auto` 模式

2. **合理设置并发数**：
   - 单机模式建议并发数为4-16
   - 分布式模式可根据节点数量适当增加

3. **设置合适的延迟**：
   - 避免对目标网站造成过大压力
   - 根据目标网站的反爬策略调整延迟

4. **使用配置验证**：
   - 在生产环境中使用前验证配置
   - 关注配置警告信息

5. **环境变量配置**：
   - 生产环境中推荐使用环境变量配置
   - 便于在不同环境中切换配置