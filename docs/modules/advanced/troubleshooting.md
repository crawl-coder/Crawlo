# 故障排除

在使用 Crawlo 框架过程中可能会遇到各种问题，本文档提供常见问题的诊断和解决方案，帮助用户快速定位和解决问题。

## 概述

故障排除是爬虫开发和运维中的重要环节。通过系统性的诊断方法和丰富的调试工具，可以快速识别和解决各种技术问题。

### 常见问题类型

1. **网络连接问题** - 无法访问目标网站或连接超时
2. **配置错误** - 配置文件格式错误或参数设置不当
3. **数据处理问题** - 解析失败或数据格式错误
4. **性能问题** - 爬取速度慢或资源消耗过高
5. **分布式问题** - 节点间通信失败或数据不一致
6. **环境问题** - 依赖缺失或版本冲突

## 网络连接问题

### 连接超时

```python
# 增加超时时间
config = CrawloConfig.standalone(
    download_timeout=60,  # 增加到60秒
    retry_times=3         # 增加重试次数
)

# 检查网络连接
import socket

def check_connection(host, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False

# 使用示例
if not check_connection('example.com', 80):
    print("无法连接到 example.com")
```

### SSL 证书问题

```python
# 忽略 SSL 证书验证（仅用于测试）
config = CrawloConfig.standalone(
    ssl_verify=False
)

# 或者使用自定义 SSL 上下文
import ssl

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

config = CrawloConfig.standalone(
    ssl_context=ssl_context
)
```

### 代理问题

```python
# 配置代理
config = CrawloConfig.standalone(
    proxy='http://proxy.example.com:8080'
)

# 使用代理列表轮换
PROXY_LIST = [
    'http://proxy1.example.com:8080',
    'http://proxy2.example.com:8080',
    'http://proxy3.example.com:8080'
]

# 自定义代理中间件
class RotatingProxyMiddleware:
    def __init__(self, settings):
        self.proxy_list = settings.PROXY_LIST
        self.current_proxy = 0
    
    def process_request(self, request, spider):
        if self.proxy_list:
            proxy = self.proxy_list[self.current_proxy]
            request.proxy = proxy
            self.current_proxy = (self.current_proxy + 1) % len(self.proxy_list)
        return request
```

## 配置问题

### 配置文件验证

```python
from crawlo.config_validator import validate_config

# 验证配置
is_valid, errors, warnings = validate_config(settings_dict)

if not is_valid:
    print("配置验证失败:")
    for error in errors:
        print(f"  ❌ {error}")
    
    if warnings:
        print("警告:")
        for warning in warnings:
            print(f"  ⚠️  {warning}")
```

### 环境变量覆盖

```python
# 检查环境变量
import os

def check_env_vars():
    required_vars = ['CRAWLO_CONCURRENCY', 'CRAWLO_DOWNLOAD_DELAY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"缺少环境变量: {', '.join(missing_vars)}")

# 使用示例
check_env_vars()
```

## 数据处理问题

### 解析错误

```python
class RobustSpider(Spider):
    def parse(self, response):
        try:
            # 安全的数据提取
            title = response.extract_text('title') or '未知标题'
            price = response.extract_text('.price')
            
            # 数据验证
            if not price:
                self.logger.warning(f"页面缺少价格信息: {response.url}")
                return
            
            # 数据转换
            try:
                price_float = float(price.replace('¥', '').strip())
            except ValueError:
                self.logger.error(f"价格格式错误: {price}")
                return
            
            yield Item(
                title=title,
                price=price_float
            )
            
        except Exception as e:
            self.logger.error(f"解析页面失败 {response.url}: {e}")
            # 可以选择重试或跳过
```

### 编码问题

```python
# 处理编码问题
class EncodingSpider(Spider):
    def parse(self, response):
        # 检查响应编码
        encoding = response.encoding
        self.logger.debug(f"响应编码: {encoding}")
        
        # 如果编码不正确，手动指定
        if encoding.lower() not in ['utf-8', 'utf8']:
            response.encoding = 'utf-8'
        
        # 处理解码后的内容
        text = response.text
```

## 性能问题

### 内存泄漏

