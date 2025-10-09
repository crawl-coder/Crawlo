# Troubleshooting

Various issues may arise when using the Crawlo framework. This document provides diagnosis and solutions for common problems to help users quickly identify and resolve issues.

## Overview

Troubleshooting is an important aspect of crawler development and operations. Through systematic diagnostic methods and rich debugging tools, various technical issues can be quickly identified and resolved.

### Common Problem Types

1. **Network Connection Issues** - Unable to access target websites or connection timeouts
2. **Configuration Errors** - Configuration file format errors or improper parameter settings
3. **Data Processing Issues** - Parsing failures or data format errors
4. **Performance Issues** - Slow crawling or high resource consumption
5. **Distributed Issues** - Node communication failures or data inconsistency
6. **Environment Issues** - Missing dependencies or version conflicts

## Network Connection Issues

### Connection Timeout

```python
# Increase timeout
config = CrawloConfig.standalone(
    download_timeout=60,  # Increase to 60 seconds
    retry_times=3         # Increase retry attempts
)

# Check network connection
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

# Usage example
if not check_connection('example.com', 80):
    print("Cannot connect to example.com")
```

### SSL Certificate Issues

```python
# Ignore SSL certificate verification (for testing only)
config = CrawloConfig.standalone(
    ssl_verify=False
)

# Or use custom SSL context
import ssl

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

config = CrawloConfig.standalone(
    ssl_context=ssl_context
)
```

### Proxy Issues

```python
# Configure proxy
config = CrawloConfig.standalone(
    proxy='http://proxy.example.com:8080'
)

# Use proxy list rotation
PROXY_LIST = [
    'http://proxy1.example.com:8080',
    'http://proxy2.example.com:8080',
    'http://proxy3.example.com:8080'
]

# Custom proxy middleware
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

## Configuration Issues

### Configuration File Validation

```python
from crawlo.config_validator import validate_config

# Validate configuration
is_valid, errors, warnings = validate_config(settings_dict)

if not is_valid:
    print("Configuration validation failed:")
    for error in errors:
        print(f"  ❌ {error}")
    
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"  ⚠️  {warning}")
```

### Environment Variable Override

```python
# Check environment variables
import os

