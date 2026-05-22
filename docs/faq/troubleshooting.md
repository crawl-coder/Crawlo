# 故障排查

## 爬虫不启动

### 问题 1: 找不到爬虫

**错误信息**：
```
ERROR: Spider not found: myspider
```

**解决方案**：

1. 检查爬虫名称是否正确
```bash
crawlo list  # 列出所有可用爬虫
```

2. 检查爬虫文件是否在 `spiders/` 目录下

3. 检查爬虫类是否继承自 `Spider`
```python
from crawlo import Spider  # 确保导入正确

class MySpider(Spider):  # 确保继承
    name = 'myspider'
```

### 问题 2: 导入错误

**错误信息**：
```
ModuleNotFoundError: No module named 'xxx'
```

**解决方案**：

1. 检查虚拟环境是否激活
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

2. 重新安装依赖
```bash
pip install -r requirements.txt
```

### 问题 3: 配置错误

**错误信息**：
```
RuntimeError: Invalid configuration
```

**解决方案**：

检查 `settings.py` 是否有语法错误：
```bash
python -m py_compile settings.py
```

## 请求超时

### 问题 1: 连接超时

**错误信息**：
```
TimeoutError: Connection timed out
```

**解决方案**：

1. 检查网络连接
```bash
ping example.com
```

2. 增加超时时间
```python
# settings.py
DOWNLOAD_TIMEOUT = 30  # 30秒
```

3. 使用代理
```python
yield Request(url, meta={'proxy': 'http://proxy:8080'})
```

### 问题 2: 读取超时

**错误信息**：
```
TimeoutError: Read timed out
```

**解决方案**：

1. 目标网站响应慢
```python
# settings.py
DOWNLOAD_TIMEOUT = 60  # 增加到60秒
CONCURRENCY = 8  # 降低并发
```

2. 使用浏览器渲染
```python
yield Request(url, meta={'use_dynamic_loader': True})
```

## 数据未保存

### 问题 1: 文件为空

**现象**：运行后输出文件为空

**原因**：
- 爬虫没有提取到数据
- 选择器错误

**解决方案**：

1. 调试选择器
```python
async def parse(self, response):
    # 打印 HTML 查看结构
    print(response.text[:1000])
    
    # 测试选择器
    items = response.css('div.item').getall()
    print(f"找到 {len(items)} 个元素")
```

2. 检查 yield 语句
```python
# 确保有 yield
async def parse(self, response):
    yield {'title': 'test'}  # 测试是否能输出
```

### 问题 2: 数据库未写入

**现象**：数据没有保存到数据库

**解决方案**：

1. 检查数据库连接
```python
# settings.py
MYSQL_HOST = 'localhost'
MYSQL_PORT = 3306
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'password'
MYSQL_DATABASE = 'mydb'
```

2. 检查 Pipeline 是否启用
```python
# settings.py
PIPELINES = {
    'crawlo.pipelines.MySQLPipeline': 300,
}
```

3. 查看 Pipeline 日志
```bash
crawlo run myspider --log-level DEBUG
```

## 连接错误

### 问题 1: Redis 连接失败

**错误信息**：
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**解决方案**：

1. 检查 Redis 是否运行
```bash
redis-cli ping  # 应返回 PONG
```

2. 检查连接配置
```python
# settings.py
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_PASSWORD = ''  # 如果有密码
```

3. 启动 Redis
```bash
# Linux/Mac
redis-server

# Windows
redis-server.exe
```

### 问题 2: MySQL 连接失败

**错误信息**：
```
pymysql.err.OperationalError: (2003, "Can't connect to MySQL server")
```

**解决方案**：

1. 检查 MySQL 是否运行
```bash
mysql -u root -p  # 尝试登录
```

2. 检查连接配置
```python
# settings.py
MYSQL_HOST = 'localhost'
MYSQL_PORT = 3306
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'password'
MYSQL_DATABASE = 'mydb'
```

