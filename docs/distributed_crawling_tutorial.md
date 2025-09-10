# Distributed Crawling Tutorial

This tutorial will guide you through setting up and running a distributed crawling system with Crawlo.

## Prerequisites

- Crawlo framework installed
- Redis server accessible
- Multiple machines or processes for distributed crawling

## Setting Up Redis

### Installing Redis Locally

#### Windows
Download Redis for Windows from the official website or use Docker:

```bash
docker run -d -p 6379:6379 --name redis-crawlo redis:alpine
```

#### Linux
```bash
sudo apt-get install redis-server
```

#### macOS
```bash
brew install redis
```

### Starting Redis

```bash
redis-server
```

Verify Redis is running:
```bash
redis-cli ping
# Should return: PONG
```

## Configuring Your Project for Distributed Crawling

### Update settings.py

In your project's `settings.py` file, add the following distributed configuration:

```python
# Distributed mode configuration
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis'

# Concurrency settings for distributed mode
CONCURRENCY = 16
DOWNLOAD_DELAY = 1.0

# Scheduler configuration
SCHEDULER = 'crawlo.scheduler.redis_scheduler.RedisScheduler'

# Redis configuration
REDIS_HOST = '127.0.0.1'  # Change to your Redis server IP
REDIS_PORT = 6379
REDIS_PASSWORD = ''  # Set if your Redis requires a password
REDIS_DB = 2  # Redis database number
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# Distributed deduplication
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'
REDIS_KEY = 'myproject:fingerprint'  # Change to your project name

# Additional distributed settings
SCHEDULER_QUEUE_NAME = 'myproject:requests'
REDIS_TTL = 0  # Fingerprint expiration (0 = never expire)
CLEANUP_FP = False  # Whether to clean up fingerprints on shutdown
```

### Update run.py

Ensure your `run.py` file properly handles distributed mode:

```python
#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import sys
import asyncio
import argparse
from pathlib import Path

# Add project path to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from crawlo.crawler import CrawlerProcess
    from myproject.spiders.myspider import MySpider
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure you're running this script from the project root directory")
    sys.exit(1)

def create_parser():
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(description='Distributed Crawlo Spider Runner')
    
    parser.add_argument('spider_name', nargs='?', default='myspider',
                        help='Spider name to run (default: myspider)')
    
    parser.add_argument('--redis-host', type=str, default='localhost',
                        help='Redis server address (default: localhost)')
    
    parser.add_argument('--redis-port', type=int, default=6379,
                        help='Redis port (default: 6379)')
    
    parser.add_argument('--redis-password', type=str,
                        help='Redis password (if required)')
    
    parser.add_argument('--concurrency', type=int,
                        help='Concurrency level (overrides settings)')
    
    parser.add_argument('--delay', type=float,
                        help='Download delay in seconds')
    
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug mode')
    
    parser.add_argument('--check-redis', action='store_true',
                        help='Check Redis connection and exit')
    
    return parser

async def check_redis_connection(host, port, password=None):
    """Check Redis connection"""
    try:
        import redis.asyncio as aioredis
        
        if password:
            url = f'redis://:{password}@{host}:{port}/0'
        else:
            url = f'redis://{host}:{port}/0'
        
        redis = aioredis.from_url(url)
        await redis.ping()
        await redis.aclose()
        
        print(f"✅ Redis connection successful: {host}:{port}")
        return True
        
    except Exception as e:
        print(f"❌ Redis connection failed: {host}:{port} - {e}")
        return False

def build_settings(args):
    """Build settings from command line arguments"""
    settings = {}
    
    # Redis configuration
    if args.redis_password:
        redis_url = f'redis://:{args.redis_password}@{args.redis_host}:{args.redis_port}/0'
    else:
        redis_url = f'redis://{args.redis_host}:{args.redis_port}/0'
    
    settings['REDIS_URL'] = redis_url
    settings['REDIS_HOST'] = args.redis_host
    settings['REDIS_PORT'] = args.redis_port
    if args.redis_password:
        settings['REDIS_PASSWORD'] = args.redis_password
    
    # Other settings
    if args.debug:
        settings['LOG_LEVEL'] = 'DEBUG'
        settings['DUPEFILTER_DEBUG'] = True
        settings['FILTER_DEBUG'] = True
        print("🐛 Debug mode enabled")
    
    if args.concurrency:
        settings['CONCURRENCY'] = args.concurrency
        print(f"⚡ Concurrency set to: {args.concurrency}")
    
    if args.delay:
        settings['DOWNLOAD_DELAY'] = args.delay
        print(f"⏱️  Download delay set to: {args.delay} seconds")
    
    return settings

async def main():
    """Main function"""
    parser = create_parser()
    args = parser.parse_args()
    
    print("🌐 Starting distributed Crawlo spider")
    
    # Check Redis connection
    redis_ok = await check_redis_connection(
        args.redis_host, 
        args.redis_port, 
        args.redis_password
    )
    
    if not redis_ok:
        print("\n💡 Solutions:")
        print("   1. Ensure Redis server is running")
        print("   2. Check Redis configuration and network connection")
        print("   3. Verify Redis password (if set)")
        if args.check_redis:
            return
        else:
            print("   4. Use --check-redis option to test connection only")
            sys.exit(1)
    
    if args.check_redis:
        print("🎉 Redis connection check completed")
        return
    
    # Build settings
    custom_settings = build_settings(args)
    
    print(f"🔗 Redis server: {args.redis_host}:{args.redis_port}")
    print(f"🌐 Multi-node mode: Run the same script on other machines")
    
    # Create crawler process
    print(f"\n🚀 Starting spider: {args.spider_name}")
    
    try:
        # Apply configuration and start
        process = CrawlerProcess()
        
        # Run specified spider
        if args.spider_name == 'myspider':
            spider_cls = MySpider
            await process.crawl(spider_cls, **custom_settings)
        else:
            print(f"❌ Unknown spider: {args.spider_name}")
            print("Available spiders: myspider")
            return
        
        print("✅ Node execution completed!")
        print("📊 Check output files for this node's results")
        print("🔄 Other nodes can continue processing remaining tasks")
        
    except ImportError as e:
        print(f"❌ Cannot import spider: {e}")
        print("   Please check if the spider file exists")
    except Exception as e:
        print(f"❌ Node execution error: {e}")
        if args.debug:
            raise

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Node interrupted by user")
        print("🔄 Other nodes can continue running and processing remaining tasks")
    except Exception as e:
        print(f"❌ Runtime error: {e}")
        sys.exit(1)
```

