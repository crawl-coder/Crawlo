# Crawlo 框架教程示例

本目录包含了两个基于Crawlo框架命令从零开始创建的完整教程示例，展示如何使用标准流程实现电信设备许可证数据采集。

## 📁 项目结构

```
examples/
├── api_data_collection/             # API数据采集示例（列表页模式）
│   ├── crawlo.cfg                   # 项目配置文件
│   ├── run.py                       # 启动脚本
│   ├── logs/                        # 日志目录
│   └── api_data_collection/
│       ├── __init__.py
│       ├── settings.py              # 分布式配置
│       ├── items.py                 # 数据结构定义
│       └── spiders/
│           ├── __init__.py
│           └── api_data.py          # 爬虫实现（列表页模式）
│
├── telecom_licenses_standalone/     # 单机版示例（使用crawlo startproject创建）
│   ├── crawlo.cfg                   # 项目配置文件
│   ├── run.py                       # 启动脚本
│   ├── logs/                        # 日志目录
│   └── telecom_licenses_standalone/
│       ├── __init__.py
│       ├── settings.py              # 项目配置
│       ├── items.py                 # 数据结构定义
│       ├── middlewares.py           # 中间件
│       ├── pipelines.py             # 数据管道
│       └── spiders/
│           ├── __init__.py
│           └── telecom_device.py    # 爬虫实现
│
├── telecom_licenses_distributed/    # 分布式版示例（使用crawlo startproject创建）
│   ├── crawlo.cfg                   # 项目配置文件
│   ├── run.py                       # 启动脚本
│   ├── logs/                        # 日志目录
│   └── telecom_licenses_distributed/
│       ├── __init__.py
│       ├── settings.py              # 分布式配置
│       ├── items.py                 # 数据结构定义（含分布式字段）
│       ├── middlewares.py           # 中间件
│       ├── pipelines.py             # 数据管道
│       └── spiders/
│           ├── __init__.py
│           └── telecom_device.py    # 分布式爬虫实现
│
└── README.md                        # 本文档
```

## 🎯 项目特点

### 按框架标准创建
- 使用 `crawlo startproject` 命令创建项目结构
- 严格遵循框架默认配置和目录规范
- 基于框架模板进行业务逻辑定制

### 真实业务逻辑
- **数据源**: 工信部电信设备许可证API
- **API地址**: `https://ythzxfw.miit.gov.cn/oldyth/user-center/tbAppSearch/selectResult`
- **数据规模**: 约26,405页数据
- **数据清洗**: 自动移除HTML标签和格式化

### 分布式模式对比
本目录包含了 Crawlo 框架支持的两种主要分布式爬虫模式：

1. **列表页直接获取数据模式**：参见 [api_data_collection](api_data_collection/) 示例
2. **传统列表-详情页模式**：参见 [telecom_licenses_distributed](telecom_licenses_distributed/) 示例

### 数据字段映射
根据框架默认配置规范定义数据结构：

| 字段名 | 描述 | API字段映射 |
|--------|------|-------------|
| license_number | 许可证编号 | articleField01 |
| device_name | 设备名称 | articleField02 |
| device_model | 设备型号 | articleField03 |
| applicant | 申请单位 | articleField04 |
| manufacturer | 生产厂商 | articleField05 |
| issue_date | 发证日期 | articleField06 |
| expiry_date | 到期日期 | articleField07 |
| certificate_type | 证书类型 | articleField08 |
| remarks | 备注 | articleField09 |
| certificate_status | 证书状态 | articleField10 |
| origin | 原产地 | articleField11 |

## 🚀 快速开始

### API数据采集示例 (api_data_collection)

此示例演示了列表页直接获取数据的分布式爬虫模式，适用于API返回完整数据的场景。

#### 1. 进入项目目录
```bash
cd examples/api_data_collection
```

#### 2. 检查 Redis 连接
```bash
python run.py api_data --check-redis
```

#### 3. 启动分布式爬虫

**单机多进程:**
```bash
# 终端1
python run.py api_data

# 终端2 (同时运行)
python run.py api_data --concurrency 32
```

**多机分布式:**
```bash
# 机器A (Redis服务器)
python run.py api_data

# 机器B
python run.py api_data --redis-host 192.168.1.100 --concurrency 32

# 机器C
python run.py api_data --redis-host 192.168.1.100 --concurrency 24
```

### 详细文档
有关这两种分布式模式的详细信息，请参阅：
- [分布式爬取](../docs/modules/index.md)
- [队列模块](../docs/modules/queue/index.md)
- [过滤器模块](../docs/modules/filter/index.md)

## 🚀 快速开始

### 单机版 (telecom_licenses_standalone)

#### 1. 进入项目目录
```bash
cd examples/telecom_licenses_standalone
```

#### 2. 运行爬虫
```bash
# 基本运行
python run.py telecom_device

# 调试模式
python run.py telecom_device --debug

# 自定义参数
python run.py telecom_device --concurrency 4 --delay 2.0

# 限制页数（测试用）
python run.py telecom_device --max-pages 10
```

