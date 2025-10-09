# 分布式爬虫教程

本教程将介绍如何使用 Crawlo 框架设置和运行分布式爬虫系统。

## 概述

分布式爬虫系统通过多个工作节点并行处理任务，能够显著提高爬取效率和处理大规模数据的能力。Crawlo 使用 Redis 作为任务队列和状态共享的中间件。

## 环境准备

### 安装 Redis

在控制节点和所有工作节点上安装 Redis：

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install redis-server

# CentOS/RHEL
sudo yum install redis

# macOS
brew install redis
```

### 启动 Redis

```bash
# 启动 Redis 服务
sudo systemctl start redis

# 设置开机自启
sudo systemctl enable redis
```

## 配置分布式环境

### 控制节点配置

创建控制节点的配置文件 `settings_control.py`：

```python
from crawlo.config import CrawloConfig

config = CrawloConfig.distributed(
    project_name='distributed_example',
    redis_host='192.168.1.100',      # Redis 服务器地址
    redis_port=6379,                 # Redis 端口
    redis_password='your_password',  # Redis 密码（如果设置）
    redis_db=0,                      # Redis 数据库编号
    concurrency=5,                   # 控制节点并发数
    download_delay=1.0               # 下载延迟
)
```

### 工作节点配置

创建工作节点的配置文件 `settings_worker.py`：

```python
from crawlo.config import CrawloConfig

config = CrawloConfig.distributed(
    project_name='distributed_example',
    redis_host='192.168.1.100',      # Redis 服务器地址
    redis_port=6379,                 # Redis 端口
    redis_password='your_password',  # Redis 密码（如果设置）
    redis_db=0,                      # Redis 数据库编号
    concurrency=20,                  # 工作节点并发数
    download_delay=0.5               # 下载延迟
)
```

## 创建爬虫

创建一个简单的分布式爬虫 `spiders/distributed_example.py`：

```python
from crawlo import Spider

class DistributedExampleSpider(Spider):
    name = 'distributed_example'
    start_urls = [
        'http://httpbin.org/get',
        'http://httpbin.org/headers',
        'http://httpbin.org/user-agent',
        # 添加更多URL...
    ]
    
    def parse(self, response):
        yield {
            'url': response.url,
            'status_code': response.status_code,
            'content_length': len(response.text),
            'timestamp': response.meta.get('download_latency', 0)
        }
```

## 部署控制节点

在控制节点上执行以下步骤：

```bash
# 创建项目
crawlo startproject distributed_crawling
cd distributed_crawling

# 复制配置文件
cp settings_control.py settings.py

# 启动控制节点
crawlo run distributed_example --config settings.py
```

## 部署工作节点

在每个工作节点上执行以下步骤：

```bash
# 克隆项目代码
git clone https://github.com/your-org/distributed_crawling.git
cd distributed_crawling

# 复制配置文件
cp settings_worker.py settings.py

# 启动工作节点
crawlo run distributed_example --config settings.py
```

## 启动多个工作节点

可以在同一台机器上启动多个工作节点，或在多台机器上部署：

```bash
# 终端 1
crawlo run distributed_example --config settings_worker.py

# 终端 2
crawlo run distributed_example --config settings_worker.py

# 终端 3
crawlo run distributed_example --config settings_worker.py
```

## 监控和管理

### 查看统计信息

```bash
# 查看爬虫统计信息
crawlo stats distributed_example

# 查看所有爬虫列表
crawlo list
```

### Redis 监控

```bash
# 监控 Redis 性能
redis-cli info

# 监控 Redis 内存使用
redis-cli info memory

# 监控 Redis 连接数
redis-cli info clients
```

## 性能优化

### 调整并发数

根据网络环境和目标网站的承受能力调整并发数：

```python
# 控制节点 - 较低并发数
config = CrawloConfig.distributed(concurrency=5)

# 工作节点 - 较高并发数
config = CrawloConfig.distributed(concurrency=30)
```

### 负载均衡

为不同性能的工作节点配置不同的参数：

```python
# 高性能节点
config = CrawloConfig.distributed(
    concurrency=50,
    download_delay=0.1
)

# 中等性能节点
config = CrawloConfig.distributed(
    concurrency=20,
    download_delay=0.5
)

# 低性能节点（避免被封）
config = CrawloConfig.distributed(
    concurrency=5,
    download_delay=2.0
)
```

## 故障排除

### Redis 连接问题

```bash
# 检查 Redis 服务状态
sudo systemctl status redis

# 测试 Redis 连接
redis-cli -h 192.168.1.100 -p 6379 ping

# 检查防火墙设置
sudo ufw status
```

### 网络问题

```python
# 启用详细日志
LOG_LEVEL = 'DEBUG'

# 检查网络连接
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = sock.connect_ex(('192.168.1.100', 6379))
if result == 0:
    print("端口开放")
else:
    print("端口关闭")
sock.close()
```

## 最佳实践

### 安全配置

```python
# 使用强密码
REDIS_PASSWORD = 'strong_password_here'

# 限制 Redis 访问
BIND_ADDRESS = '192.168.1.100'  # 只绑定内网地址

# 启用 Redis 认证
REQUIREPASS = 'your_strong_password'
```

### 资源管理

```python
# 合理设置并发数
# 控制节点
config = CrawloConfig.distributed(concurrency=5)

# 工作节点
config = CrawloConfig.distributed(concurrency=20)

# 设置内存限制
MEMORY_LIMIT = '2GB'
```

### 容错处理

```python
# 配置重试机制
MAX_RETRY_TIMES = 5
RETRY_STATUS_CODES = [500, 502, 503, 504, 429]

# 启用自动重试扩展
EXTENSIONS = [
    'crawlo.extensions.RetryExtension',
]
```

## 扩展部署

### Docker 部署

创建 Dockerfile：

```dockerfile
FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["crawlo", "run", "distributed_example"]
```

构建和运行容器：

```bash
# 构建镜像
docker build -t crawlo-distributed .

# 运行控制节点
docker run -d --name control-node crawlo-distributed crawlo run distributed_example --config settings_control.py

# 运行工作节点
docker run -d --name worker-node1 crawlo-distributed crawlo run distributed_example --config settings_worker.py
docker run -d --name worker-node2 crawlo-distributed crawlo run distributed_example --config settings_worker.py
```

### Kubernetes 部署

创建部署配置：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crawlo-worker
spec:
  replicas: 3
  selector:
    matchLabels:
      app: crawlo-worker
  template:
    metadata:
      labels:
        app: crawlo-worker
    spec:
      containers:
      - name: worker
        image: crawlo-distributed:latest
        env:
        - name: REDIS_HOST
          value: "redis-service"
        - name: CONCURRENCY
          value: "20"
```

通过以上步骤，您可以成功部署和运行一个分布式爬虫系统，充分利用多节点的计算资源来提高爬取效率。