## Running Distributed Crawlers

### Single Machine with Multiple Processes

Terminal 1:
```bash
python run.py myspider
```

Terminal 2 (run simultaneously):
```bash
python run.py myspider --concurrency 32
```

### Multi-Machine Deployment

Machine A (Redis server):
```bash
python run.py myspider
```

Machine B:
```bash
python run.py myspider --redis-host 192.168.1.100 --concurrency 16
```

Machine C:
```bash
python run.py myspider --redis-host 192.168.1.100 --concurrency 24
```

## Monitoring Distributed Crawls

### Redis Monitoring

Check queue sizes:
```bash
redis-cli llen myproject:requests
```

Check deduplication set size:
```bash
redis-cli scard myproject:fingerprint
```

### Built-in Statistics

View crawl statistics:
```bash
crawlo stats myspider
```

## Best Practices for Distributed Crawling

### 1. Network Configuration

Ensure all nodes can connect to the Redis server:
- Configure firewall rules
- Use private network addresses when possible
- Consider Redis security settings

### 2. Resource Management

- Adjust concurrency based on target server capacity
- Monitor system resources on each node
- Balance load across nodes

### 3. Error Handling

- Implement proper retry logic
- Handle network timeouts gracefully
- Log errors for debugging

### 4. Data Consistency

- Use consistent data models across nodes
- Implement proper data deduplication
- Consider using distributed databases for storage

## Troubleshooting

### Common Issues

1. **Redis Connection Failures**
   - Verify Redis server is running
   - Check network connectivity
   - Confirm Redis credentials

2. **Duplicate Data**
   - Ensure Redis deduplication is properly configured
   - Check that all nodes use the same Redis instance

3. **Performance Issues**
   - Monitor Redis performance
   - Adjust concurrency settings
   - Check network bandwidth

### Debugging Distributed Crawls

Enable debug mode:
```bash
python run.py myspider --debug
```

Check Redis connection:
```bash
python run.py myspider --check-redis
```

Monitor Redis in real-time:
```bash
redis-cli monitor
```

## Scaling Your Distributed Crawler

### Adding More Nodes

Simply run the same command on additional machines:
```bash
python run.py myspider --redis-host YOUR_REDIS_HOST --concurrency 20
```

### Removing Nodes

Gracefully stop nodes with Ctrl+C. The distributed system will automatically redistribute tasks.

### Performance Tuning

1. Adjust concurrency based on:
   - Target server capacity
   - Network bandwidth
   - System resources

2. Optimize Redis:
   - Use Redis clustering for large deployments
   - Monitor memory usage
   - Configure appropriate persistence settings

This tutorial provides a comprehensive guide to setting up and running distributed crawls with Crawlo. With proper configuration and monitoring, you can efficiently scale your crawling operations across multiple machines.