```python
import gc
import psutil
import weakref

class MemoryLeakDetector:
    def __init__(self):
        self.objects = weakref.WeakSet()
    
    def track_object(self, obj):
        self.objects.add(obj)
    
    def check_leaks(self):
        # 强制垃圾回收
        gc.collect()
        
        # 检查内存使用
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        if memory_mb > 500:  # 500MB 阈值
            self.logger.warning(f"内存使用过高: {memory_mb:.2f}MB")
            # 分析对象引用
            self.analyze_objects()
    
    def analyze_objects(self):
        # 分析可能的内存泄漏对象
        import objgraph
        objgraph.show_most_common_types(limit=20)
```

### CPU 使用过高

```python
import asyncio
import time

class CPUMonitor:
    def __init__(self, threshold=80):
        self.threshold = threshold
        self.monitoring = False
    
    async def start_monitoring(self):
        self.monitoring = True
        while self.monitoring:
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > self.threshold:
                self.logger.warning(f"CPU 使用率过高: {cpu_percent}%")
                # 可以采取降频措施
                await self.throttle()
            await asyncio.sleep(10)
    
    async def throttle(self):
        # 临时降低并发数
        original_concurrency = self.settings.CONCURRENCY
        self.settings.CONCURRENCY = max(1, original_concurrency // 2)
        self.logger.info("已降低并发数以减少 CPU 使用")
        
        # 等待一段时间后恢复
        await asyncio.sleep(60)
        self.settings.CONCURRENCY = original_concurrency
        self.logger.info("已恢复原始并发数")
```

## 分布式问题

### Redis 连接问题

```python
import redis
import time

class RedisHealthChecker:
    def __init__(self, redis_config):
        self.redis_config = redis_config
        self.client = None
    
    def connect(self):
        try:
            self.client = redis.Redis(
                host=self.redis_config['host'],
                port=self.redis_config['port'],
                password=self.redis_config.get('password'),
                db=self.redis_config.get('db', 0),
                socket_timeout=5
            )
            # 测试连接
            self.client.ping()
            return True
        except Exception as e:
            self.logger.error(f"Redis 连接失败: {e}")
            return False
    
    def check_health(self):
        if not self.client:
            return False
        
        try:
            # 检查 Redis 状态
            info = self.client.info()
            self.logger.debug(f"Redis 内存使用: {info['used_memory_human']}")
            self.logger.debug(f"Redis 连接数: {info['connected_clients']}")
            return True
        except Exception as e:
            self.logger.error(f"Redis 健康检查失败: {e}")
            return False
```

### 节点通信问题

```python
import asyncio
import hashlib

class NodeCommunicator:
    def __init__(self, node_id, redis_client):
        self.node_id = node_id
        self.redis_client = redis_client
        self.heartbeat_key = f"node:{node_id}:heartbeat"
    
    async def send_heartbeat(self):
        """发送心跳信号"""
        try:
            timestamp = int(time.time())
            self.redis_client.setex(
                self.heartbeat_key,
                60,  # 60秒过期
                timestamp
            )
        except Exception as e:
            self.logger.error(f"发送心跳失败: {e}")
    
    async def check_nodes(self):
        """检查其他节点状态"""
        try:
            keys = self.redis_client.keys("node:*:heartbeat")
            active_nodes = []
            
            for key in keys:
                ttl = self.redis_client.ttl(key)
                if ttl > 0:
                    node_id = key.decode().split(':')[1]
                    active_nodes.append(node_id)
            
            self.logger.info(f"活跃节点: {active_nodes}")
            return active_nodes
        except Exception as e:
            self.logger.error(f"检查节点状态失败: {e}")
            return []
```

## 日志和调试

### 详细日志配置

```python
# 启用详细日志
config = CrawloConfig.standalone(
    log_level='DEBUG',
    log_file='debug.log',
    log_max_bytes=10*1024*1024,  # 10MB
    log_backup_count=5
)

# 自定义日志格式
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
```

### 调试中间件

```python
class DebuggingMiddleware:
    def __init__(self, settings):
        self.logger = logging.getLogger('debug.middleware')
    
    def process_request(self, request, spider):
        self.logger.debug(f"发送请求: {request.url}")
        self.logger.debug(f"请求头部: {request.headers}")
        return request
    
    def process_response(self, request, response, spider):
        self.logger.debug(f"收到响应: {response.url}")
        self.logger.debug(f"状态码: {response.status_code}")
        self.logger.debug(f"响应大小: {len(response.content)} bytes")
        return response
    
    def process_exception(self, request, exception, spider):
        self.logger.error(f"请求异常: {request.url}")
        self.logger.error(f"异常详情: {exception}")
        return None
```