3. 创建数据库
```sql
CREATE DATABASE mydb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 问题 3: MongoDB 连接失败

**错误信息**：
```
pymongo.errors.ServerSelectionTimeoutError
```

**解决方案**：

1. 检查 MongoDB 是否运行
```bash
mongosh  # 尝试连接
```

2. 检查连接配置
```python
# settings.py
MONGO_URI = 'mongodb://localhost:27017'
MONGO_DATABASE = 'mydb'
```

## 403 Forbidden

### 问题：被目标网站拒绝

**错误信息**：
```
HTTP 403 Forbidden
```

**解决方案**：

1. 设置 User-Agent
```python
# settings.py
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...'
```

2. 使用代理
```python
# settings.py
PROXY_ENABLED = True
PROXY_LIST = ['http://proxy1:8080']
```

3. 使用浏览器渲染
```python
yield Request(url, meta={'use_dynamic_loader': True})
```

4. 启用 Cloudflare 绕过
```python
# settings.py
CLOUDFLARE_BYPASS_ENABLED = True
```

## 500 Internal Server Error

### 问题：目标服务器错误

**解决方案**：

1. 启用重试
```python
# settings.py
RETRY_ENABLED = True
RETRY_TIMES = 3
```

2. 添加延迟
```python
# settings.py
DOWNLOAD_DELAY = 2.0
```

3. 降低并发
```python
# settings.py
CONCURRENCY = 4
```

## 内存溢出 (OOM)

### 问题：进程被系统杀死

**解决方案**：

1. 限制队列大小
```python
# settings.py
MEMORY_SCHEDULER_MAX_QUEUE_SIZE = 5000
```

2. 启用背压
```python
# settings.py
BACKPRESSURE_ENABLED = True
BACKPRESSURE_RATIO = 0.8
```

3. 分批处理
```python
# settings.py
BATCH_SIZE = 500
```

## 爬虫卡住不动

### 诊断步骤

1. 查看日志
```bash
crawlo run myspider --log-level DEBUG
```

2. 检查队列状态
```python
# 在爬虫中
async def parse(self, response):
    queue_size = await self.crawler.scheduler.queue.size()
    self.logger.info(f"队列: {queue_size}")
```

3. 检查是否有请求在等待
```python
# settings.py
STATS_ENABLED = True
STATS_INTERVAL = 10
```

### 常见原因

| 原因 | 症状 | 解决方案 |
|------|------|---------|
| **队列空了** | 无错误，爬虫退出 | 检查 start_urls |
| **所有请求失败** | 大量错误日志 | 检查代理、UA |
| **死锁** | 卡住不动 | 降低并发、增加超时 |
| **等待响应** | 日志停止更新 | 检查网络、增加超时 |

## 深度优先调度不生效

### 问题：设置了 DEPTH_PRIORITY=1 但详情页没有优先处理

**现象**：
- 列表页和详情页的 priority 值相同
- 首个 Item 产出时间极慢（需要等所有列表页处理完才处理详情页）
- 调试日志显示子请求 `depth` 与父请求相同（如都是 depth=1）

**原因分析**：

`depth` 传播由 Engine 的 `_handle_spider_output` 统一管理。如果中间件或工具函数提前向 `request.meta` 注入了 `depth`，Engine 的 `if 'depth' not in spider_output.meta` 检查会被跳过，导致子请求 depth 值错误。

**诊断步骤**：

1. 开启 DEBUG 日志，检查 depth 传播：
```python
# settings.py
LOG_LEVEL = 'DEBUG'
```

2. 在日志中搜索关键信息：
```
[产出] 子请求 depth=1    ← 如果子请求 depth 与父请求相同，说明 depth 传播失效
[set_request] had_depth=True → depth=1    ← depth 已存在但值错误
```

3. 正确的日志应显示：
```
[产出] 子请求 depth=2    ← 子请求 depth = parent_depth + 1
[set_request] had_depth=True → depth=2, priority: 0 → -2    ← 深度优先生效
```

**解决方案**：

检查是否有中间件或工具函数提前设置了 `request.meta['depth']`，确保 `depth` 仅由 Engine 传播：

```python
# ❌ 错误：中间件或工具函数不应提前注入 depth
def some_middleware(request, spider):
    request.meta.setdefault('depth', response.meta.get('depth', 0))  # 会导致 depth 传播失效

# ✅ 正确：让 Engine 自动传播 depth
def some_middleware(request, spider):
    # 不要设置 depth，Engine 会自动处理
    pass
```

> 提示：Engine 层 `_handle_spider_output` 统一管理 depth 传播，中间件或工具函数不应提前注入 depth。

## Ctrl+C 无法停止爬虫

### 问题：按 Ctrl+C 后爬虫继续运行

**解决方案**：

确保使用正确的关闭方法：

```python
# settings.py
CLOSE_SPIDER_ON_SIGNAL = True
```

查看 [爬虫生命周期](../concepts/spider-lifecycle.md) 了解关闭机制。

## 日志不输出

### 问题：运行时看不到日志

**解决方案**：

1. 检查日志级别
```python
# settings.py
LOG_LEVEL = 'DEBUG'  # 最详细
```

2. 检查日志输出
```python
# settings.py
LOG_FILE = 'spider.log'  # 输出到文件
LOG_TO_CONSOLE = True    # 同时输出到控制台
```

---

**还有其他问题？** 查看 [使用指南](../guides/) 或提交 [GitHub Issue](https://github.com/crawl-coder/Crawlo/issues)。
