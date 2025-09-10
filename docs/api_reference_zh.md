# Crawlo API 参考文档

## 目录
- [核心组件](#核心组件)
- [网络](#网络)
- [下载器](#下载器)
- [中间件](#中间件)
- [工具](#工具)
- [工具类](#工具类)

## 核心组件

### Spider
所有爬虫的基类。

#### 方法
- `__init__(self, name: str = None, **kwargs)` - 初始化爬虫
- `start_requests(self) -> Iterator[Request]` - 生成初始请求
- `parse(self, response)` - 解析响应（必须实现）
- `spider_opened(self)` - 爬虫启动时调用
- `spider_closed(self)` - 爬虫结束时调用

#### 属性
- `name: str` - 爬虫名称（必需）
- `start_urls: List[str]` - 初始URL列表
- `custom_settings: Dict[str, Any]` - 自定义配置
- `allowed_domains: List[str]` - 允许的域名列表

### Request
HTTP请求封装类，功能丰富。

#### 构造函数
```python
Request(
    url: str,
    callback: Optional[Callable] = None,
    method: str = 'GET',
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Union[bytes, str, Dict[Any, Any]]] = None,
    form_data: Optional[Dict[Any, Any]] = None,
    json_body: Optional[Dict[Any, Any]] = None,
    cb_kwargs: Optional[Dict[str, Any]] = None,
    cookies: Optional[Dict[str, str]] = None,
    meta: Optional[Dict[str, Any]] = None,
    priority: int = 0,
    dont_filter: bool = False,
    timeout: Optional[float] = None,
    proxy: Optional[str] = None,
    allow_redirects: bool = True,
    auth: Optional[tuple] = None,
    verify: bool = True,
    flags: Optional[List[str]] = None,
    encoding: str = 'utf-8'
)
```

#### 方法
- `copy(self) -> Request` - 创建副本
- `set_meta(self, key: str, value: Any) -> Request` - 设置元数据
- `add_header(self, key: str, value: str) -> Request` - 添加请求头
- `add_headers(self, headers: Dict[str, str]) -> Request` - 批量添加请求头
- `set_proxy(self, proxy: str) -> Request` - 设置代理
- `set_timeout(self, timeout: float) -> Request` - 设置超时时间
- `add_flag(self, flag: str) -> Request` - 添加标记
- `remove_flag(self, flag: str) -> Request` - 移除标记

#### 属性
- `url: str` - 请求URL
- `meta: Dict[str, Any]` - 元数据
- `headers: Dict[str, str]` - 请求头

### Response
HTTP响应封装类。

#### 构造函数
```python
Response(
    url: str,
    headers: Dict[str, str],
    status_code: int,
    body: bytes,
    request: Request
)
```

#### 方法
- `css(self, query: str)` - CSS选择器
- `xpath(self, query: str)` - XPath选择器
- `extract_text(self, query: str, first: bool = True) -> Union[str, List[str]]` - 提取文本
- `extract_texts(self, query: str) -> List[str]` - 提取所有文本
- `extract_attr(self, query: str, attr: str, first: bool = True) -> Union[str, List[str]]` - 提取属性
- `extract_attrs(self, query: str, attr: str) -> List[str]` - 提取所有属性

#### 属性
- `url: str` - 响应URL
- `headers: Dict[str, str]` - 响应头
- `status_code: int` - HTTP状态码
- `body: bytes` - 响应体
- `text: str` - 响应体文本
- `title: str` - 页面标题

## 网络

### 请求优先级常量
- `RequestPriority.URGENT = -200` - 紧急
- `RequestPriority.HIGH = -100` - 高优先级
- `RequestPriority.NORMAL = 0` - 正常优先级
- `RequestPriority.LOW = 100` - 低优先级
- `RequestPriority.BACKGROUND = 200` - 后台任务

## 下载器

### 支持的下载器
1. `aiohttp` - 高性能异步HTTP客户端
2. `httpx` - 现代异步HTTP客户端，支持HTTP/2
3. `curl_cffi` - 基于curl的下载器，支持浏览器指纹模拟
4. `selenium` - 浏览器自动化，用于动态内容
5. `playwright` - 高性能浏览器自动化

### 下载器配置
```python
# 在 settings.py 或 Spider.custom_settings 中配置
custom_settings = {
    'DOWNLOADER_TYPE': 'httpx',  # 或 'aiohttp', 'curl_cffi', 'selenium', 'playwright'
    'DOWNLOAD_DELAY': 1,
    'DOWNLOAD_TIMEOUT': 30,
    'CONNECTION_POOL_LIMIT': 100,
}
```

## 中间件

### ProxyMiddleware
代理支持，支持自动轮换。

#### 配置
```python
# 在 settings.py 中配置
custom_settings = {
    'MIDDLEWARES': [
        'crawlo.middleware.proxy.ProxyMiddleware',
        # ... 其他中间件
    ],
    'PROXY_ENABLED': True,
    'PROXY_API_URL': 'https://api.proxyprovider.com/get',
    'PROXY_EXTRACTOR': 'proxy',
    'PROXY_REFRESH_INTERVAL': 60,
}
```

### RetryMiddleware
自动重试，支持指数退避。

#### 配置
```python
custom_settings = {
    'RETRY_TIMES': 3,
    'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429],
}
```

## 工具

### 日期工具
```python
from crawlo.tools import parse_time, format_time, time_diff

# 解析时间
dt = parse_time("2023-01-01 12:00:00")

# 格式化时间
formatted = format_time(dt, "%Y-%m-%d %H:%M:%S")

# 时间差
diff = time_diff(dt2, dt1)  # 秒
```

### 数据清洗工具
```python
from crawlo.tools import clean_text, format_currency, extract_emails

# 清洗HTML文本
clean = clean_text("<p>Hello&nbsp;World</p>")  # "Hello World"

# 格式化货币
formatted = format_currency(1234.56, "¥", 2)  # "¥1,234.56"

# 提取邮箱
emails = extract_emails("联系: test@example.com")  # ["test@example.com"]
```

### 数据验证工具
```python
from crawlo.tools import validate_email, validate_url, validate_phone

# 验证邮箱
is_valid = validate_email("test@example.com")  # True

# 验证URL
is_valid = validate_url("https://example.com")  # True

# 验证电话
is_valid = validate_phone("13812345678")  # True
```

### 带认证代理工具
```python
from crawlo.tools import AuthenticatedProxy, create_proxy_config

# 创建带认证代理
proxy = AuthenticatedProxy("http://username:password@proxy.example.com:8080")

# 获取不带认证信息的URL
clean_url = proxy.clean_url  # "http://proxy.example.com:8080"

# 获取认证凭据
auth = proxy.get_auth_credentials()  # {"username": "username", "password": "password"}

# 为不同下载器获取代理配置
config = create_proxy_config("http://username:password@proxy.example.com:8080")
aiohttp_config = format_proxy_for_request(config, "aiohttp")
httpx_config = format_proxy_for_request(config, "httpx")
curl_config = format_proxy_for_request(config, "curl_cffi")
```

### 重试机制
```python
from crawlo.tools import retry, exponential_backoff

# 重试装饰器
@retry(max_retries=3)
def fetch_data():
    # ... 某些网络操作
    pass

# 指数退避
delay = exponential_backoff(attempt_number)  # 秒
```

### 反爬虫工具
```python
from crawlo.tools import AntiCrawler, get_random_user_agent

# 获取随机User-Agent
ua = get_random_user_agent()

# 反爬虫工具包
anti_crawler = AntiCrawler()
proxy = anti_crawler.rotate_proxy()
has_captcha = anti_crawler.handle_captcha(response_text)
is_rate_limited = anti_crawler.detect_rate_limiting(status_code, headers)
```

### 分布式协调工具
```python
from crawlo.tools import DistributedCoordinator, generate_pagination_tasks

# 生成分页任务
tasks = generate_pagination_tasks("https://api.example.com/items", 1, 100)

# 分布式协调器
coordinator = DistributedCoordinator()
task_id = coordinator.generate_task_id(url, spider_name)
is_duplicate = await coordinator.is_duplicate(item_data)
```

## 工具类

### 日志工具
```python
from crawlo.utils.log import get_logger

logger = get_logger(__name__)
logger.info("消息")
```

### URL工具
```python
from crawlo.utils.url import escape_ajax, add_url_param

# 转义AJAX URL
escaped = escape_ajax("#!hashbang")

# 添加URL参数
url_with_params = add_url_param("https://example.com", {"key": "value"})
```

### 环境配置工具
```python
from crawlo.utils.env_config import get_runtime_config, get_redis_config

# 获取运行时配置
runtime_config = get_runtime_config()

# 获取Redis配置
redis_config = get_redis_config()
```