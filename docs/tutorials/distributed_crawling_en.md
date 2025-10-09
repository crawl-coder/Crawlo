# Distributed Crawling Tutorial

This tutorial introduces how to set up and run a distributed crawler system using the Crawlo framework.

## Overview

A distributed crawler system processes tasks in parallel across multiple worker nodes, significantly improving crawling efficiency and the ability to handle large-scale data. Crawlo uses Redis as middleware for task queues and state sharing.

## Environment Setup

### Install Redis

Install Redis on the control node and all worker nodes:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install redis-server

# CentOS/RHEL
sudo yum install redis

# macOS
brew install redis
```

### Start Redis

```bash
# Start Redis service
sudo systemctl start redis

# Enable auto-start on boot
sudo systemctl enable redis
```

## Configure Distributed Environment

### Control Node Configuration

Create a configuration file for the control node `settings_control.py`:

```python
from crawlo.config import CrawloConfig

config = CrawloConfig.distributed(
    project_name='distributed_example',
    redis_host='192.168.1.100',      # Redis server address
    redis_port=6379,                 # Redis port
    redis_password='your_password',  # Redis password (if set)
    redis_db=0,                      # Redis database number
    concurrency=5,                   # Control node concurrency
    download_delay=1.0               # Download delay
)
```

### Worker Node Configuration

Create a configuration file for worker nodes `settings_worker.py`:

```python
from crawlo.config import CrawloConfig

config = CrawloConfig.distributed(
    project_name='distributed_example',
    redis_host='192.168.1.100',      # Redis server address
    redis_port=6379,                 # Redis port
    redis_password='your_password',  # Redis password (if set)
    redis_db=0,                      # Redis database number
    concurrency=20,                  # Worker node concurrency
    download_delay=0.5               # Download delay
)
```

## Create a Spider

Create a simple distributed spider `spiders/distributed_example.py`:

```python
from crawlo import Spider

class DistributedExampleSpider(Spider):
    name = 'distributed_example'
    start_urls = [
        'http://httpbin.org/get',
        'http://httpbin.org/headers',
        'http://httpbin.org/user-agent',
        # Add more URLs...
    ]
    
    def parse(self, response):
        yield {
            'url': response.url,
            'status_code': response.status_code,
            'content_length': len(response.text),
            'timestamp': response.meta.get('download_latency', 0)
        }
```

## Deploy Control Node

Execute the following steps on the control node:

```bash
# Create project
crawlo startproject distributed_crawling
cd distributed_crawling

# Copy configuration file
cp settings_control.py settings.py

# Start control node
crawlo run distributed_example --config settings.py
```

## Deploy Worker Nodes

Execute the following steps on each worker node:

```bash
# Clone project code
git clone https://github.com/your-org/distributed_crawling.git
cd distributed_crawling

# Copy configuration file
cp settings_worker.py settings.py

# Start worker node
crawlo run distributed_example --config settings.py
```

## Start Multiple Worker Nodes

You can start multiple worker nodes on the same machine or deploy across multiple machines:

```bash
# Terminal 1
crawlo run distributed_example --config settings_worker.py

# Terminal 2
crawlo run distributed_example --config settings_worker.py

# Terminal 3
crawlo run distributed_example --config settings_worker.py
```

## Monitoring and Management

### View Statistics

```bash
# View spider statistics
crawlo stats distributed_example

# View all spider list
crawlo list
```

### Redis Monitoring

```bash
# Monitor Redis performance
redis-cli info

# Monitor Redis memory usage
redis-cli info memory

# Monitor Redis connections
redis-cli info clients
```

## Performance Optimization

### Adjust Concurrency

Adjust concurrency based on network environment and target website capacity:

```python
# Control node - lower concurrency
config = CrawloConfig.distributed(concurrency=5)

# Worker node - higher concurrency
config = CrawloConfig.distributed(concurrency=30)
```

### Load Balancing

Configure different parameters for worker nodes with different performance:

```python
# High-performance node
config = CrawloConfig.distributed(
    concurrency=50,
    download_delay=0.1
)

# Medium-performance node
config = CrawloConfig.distributed(
    concurrency=20,
    download_delay=0.5
)

# Low-performance node (avoid being blocked)
config = CrawloConfig.distributed(
    concurrency=5,
    download_delay=2.0
)
```

## Troubleshooting

### Redis Connection Issues

```bash
# Check Redis service status
sudo systemctl status redis

# Test Redis connection
redis-cli -h 192.168.1.100 -p 6379 ping

# Check firewall settings
sudo ufw status
```

### Network Issues

```python
# Enable detailed logging
LOG_LEVEL = 'DEBUG'

# Check network connection
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = sock.connect_ex(('192.168.1.100', 6379))
if result == 0:
    print("Port open")
else:
    print("Port closed")
sock.close()
```

## Best Practices

### Security Configuration

```python
# Use strong password
REDIS_PASSWORD = 'strong_password_here'

# Restrict Redis access
BIND_ADDRESS = '192.168.1.100'  # Bind to internal network address only

# Enable Redis authentication
REQUIREPASS = 'your_strong_password'
```

### Resource Management

```python
# Reasonable concurrency settings
# Control node
config = CrawloConfig.distributed(concurrency=5)

# Worker node
config = CrawloConfig.distributed(concurrency=20)

# Set memory limit
MEMORY_LIMIT = '2GB'
```

### Fault Tolerance

```python
# Configure retry mechanism
MAX_RETRY_TIMES = 5
RETRY_STATUS_CODES = [500, 502, 503, 504, 429]

# Enable auto-retry extension
EXTENSIONS = [
    'crawlo.extensions.RetryExtension',
]
```

## Extended Deployment

### Docker Deployment

Create a Dockerfile:

```dockerfile
FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["crawlo", "run", "distributed_example"]
```

Build and run containers:

```bash
# Build image
docker build -t crawlo-distributed .

# Run control node
docker run -d --name control-node crawlo-distributed crawlo run distributed_example --config settings_control.py

# Run worker nodes
docker run -d --name worker-node1 crawlo-distributed crawlo run distributed_example --config settings_worker.py
docker run -d --name worker-node2 crawlo-distributed crawlo run distributed_example --config settings_worker.py
```

### Kubernetes Deployment

Create deployment configuration:

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

Through the above steps, you can successfully deploy and run a distributed crawler system, fully utilizing multi-node computing resources to improve crawling efficiency.