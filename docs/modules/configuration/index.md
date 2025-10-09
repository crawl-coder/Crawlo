# 配置系统

Crawlo 提供了强大而灵活的配置管理系统，支持多种配置方式和验证机制，确保框架的稳定运行。

## 配置方式

Crawlo 支持多种配置方式，用户可以根据需要选择最适合的方式：

### 1. 代码配置

通过 [CrawloConfig](../../api/crawlo_config.md) 类的静态工厂方法创建配置：

```python
from crawlo.config import CrawloConfig

# 单机模式配置
config = CrawloConfig.standalone(
    project_name='my_project',
    concurrency=10,
    download_delay=1.0
)

# 分布式模式配置
config = CrawloConfig.distributed(
    project_name='my_project',
    redis_host='127.0.0.1',
    redis_port=6379,
    concurrency=20
)
```

### 2. 配置文件

创建 `settings.py` 文件定义配置：

```python
# settings.py
PROJECT_NAME = 'my_project'
CONCURRENCY = 10
DOWNLOAD_DELAY = 1.0
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
```

### 3. 环境变量

通过环境变量配置关键参数：

```bash
export CRAWLO_CONCURRENCY=20
export CRAWLO_DOWNLOAD_DELAY=0.5
export CRAWLO_REDIS_HOST=192.168.1.100
```

## 配置优先级

Crawlo 采用以下配置优先级顺序（从高到低）：

1. **代码配置** - 直接通过 CrawloConfig 类设置的配置
2. **环境变量** - 系统环境变量
3. **配置文件** - settings.py 文件中的配置
4. **默认配置** - 框架内置的默认配置

## 核心配置项

### 基础配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| PROJECT_NAME | str | 'crawlo_project' | 项目名称 |
| VERSION | str | '1.0.0' | 项目版本 |
| CONCURRENCY | int | 16 | 并发请求数 |
| DOWNLOAD_DELAY | float | 0.5 | 下载延迟（秒） |
| DOWNLOAD_TIMEOUT | int | 30 | 下载超时时间（秒） |
| MAX_RETRY_TIMES | int | 3 | 最大重试次数 |

### 队列配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| QUEUE_TYPE | str | 'memory' | 队列类型（memory/redis） |
| SCHEDULER_MAX_QUEUE_SIZE | int | 10000 | 调度器最大队列大小 |
| REDIS_HOST | str | '127.0.0.1' | Redis 主机地址 |
| REDIS_PORT | int | 6379 | Redis 端口 |
| REDIS_PASSWORD | str | None | Redis 密码 |
| REDIS_DB | int | 0 | Redis 数据库编号 |

### 存储配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| MYSQL_HOST | str | '127.0.0.1' | MySQL 主机地址 |
| MYSQL_PORT | int | 3306 | MySQL 端口 |
| MYSQL_USER | str | 'root' | MySQL 用户名 |
| MYSQL_PASSWORD | str | '' | MySQL 密码 |
| MYSQL_DATABASE | str | 'crawlo' | MySQL 数据库名 |
| MONGO_URI | str | 'mongodb://127.0.0.1:27017' | MongoDB 连接 URI |

### 日志配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| LOG_LEVEL | str | 'INFO' | 日志级别 |
| LOG_FILE | str | None | 日志文件路径 |
| LOG_MAX_BYTES | int | 10*1024*1024 | 日志文件最大大小 |
| LOG_BACKUP_COUNT | int | 5 | 日志文件备份数量 |

## 配置验证

Crawlo 内置了配置验证机制，确保配置的正确性和完整性。

### 验证器

[ConfigValidator](../../api/crawlo_config_validator.md) 类提供了全面的配置验证功能：

```python
from crawlo.config_validator import validate_config, print_validation_report

# 验证配置
is_valid, errors, warnings = validate_config(settings_dict)

if not is_valid:
    print(f"配置验证失败，发现 {len(errors)} 个错误")
    for error in errors:
        print(f"❌ {error}")
else:
    print("配置验证通过")

# 打印详细验证报告
print_validation_report(settings_dict)
```

### 验证内容

配置验证器会检查以下内容：

1. **基本设置验证** - 检查项目名称、版本等基本配置项
2. **网络设置验证** - 验证下载超时、延迟、重试次数等网络相关参数
3. **并发设置验证** - 确保并发数为正整数
4. **队列设置验证** - 检查队列类型的有效性
5. **存储设置验证** - 验证数据库相关配置
6. **Redis设置验证** - 当使用 Redis 队列时，验证 Redis 配置
7. **中间件和管道验证** - 确保中间件和管道配置为列表类型
8. **日志设置验证** - 验证日志级别是否为有效值

## Redis Key 命名规范

为了确保 Redis 中的键名统一和可维护，Crawlo 推荐使用以下命名规范：

```python
# 推荐的 Redis Key 命名规范
crawlo:{PROJECT_NAME}:queue:requests     # 请求队列
crawlo:{PROJECT_NAME}:item:fingerprint   # 数据项去重
crawlo:{PROJECT_NAME}:queue:processing   # 处理中队列
crawlo:{PROJECT_NAME}:queue:failed       # 失败队列
```

## 最佳实践

### 配置管理建议

1. **开发环境** - 使用代码配置或简单的配置文件
2. **测试环境** - 使用配置文件，通过环境变量覆盖关键参数
3. **生产环境** - 使用配置文件和环境变量结合的方式，敏感信息通过环境变量传递

### 安全配置

1. **敏感信息** - 密码等敏感信息应通过环境变量配置
2. **访问控制** - 配置文件应设置适当的文件权限
3. **备份策略** - 重要配置应定期备份

### 性能调优

1. **并发设置** - 根据目标网站的承受能力调整并发数
2. **延迟设置** - 合理设置下载延迟，避免对目标网站造成压力
3. **超时设置** - 根据网络环境调整超时时间