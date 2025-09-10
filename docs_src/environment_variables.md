# 环境变量配置指南

## 概述

Crawlo 框架采用统一的环境变量管理机制，所有环境变量的读取都集中在 [default_settings.py](file:///d%3A/dowell/projects/Crawlo/crawlo/settings/default_settings.py) 中通过 [env_config.py](file:///d%3A/dowell/projects/Crawlo/crawlo/utils/env_config.py) 工具进行处理。这样确保了环境变量的使用一致性和可维护性。

## 支持的环境变量

### 运行时配置

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `PROJECT_NAME` | `crawlo` | 项目名称，用于日志、Redis Key 等标识 |
| `CRAWLO_MODE` | `standalone` | 运行模式：`standalone`/`distributed`/`auto` |
| `CONCURRENCY` | `8` | 并发数配置 |

### Redis 配置

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `REDIS_HOST` | `127.0.0.1` | Redis 服务器主机地址 |
| `REDIS_PORT` | `6379` | Redis 服务器端口 |
| `REDIS_PASSWORD` | `` | Redis 密码（空表示无密码） |
| `REDIS_DB` | `0` | Redis 数据库编号 |

## 使用方法

### 1. 在命令行中设置环境变量

#### Windows (PowerShell)
```powershell
$env:PROJECT_NAME = "my_distributed_crawler"
$env:REDIS_HOST = "redis.example.com"
$env:REDIS_PORT = "6380"
$env:CONCURRENCY = "16"
$env:CRAWLO_MODE = "distributed"
```

#### Linux/macOS
```bash
export PROJECT_NAME="my_distributed_crawler"
export REDIS_HOST="redis.example.com"
export REDIS_PORT="6380"
export CONCURRENCY="16"
export CRAWLO_MODE="distributed"
```

### 2. 在代码中使用环境变量

框架内部通过 [env_config.py](file:///d%3A/dowell/projects/Crawlo/crawlo/utils/env_config.py) 工具统一处理环境变量：

```python
from crawlo.utils.env_config import get_env_var, get_redis_config, get_runtime_config

# 获取单个环境变量
project_name = get_env_var('PROJECT_NAME', 'default_project', str)

# 获取Redis配置
redis_config = get_redis_config()
redis_host = redis_config['REDIS_HOST']

# 获取运行时配置
runtime_config = get_runtime_config()
mode = runtime_config['CRAWLO_MODE']
```

### 3. 在 settings.py 中使用

在项目的 [settings.py](file:///d%3A/dowell/projects/Crawlo/examples/telecom_licenses_distributed/telecom_licenses_distributed/settings.py) 文件中，可以通过以下方式使用环境变量：

```python
from crawlo.utils.env_config import get_env_var, get_redis_config

# 项目配置
PROJECT_NAME = get_env_var('PROJECT_NAME', 'my_crawler', str)
CONCURRENCY = get_env_var('CONCURRENCY', 8, int)

# Redis配置
redis_config = get_redis_config()
REDIS_HOST = redis_config['REDIS_HOST']
REDIS_PORT = redis_config['REDIS_PORT']
```

## 最佳实践

### 1. 配置优先级

环境变量配置优先级高于代码中的默认值，但低于 [settings.py](file:///d%3A/dowell/projects/Crawlo/examples/telecom_licenses_distributed/telecom_licenses_distributed/settings.py) 中的显式配置。

### 2. 配置验证

框架会在启动时验证关键配置的有效性，如 Redis 连接参数。

### 3. 安全性

敏感信息如 Redis 密码应通过环境变量传递，避免硬编码在代码中。

## 故障排除

### 1. 环境变量未生效

确保环境变量在运行 Crawlo 应用之前正确设置，并且应用能够访问这些变量。

### 2. Redis 连接失败

检查以下配置：
- `REDIS_HOST` 和 `REDIS_PORT` 是否正确
- `REDIS_PASSWORD` 是否正确（如果需要密码）
- Redis 服务器是否正在运行并可访问

### 3. 并发配置问题

如果设置的 `CONCURRENCY` 值过高，可能会导致系统资源不足，建议根据实际硬件配置调整。