# Request & Response 使用指南

## Request 对象

### 基础用法

```python
from crawlo.network import Request, RequestPriority

# 基础请求
request = Request(url="http://example.com")

# 带回调函数
request = Request(
    url="http://example.com",
    callback=self.parse_detail
)
```

---

## 工厂方法

### `Request.get()` - 创建 GET 请求

**使用场景**：
- 从 API 获取数据
- 抓取网页内容
- 带查询参数的请求

```python
# 简单 GET 请求
request = Request.get("http://example.com")

# 带查询参数（自动拼接 URL）
request = Request.get(
    "http://api.example.com/search",
    params={"q": "python", "page": 1, "limit": 20}
)
# URL: http://api.example.com/search?q=python&page=1&limit=20

# 带请求头和优先级
request = Request.get(
    "http://api.example.com/data",
    headers={"Authorization": "Bearer token"},
    priority=RequestPriority.HIGH,
    timeout=10.0
)
```

### `Request.post()` - 创建 POST 请求

**使用场景**：
- 提交 JSON 数据到 API
- 表单提交
- API 调用（创建资源、登录等）

```python
# 提交 JSON（自动序列化 + 设置 Content-Type）
request = Request.post(
    "http://api.example.com/users",
    json_body={"name": "John", "email": "john@example.com"}
)

# 提交表单（自动序列化）
request = Request.post(
    "http://example.com/login",
    form_data={"username": "admin", "password": "secret"}
)

# 带认证和代理
request = Request.post(
    "http://api.example.com/data",
    json_body={"key": "value"},
    headers={"Authorization": "Bearer token"},
    proxy="http://127.0.0.1:8080",
    timeout=30.0
)
```

---

## 序列化方法

### `to_dict()` - 序列化 Request

**使用场景**：
- **队列持久化**：Request 存入 Redis/磁盘队列
- **断点续爬**：保存未完成的请求到文件
- **日志记录**：记录请求详情用于调试
- **分布式传输**：跨节点传递 Request 对象

```python
import json
import redis
import pickle

# 场景 1: Redis 队列持久化
redis_client = redis.Redis()
request = Request.post("http://api.example.com", json_body={"key": "value"})

# 序列化后存入 Redis
redis_client.lpush("request_queue", json.dumps(request.to_dict()))

# 场景 2: 断点续爬
pending_requests = [
    Request.get("http://example.com/page1"),
    Request.get("http://example.com/page2"),
]

# 保存到文件
with open("pending.pkl", "wb") as f:
    pickle.dump([r.to_dict() for r in pending_requests], f)

# 场景 3: 日志记录
def log_request(request: Request):
    logger.info(f"Processing: {json.dumps(request.to_dict(), ensure_ascii=False)}")
```

### `from_dict()` - 反序列化 Request

**使用场景**：
- **队列消费**：从 Redis/磁盘读取请求后反序列化
- **断点恢复**：从文件恢复未完成的请求
- **API 接收**：从 HTTP API 接收请求配置
- **配置加载**：从配置文件批量创建请求

```python
# 场景 1: Redis 队列消费
data = redis_client.rpop("request_queue")
if data:
    request = Request.from_dict(json.loads(data))
    # 处理请求...

# 场景 2: 断点恢复
with open("pending.pkl", "rb") as f:
    restored = [Request.from_dict(d) for d in pickle.load(f)]

# 场景 3: 从配置文件加载
import json

with open("requests.json") as f:
    requests_data = json.load(f)

requests = [Request.from_dict(d) for d in requests_data]

# requests.json 示例:
# [
#   {"url": "http://example.com/api1", "method": "GET"},
#   {"url": "http://example.com/api2", "method": "POST", "json_body": {"key": "value"}}
# ]
```

---

## Response 工厂方法

### `Response.from_text()` - 从文本创建响应

**使用场景**：
- **测试**：创建模拟响应进行测试
- **本地处理**：处理本地 HTML 文件
- **中间件**：修改响应内容后重新创建

```python
from crawlo.network import Response

# 从 HTML 文本创建
response = Response.from_text(
    "http://example.com",
    "<html><body><h1>Test</h1></body></html>"
)

# 访问内容
print(response.text)  # <html><body><h1>Test</h1></body></html>
print(response.xpath("//h1/text()").get())  # Test
```

### `Response.from_json()` - 从 JSON 数据创建响应

**使用场景**：
- **API 测试**：测试 JSON API 的回调函数
- **数据转换**：将数据转换为响应格式
- **Mock 服务**：模拟 API 响应

```python
# 从 JSON 数据创建
response = Response.from_json(
    "http://api.example.com/users",
    {"name": "John", "email": "john@example.com"}
)

# 访问 JSON 数据
data = response.json()
print(data["name"])  # John

# 自动设置 Content-Type
print(response.headers["Content-Type"])  # application/json
```

---

## 实际应用场景

### 场景 1: 分布式爬虫任务分发