#### 3. 使用框架命令
```bash
# 查看爬虫列表
crawlo list

# 检查爬虫语法
crawlo check telecom_device

# 使用框架run命令（推荐使用项目自带的run.py）
crawlo run telecom_device
```

### 分布式版 (telecom_licenses_distributed)

#### 1. 准备 Redis 环境
```bash
# 使用 Docker 启动 Redis
docker run -d -p 6379:6379 --name redis-crawlo redis:alpine

# 或安装本地 Redis
# Windows: 下载 Redis for Windows
# Linux: sudo apt-get install redis-server
# macOS: brew install redis
```

#### 2. 进入项目目录
```bash
cd examples/telecom_licenses_distributed
```

#### 3. 检查 Redis 连接
```bash
python run.py telecom_device --check-redis
```

#### 4. 启动分布式爬虫

**单机多进程:**
```bash
# 终端1
python run.py telecom_device

# 终端2 (同时运行)
python run.py telecom_device --concurrency 32
```

**多机分布式:**
```bash
# 机器A (Redis服务器)
python run.py telecom_device

# 机器B
python run.py telecom_device --redis-host 192.168.1.100 --concurrency 16

# 机器C
python run.py telecom_device --redis-host 192.168.1.100 --concurrency 24
```

## ⚙️ 配置对比

### 单机版配置特点 (基于框架默认设置)
```python
# settings.py
DOWNLOADER = "crawlo.downloader.aiohttp_downloader.AioHttpDownloader"
CONCURRENCY = 8
DOWNLOAD_DELAY = 1.0
FILTER_CLASS = 'crawlo.filters.memory_filter.MemoryFilter'
```

### 分布式版配置特点 (扩展默认配置)
```python
# settings.py  
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis'
CONCURRENCY = 16
DOWNLOAD_DELAY = 1.0
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'
SCHEDULER = 'crawlo.scheduler.redis_scheduler.RedisScheduler'
```

## 📊 性能对比

| 特性 | 单机版 | 分布式版 |
|------|--------|----------|
| 部署复杂度 | ⭐ 简单 | ⭐⭐⭐ 中等 |
| 扩展性 | ⭐⭐ 限制 | ⭐⭐⭐⭐⭐ 优秀 |
| 资源要求 | 低 | 中等（需Redis） |
| 故障恢复 | ⭐⭐ 基础 | ⭐⭐⭐⭐ 强 |
| 去重效果 | ⭐⭐⭐ 内存 | ⭐⭐⭐⭐⭐ Redis |
| 适用场景 | 小到中等规模 | 大规模采集 |

## 🔧 框架命令使用

### 创建项目（已完成）
```bash
# 1. 创建项目
crawlo startproject telecom_licenses_standalone
crawlo startproject telecom_licenses_distributed

# 2. 生成爬虫（在项目目录中）
cd telecom_licenses_standalone
crawlo genspider telecom_device ythzxfw.miit.gov.cn
```

### 管理命令
```bash
# 列出爬虫
crawlo list

# 检查爬虫
crawlo check telecom_device

# 查看统计
crawlo stats

# 运行爬虫
crawlo run telecom_device
```

## 🐛 故障排除

### 常见问题

1. **导入错误**
   ```
   ImportError: No module named 'telecom_licenses_standalone'
   ```
   **解决**: 确保在项目根目录运行脚本，run.py已配置路径处理

2. **Redis 连接失败**
   ```
   Redis连接失败: localhost:6379
   ```
   **解决**: 检查Redis服务状态，使用 `--check-redis` 测试连接

3. **配置文件错误**
   ```
   crawlo.cfg not found
   ```
   **解决**: 确保在包含crawlo.cfg的目录中运行框架命令

4. **Spider类未找到**
   ```
   No spider found for: telecom_device
   ```
   **解决**: 检查spider文件中的name属性是否正确

### 调试方法
```bash
# 启用调试模式
python run.py telecom_device --debug

# 限制数据量测试
python run.py telecom_device --max-pages 5

# 检查配置
python -c "from telecom_licenses_standalone import settings; print(settings.CONCURRENCY)"
```

## 📈 最佳实践

### 开发流程
1. 使用 `crawlo startproject` 创建项目
2. 根据数据源更新 `items.py` 定义数据结构  
3. 实现 `spiders/` 中的爬虫逻辑
4. 在 `settings.py` 中调整配置参数
5. 创建适合的 `run.py` 启动脚本
6. 使用 `crawlo check` 验证爬虫代码

### 配置原则
- 遵循框架默认配置结构
- 单机版使用内存队列和过滤器
- 分布式版使用Redis队列和过滤器
- 根据目标网站调整延迟和并发参数

### 扩展方向
- 添加数据库存储管道
- 实现自定义中间件
- 配置代理池支持
- 添加监控和告警

## 📚 相关文档

- [Crawlo 框架文档](https://crawlo.readthedocs.io/)
- [框架命令参考](../crawlo/commands/)
- [默认配置说明](../crawlo/settings/default_settings.py)
- [项目模板](../crawlo/templates/)

---

**注意**: 本示例严格按照Crawlo框架标准流程创建，展示了从零开始使用框架命令构建完整爬虫项目的最佳实践.