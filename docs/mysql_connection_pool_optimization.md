# MySQL 连接池优化

## 背景

多爬虫运行时，每个 MySQL Pipeline 创建独立连接池会导致资源浪费和连接数超限。

## 解决方案

使用单例模式，相同配置共享同一个连接池。

```python
from crawlo.utils.mysql_connection_pool import MySQLConnectionPoolManager

pool = await MySQLConnectionPoolManager.get_pool(
    pool_type='asyncmy',
    host='localhost',
    port=3306,
    user='root',
    password='',
    db='crawlo',
    minsize=3,
    maxsize=10
)
```

## 配置 (settings.py)

```python
# MySQL 基础配置
MYSQL_HOST = '127.0.0.1'
MYSQL_PORT = 3306
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'your_password'
MYSQL_DB = 'your_database'

# 连接池配置
MYSQL_POOL_MIN = 3
MYSQL_POOL_MAX = 10

# 使用 Pipeline
PIPELINES = {
    'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline': 500,
}
```

## 监控

```python
from crawlo.utils.mysql_connection_pool import MySQLConnectionPoolManager

# 查看所有连接池状态
stats = MySQLConnectionPoolManager.get_pool_stats()

# 程序退出时关闭
await MySQLConnectionPoolManager.close_all_pools()
```

## 连接池大小建议

| 爬虫数量 | minsize | maxsize |
|---------|---------|---------|
| 1-3 个   | 3       | 10      |
| 4-10 个  | 5       | 20      |
| 10+ 个   | 10      | 50      |

## 迁移

**无需修改代码**，旧代码自动使用新的单例连接池。