## 监控和告警

### 健康检查

```python
class HealthChecker:
    def __init__(self, crawler):
        self.crawler = crawler
        self.checks = [
            self.check_network,
            self.check_storage,
            self.check_memory,
            self.check_cpu
        ]
    
    async def run_health_check(self):
        results = []
        for check in self.checks:
            try:
                result = await check()
                results.append(result)
            except Exception as e:
                results.append({'name': check.__name__, 'status': 'ERROR', 'error': str(e)})
        
        # 汇总检查结果
        healthy = all(result['status'] == 'OK' for result in results)
        return healthy, results
    
    async def check_network(self):
        # 检查网络连接
        return {'name': 'network', 'status': 'OK'}
    
    async def check_storage(self):
        # 检查存储空间
        import shutil
        total, used, free = shutil.disk_usage("/")
        if free < 1024*1024*1024:  # 少于1GB
            return {'name': 'storage', 'status': 'WARNING', 'message': '存储空间不足'}
        return {'name': 'storage', 'status': 'OK'}
    
    async def check_memory(self):
        # 检查内存使用
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        if memory_mb > 800:
            return {'name': 'memory', 'status': 'WARNING', 'message': f'内存使用过高: {memory_mb:.2f}MB'}
        return {'name': 'memory', 'status': 'OK'}
    
    async def check_cpu(self):
        # 检查CPU使用
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 90:
            return {'name': 'cpu', 'status': 'WARNING', 'message': f'CPU使用率过高: {cpu_percent}%'}
        return {'name': 'cpu', 'status': 'OK'}
```

### 告警机制

```python
class AlertManager:
    def __init__(self, alert_thresholds):
        self.alert_thresholds = alert_thresholds
        self.alert_history = {}
    
    def check_and_alert(self, metric_name, value):
        threshold = self.alert_thresholds.get(metric_name)
        if threshold and value > threshold:
            # 检查是否需要发送告警（避免重复告警）
            last_alert = self.alert_history.get(metric_name, 0)
            current_time = time.time()
            
            # 如果距离上次告警超过5分钟，则发送新告警
            if current_time - last_alert > 300:
                self.send_alert(metric_name, value, threshold)
                self.alert_history[metric_name] = current_time
    
    def send_alert(self, metric_name, value, threshold):
        message = f"告警: {metric_name} 超过阈值 {threshold}, 当前值: {value}"
        self.logger.error(message)
        
        # 可以集成邮件、短信、微信等告警方式
        # send_email_alert(message)
        # send_sms_alert(message)
```

## 最佳实践

### 1. 系统化诊断

```python
class DiagnosticTool:
    def __init__(self):
        self.diagnostic_steps = [
            self.check_configuration,
            self.check_network,
            self.check_dependencies,
            self.check_permissions,
            self.check_resources
        ]
    
    def run_diagnostics(self):
        print("开始系统诊断...")
        for step in self.diagnostic_steps:
            print(f"执行检查: {step.__name__}")
            try:
                result = step()
                if result:
                    print(f"  ✅ {step.__name__}: 通过")
                else:
                    print(f"  ❌ {step.__name__}: 失败")
            except Exception as e:
                print(f"  ❌ {step.__name__}: 错误 - {e}")
        print("诊断完成")
```

### 2. 渐进式调试

```python
# 从简单配置开始调试
SIMPLE_CONFIG = CrawloConfig.standalone(
    concurrency=1,
    log_level='DEBUG'
)

# 逐步增加复杂度
MEDIUM_CONFIG = CrawloConfig.standalone(
    concurrency=5,
    downloader_type='aiohttp'
)

# 完整配置
FULL_CONFIG = CrawloConfig.standalone(
    concurrency=20,
    downloader_type='aiohttp',
    middlewares=['proxy', 'retry']
)
```

通过以上故障排除方法和工具，可以快速识别和解决 Crawlo 爬虫开发和运行过程中遇到的各种问题。建议在遇到问题时按照从简单到复杂的顺序进行排查，并充分利用日志和监控工具来辅助诊断。