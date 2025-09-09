# API数据采集示例（列表页模式）

本示例演示了如何在 Crawlo 框架中使用分布式爬虫的列表页直接获取数据模式，其中完整数据可直接从列表/API页面获得，无需解析详情页。

## 🎯 核心特性

- **分布式处理**：多个节点并发处理不同页面
- **高并发**：针对高并发场景优化
- **Redis协调**：使用Redis进行请求队列和去重
- **负载均衡**：节点间自动负载分配

## 📁 项目结构

```
api_data_collection/
├── crawlo.cfg                   # 项目配置
├── run.py                       # 运行脚本
├── logs/                        # 日志目录
└── api_data_collection/
    ├── __init__.py
    ├── settings.py              # 分布式配置
    ├── items.py                 # 数据结构定义
    └── spiders/
        ├── __init__.py
        └── api_data.py         # 爬虫实现（列表页模式）
```

## ⚙️ 配置亮点

### 分布式设置
```python
# settings.py
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis'
CONCURRENCY = 32  # 列表页模式支持高并发
DOWNLOAD_DELAY = 0.5
```

### 爬虫实现
爬虫预先生成所有页面请求，允许多个节点并行处理：

```python
def start_requests(self):
    """生成所有页面请求以实现并行处理"""
    for page in range(self.start_page, self.end_page + 1):
        yield Request(
            url=f'{self.base_api_url}?page={page}&limit=50',
            callback=self.parse,
            meta={'page': page},
            dont_filter=False  # 启用去重
        )
```

## 🚀 运行爬虫

### 1. 启动Redis服务器
```bash
redis-server
```

### 2. 运行多个节点
```bash
# 终端1
python run.py api_data

# 终端2
python run.py api_data --concurrency 32

# 终端3
python run.py api_data --concurrency 24
```

## 📊 性能优势

| 方面 | 优势 |
|------|------|
| **速度** | 多个节点并发处理页面 |
| **扩展性** | 易于添加更多节点 |
| **可靠性** | 节点故障不会停止爬取 |
| **效率** | 无需冗余的详情页请求 |

## 🛠️ 适用场景

此模式适用于：
- API数据采集，其中完整数据在列表响应中返回
- 简单列表页面包含所有所需信息
- 大量数据采集场景
- 详情页不提供额外价值的情况

对于需要解析详情页的场景，请参阅 [telecom_licenses_distributed](../telecom_licenses_distributed/) 示例。