def check_env_vars():
    required_vars = ['CRAWLO_CONCURRENCY', 'CRAWLO_DOWNLOAD_DELAY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"Missing environment variables: {', '.join(missing_vars)}")

# Usage example
check_env_vars()
```

## Data Processing Issues

### Parsing Errors

```python
class RobustSpider(Spider):
    def parse(self, response):
        try:
            # Safe data extraction
            title = response.extract_text('title') or 'Unknown Title'
            price = response.extract_text('.price')
            
            # Data validation
            if not price:
                self.logger.warning(f"Page missing price information: {response.url}")
                return
            
            # Data conversion
            try:
                price_float = float(price.replace('¥', '').strip())
            except ValueError:
                self.logger.error(f"Price format error: {price}")
                return
            
            yield Item(
                title=title,
                price=price_float
            )
            
        except Exception as e:
            self.logger.error(f"Failed to parse page {response.url}: {e}")
            # Can choose to retry or skip
```

### Encoding Issues

```python
# Handle encoding issues
class EncodingSpider(Spider):
    def parse(self, response):
        # Check response encoding
        encoding = response.encoding
        self.logger.debug(f"Response encoding: {encoding}")
        
        # If encoding is incorrect, specify manually
        if encoding.lower() not in ['utf-8', 'utf8']:
            response.encoding = 'utf-8'
        
        # Process decoded content
        text = response.text
```

## Performance Issues

### Memory Leaks

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
        # Force garbage collection
        gc.collect()
        
        # Check memory usage
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        if memory_mb > 500:  # 500MB threshold
            self.logger.warning(f"High memory usage: {memory_mb:.2f}MB")
            # Analyze object references
            self.analyze_objects()
    
    def analyze_objects(self):
        # Analyze potential memory leak objects
        import objgraph
        objgraph.show_most_common_types(limit=20)
```

### High CPU Usage

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
                self.logger.warning(f"High CPU usage: {cpu_percent}%")
                # Can take throttling measures
                await self.throttle()
            await asyncio.sleep(10)
    
    async def throttle(self):
        # Temporarily reduce concurrency
        original_concurrency = self.settings.CONCURRENCY
        self.settings.CONCURRENCY = max(1, original_concurrency // 2)
        self.logger.info("Reduced concurrency to reduce CPU usage")
        
        # Wait for a while then restore
        await asyncio.sleep(60)
        self.settings.CONCURRENCY = original_concurrency
        self.logger.info("Restored original concurrency")
```

## Distributed Issues

### Redis Connection Issues

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
            # Test connection
            self.client.ping()
            return True
        except Exception as e:
            self.logger.error(f"Redis connection failed: {e}")
            return False
    
    def check_health(self):
        if not self.client:
            return False
        
        try:
            # Check Redis status
            info = self.client.info()
            self.logger.debug(f"Redis memory usage: {info['used_memory_human']}")
            self.logger.debug(f"Redis connections: {info['connected_clients']}")
            return True
        except Exception as e:
            self.logger.error(f"Redis health check failed: {e}")
            return False
```

### Node Communication Issues

```python
import asyncio
import hashlib

class NodeCommunicator:
    def __init__(self, node_id, redis_client):
        self.node_id = node_id
        self.redis_client = redis_client
        self.heartbeat_key = f"node:{node_id}:heartbeat"
    
    async def send_heartbeat(self):
        """Send heartbeat signal"""
        try:
            timestamp = int(time.time())
            self.redis_client.setex(
                self.heartbeat_key,
                60,  # Expire in 60 seconds
                timestamp
            )
        except Exception as e:
            self.logger.error(f"Failed to send heartbeat: {e}")
    
    async def check_nodes(self):
        """Check other nodes' status"""
        try:
            keys = self.redis_client.keys("node:*:heartbeat")
            active_nodes = []
            
            for key in keys:
                ttl = self.redis_client.ttl(key)
                if ttl > 0:
                    node_id = key.decode().split(':')[1]
                    active_nodes.append(node_id)
            
            self.logger.info(f"Active nodes: {active_nodes}")
            return active_nodes
        except Exception as e:
            self.logger.error(f"Failed to check node status: {e}")
            return []
```

## Logging and Debugging

### Detailed Logging Configuration

```python
# Enable detailed logging
config = CrawloConfig.standalone(
    log_level='DEBUG',
    log_file='debug.log',
    log_max_bytes=10*1024*1024,  # 10MB
    log_backup_count=5
)

# Custom log format
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
```

### Debugging Middleware

```python
class DebuggingMiddleware:
    def __init__(self, settings):
        self.logger = logging.getLogger('debug.middleware')
    
    def process_request(self, request, spider):
        self.logger.debug(f"Sending request: {request.url}")
        self.logger.debug(f"Request headers: {request.headers}")
        return request
    
    def process_response(self, request, response, spider):
        self.logger.debug(f"Received response: {response.url}")
        self.logger.debug(f"Status code: {response.status_code}")
        self.logger.debug(f"Response size: {len(response.content)} bytes")
        return response
    
    def process_exception(self, request, exception, spider):
        self.logger.error(f"Request exception: {request.url}")
        self.logger.error(f"Exception details: {exception}")
        return None
```

## Monitoring and Alerting

### Health Check

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
        
        # Summarize check results
        healthy = all(result['status'] == 'OK' for result in results)
        return healthy, results
    
    async def check_network(self):
        # Check network connection
        return {'name': 'network', 'status': 'OK'}
    
    async def check_storage(self):
        # Check storage space
        import shutil
        total, used, free = shutil.disk_usage("/")
        if free < 1024*1024*1024:  # Less than 1GB
            return {'name': 'storage', 'status': 'WARNING', 'message': 'Insufficient storage space'}
        return {'name': 'storage', 'status': 'OK'}
    
    async def check_memory(self):
        # Check memory usage
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        if memory_mb > 800:
            return {'name': 'memory', 'status': 'WARNING', 'message': f'High memory usage: {memory_mb:.2f}MB'}
        return {'name': 'memory', 'status': 'OK'}
    
    async def check_cpu(self):
        # Check CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 90:
            return {'name': 'cpu', 'status': 'WARNING', 'message': f'High CPU usage: {cpu_percent}%'}
        return {'name': 'cpu', 'status': 'OK'}
```

### Alerting Mechanism

```python
class AlertManager:
    def __init__(self, alert_thresholds):
        self.alert_thresholds = alert_thresholds
        self.alert_history = {}
    
    def check_and_alert(self, metric_name, value):
        threshold = self.alert_thresholds.get(metric_name)
        if threshold and value > threshold:
            # Check if alert needs to be sent (avoid duplicate alerts)
            last_alert = self.alert_history.get(metric_name, 0)
            current_time = time.time()
            
            # Send new alert if more than 5 minutes since last alert
            if current_time - last_alert > 300:
                self.send_alert(metric_name, value, threshold)
                self.alert_history[metric_name] = current_time
    
    def send_alert(self, metric_name, value, threshold):
        message = f"Alert: {metric_name} exceeded threshold {threshold}, current value: {value}"
        self.logger.error(message)
        
        # Can integrate email, SMS, WeChat and other alerting methods
        # send_email_alert(message)
        # send_sms_alert(message)
```

## Best Practices

### 1. Systematic Diagnosis

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
        print("Starting system diagnostics...")
        for step in self.diagnostic_steps:
            print(f"Running check: {step.__name__}")
            try:
                result = step()
                if result:
                    print(f"  ✅ {step.__name__}: Passed")
                else:
                    print(f"  ❌ {step.__name__}: Failed")
            except Exception as e:
                print(f"  ❌ {step.__name__}: Error - {e}")
        print("Diagnostics completed")
```

### 2. Progressive Debugging

```python
# Start debugging with simple configuration
SIMPLE_CONFIG = CrawloConfig.standalone(
    concurrency=1,
    log_level='DEBUG'
)

# Gradually increase complexity
MEDIUM_CONFIG = CrawloConfig.standalone(
    concurrency=5,
    downloader_type='aiohttp'
)

# Full configuration
FULL_CONFIG = CrawloConfig.standalone(
    concurrency=20,
    downloader_type='aiohttp',
    middlewares=['proxy', 'retry']
)
```

Through the above troubleshooting methods and tools, various issues encountered during Crawlo crawler development and operation can be quickly identified and resolved. It is recommended to troubleshoot in order from simple to complex when encountering problems, and make full use of logs and monitoring tools to assist in diagnosis.