```python
# 主节点：创建请求并序列化
from crawlo.network import Request
import json
import redis

redis_client = redis.Redis()

urls = [
    "http://example.com/page1",
    "http://example.com/page2",
    "http://example.com/page3",
]

for url in urls:
    request = Request.get(url, priority=RequestPriority.NORMAL)
    redis_client.lpush("crawl_queue", json.dumps(request.to_dict()))

# 工作节点：消费请求并反序列化
while True:
    data = redis_client.rpop("crawl_queue")
    if not data:
        break
    
    request = Request.from_dict(json.loads(data))
    # 处理请求...
```

### 场景 2: 断点续爬

```python
import json
import os
from crawlo.network import Request

STATE_FILE = "crawl_state.json"

# 保存进度
def save_state(pending_requests):
    with open(STATE_FILE, "w") as f:
        json.dump([r.to_dict() for r in pending_requests], f)

# 恢复进度
def load_state():
    if not os.path.exists(STATE_FILE):
        return []
    
    with open(STATE_FILE) as f:
        return [Request.from_dict(d) for d in json.load(f)]

# 使用示例
pending = load_state()
if pending:
    print(f"恢复 {len(pending)} 个未完成的请求")
else:
    pending = [Request.get(f"http://example.com/page{i}") for i in range(100)]

for request in pending:
    # 处理请求...
    pass
```

### 场景 3: 请求日志与审计

```python
import json
import logging
from crawlo.network import Request

logger = logging.getLogger(__name__)

def log_request(request: Request):
    """记录请求详情用于审计"""
    log_data = request.to_dict()
    # 移除敏感信息
    log_data.pop("auth", None)
    
    logger.info(
        f"Request: {log_data['method']} {log_data['url']}",
        extra={"request": log_data}
    )

# 使用
request = Request.post(
    "http://api.example.com/data",
    json_body={"key": "value"},
    headers={"Authorization": "Bearer secret"}
)

log_request(request)
# 输出: Request: POST http://api.example.com/data (auth 已移除)
```

### 场景 4: 测试 Mock 响应

```python
import pytest
from crawlo.network import Response

def test_parse_user_data():
    # 创建模拟响应
    response = Response.from_json(
        "http://api.example.com/users/1",
        {
            "id": 1,
            "name": "John",
            "email": "john@example.com"
        }
    )
    
    # 测试解析函数
    result = parse_user_data(response)
    
    assert result["id"] == 1
    assert result["name"] == "John"

def test_parse_html_page():
    # 创建模拟 HTML 响应
    response = Response.from_text(
        "http://example.com/users",
        """
        <html>
            <body>
                <div class="user">User 1</div>
                <div class="user">User 2</div>
            </body>
        </html>
        """
    )
    
    # 测试 XPath 提取
    users = response.xpath("//div[@class='user']/text()").getall()
    assert len(users) == 2
    assert users[0] == "User 1"
```

---

## 最佳实践

### 1. 使用工厂方法简化代码

```python
# ✅ 推荐：使用工厂方法
request = Request.get("http://example.com", params={"page": 1})
request = Request.post("http://api.example.com", json_body={"key": "value"})

# ❌ 不推荐：手动指定 method
request = Request("http://example.com", method="GET", params={"page": 1})
request = Request("http://api.example.com", method="POST", json_body={"key": "value"})
```

### 2. 序列化时注意敏感信息

```python
# ✅ 推荐：移除敏感信息后再日志记录
log_data = request.to_dict()
log_data.pop("auth", None)
logger.info(json.dumps(log_data))

# ❌ 不推荐：直接记录包含认证信息的请求
logger.info(json.dumps(request.to_dict()))  # 可能泄露 token
```

### 3. 断点续爬时定期保存

```python
# ✅ 推荐：每处理 100 个请求保存一次
for i, request in enumerate(pending_requests):
    process(request)
    if i % 100 == 0:
        save_state(pending_requests[i:])

# ❌ 不推荐：只在最后保存
for request in pending_requests:
    process(request)
save_state([])  # 如果中间崩溃，进度丢失
```

### 4. 使用 `to_dict()` 进行请求去重

```python
import hashlib

def request_fingerprint(request: Request) -> str:
    """生成请求指纹"""
    data = request.to_dict()
    # 移除动态字段
    data.pop("priority", None)
    data.pop("timeout", None)
    
    # 生成 MD5
    return hashlib.md5(
        json.dumps(data, sort_keys=True).encode()
    ).hexdigest()

# 使用
seen = set()
for request in pending_requests:
    fp = request_fingerprint(request)
    if fp not in seen:
        seen.add(fp)
        process(request)
```

---

## 性能提示

| 操作 | 耗时 | 说明 |
|---|---|---|
| `Request.get()` | ~2 μs | 工厂方法开销极小 |
| `request.to_dict()` | ~5 μs | 序列化快速 |
| `Request.from_dict()` | ~8 μs | 反序列化略慢（需要创建对象） |
| `request.copy()` | ~2 μs | 深拷贝 |
| `copy.copy(request)` | ~0.5 μs | 浅拷贝（`__copy__`） |

**建议**：
- 高频场景使用浅拷贝 `copy.copy(request)`
- 需要修改 meta 时使用深拷贝 `request.copy()`
- 序列化操作适合队列存储，不适合高频调用
