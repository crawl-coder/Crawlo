# Crawlo Distributed Crawling Mechanism Explained

## Table of Contents
1. [Overview](#overview)
2. [Core Components](#core-components)
3. [Working Mechanism](#working-mechanism)
4. [Case Studies](#case-studies)
5. [Comparison with Scrapy-Redis](#comparison-with-scrapy-redis)

## Overview

Crawlo is an asynchronous web crawling framework based on Python asyncio that supports both standalone and distributed operating modes. In distributed mode, multiple crawler nodes can work together, sharing task queues and deduplication data to avoid processing the same requests repeatedly, achieving efficient distributed data collection.

## Core Components

### 1. Queue Manager (QueueManager)
Unifies the management of different types of queue implementations, supporting automatic switching between memory queues and Redis queues.

### 2. Redis Priority Queue (RedisPriorityQueue)
A distributed asynchronous priority queue based on Redis, implemented using sorted sets (ZSET) to achieve task priority scheduling.

### 3. Redis Deduplication Filter (AioRedisFilter)
A distributed request deduplication filter based on Redis sets, ensuring shared deduplication data between multiple nodes.

### 4. Scheduler (Scheduler)
Coordinates queues and deduplication filters, managing request enqueue and dequeue operations.

### 5. Pipeline Deduplication (RedisDedupPipeline)
A data item deduplication pipeline based on Redis, preventing the saving of duplicate data records.

## Working Mechanism

### 1. Distributed Queue Mechanism

Crawlo uses Redis as the central coordinator for distributed task queues:

1. **Task Enqueue**: All nodes' [Scheduler.enqueue_request](https://github.com/crawl-coder/Crawlo/blob/master/crawlo/core/scheduler.py#L79-L96) methods put requests into the shared Redis sorted set
2. **Priority Scheduling**: Uses the ZSET score mechanism to implement request priority sorting
3. **Task Distribution**: Multiple nodes compete to get tasks through the [RedisPriorityQueue.get](https://github.com/crawl-coder/Crawlo/blob/master/crawlo/queue/redis_priority_queue.py#L104-L143) method
4. **Task Acknowledgment**: After task processing is completed, the [RedisPriorityQueue.ack](https://github.com/crawl-coder/Crawlo/blob/master/crawlo/queue/redis_priority_queue.py#L145-L159) method confirms completion

### 2. Distributed Deduplication Mechanism

Crawlo employs a two-layer deduplication mechanism to ensure data consistency in distributed environments:

1. **Request-level Deduplication**: Distributed request deduplication through [AioRedisFilter](https://github.com/crawl-coder/Crawlo/blob/master/crawlo/filters/aioredis_filter.py#L36-L241)
2. **Data-level Deduplication**: Distributed data item deduplication through [RedisDedupPipeline](https://github.com/crawl-coder/Crawlo/blob/master/crawlo/pipelines/redis_dedup_pipeline.py#L33-L162)

### 3. Node Coordination Mechanism

1. **Automatic Discovery**: All nodes connect to the same Redis instance and automatically discover shared queues
2. **Load Balancing**: Nodes compete for tasks from the shared queue, achieving natural load balancing
3. **Fault Recovery**: Timed-out tasks are automatically requeued to ensure no task loss

## Case Studies

### Case 1: API Data Collection Distributed Crawler

Here's a typical distributed crawler example, showing how to handle API data collection scenarios with only list pages:

```python
# api_data_collection/api_data_collection/spiders/api_data.py
class ApiDataSpider(Spider):
    name = 'api_data'
    
    # Spider configuration
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'CONCURRENCY': 32,
        'MAX_RETRY_TIMES': 5,
        'DUPEFILTER_CLASS': 'crawlo.filters.aioredis_filter.AioRedisFilter',
        'SCHEDULER': 'crawlo.scheduler.Scheduler',
    }
    
    def start_requests(self):
        """Generate requests for all pages, allowing multiple nodes to process in parallel"""
        # Generate requests for all pages (1-1000 pages)
        for page in range(1, 1001):
            yield Request(
                url=f'https://api.example.com/data?page={page}&limit=50',
                callback=self.parse,
                meta={'page': page},
                # Enable deduplication mechanism to avoid duplicate requests
                dont_filter=False
            )
    
    def parse(self, response):
        """Parse API response"""
        page = response.meta['page']
        try:
            json_data = response.json()
            
            # Extract data list
            data_list = json_data.get("data", [])
            
            # Yield each record as an independent item
            for item_data in data_list:
                item = ApiDataItem()
                item['id'] = item_data.get('id')
                item['name'] = item_data.get('name')
                # ... other field processing
                yield item
                
        except Exception as e:
            logger.error(f"Failed to parse response for page {page}: {e}", exc_info=True)
```

You can view the complete example on GitHub: [API Data Collection Example](https://github.com/crawl-coder/Crawlo/tree/master/examples/api_data_collection)

### Case 2: Traditional List-Detail Page Distributed Crawler

```
# telecom_licenses_distributed/telecom_licenses/spiders/device.py
class DeviceSpider(Spider):
    name = 'device'
    
    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'CONCURRENCY': 16,
        'DUPEFILTER_CLASS': 'crawlo.filters.aioredis_filter.AioRedisFilter',
        'SCHEDULER': 'crawlo.scheduler.Scheduler',
    }
    
    def start_requests(self):
        """Generate list page requests"""
        for page in range(1, 101):
            yield Request(
                url=f'http://example.com/device/list?page={page}',
                callback=self.parse_list,
                meta={'page': page},
                dont_filter=False
            )
    
    def parse_list(self, response):
        """Parse list page, extract detail page links"""
        # Extract detail page links
        detail_links = response.css('.device-link::attr(href)').getall()
        
        for link in detail_links:
            yield Request(
                url=response.urljoin(link),
                callback=self.parse_detail,
                dont_filter=False
            )
    
    def parse_detail(self, response):
        """Parse detail page"""
        item = DeviceItem()
        item['name'] = response.css('.device-name::text').get()
        item['model'] = response.css('.device-model::text').get()
        # ... other field extraction
        yield item
```

You can view the complete example on GitHub: [Telecom Equipment Licenses Distributed Crawler Example](https://github.com/crawl-coder/Crawlo/tree/master/examples/telecom_licenses_distributed)

### Case 3: Distributed Implementation Principle for 10 Nodes Crawling 10,000 Pages

When 10 nodes are running simultaneously, and there are 10,000 pages to crawl on the website, users might wonder: since each node starts generating requests from [start_requests](file:///d:\dowell\projects\Crawlo\crawlo\spider\__init__.py#L24-L53), how does Crawlo avoid duplicate crawling and achieve efficient distributed processing?

#### Implementation Principle

Crawlo ensures multiple nodes work collaboratively without processing the same requests through the following mechanisms:

1. **Shared Task Queue**:
   - All nodes connect to the same Redis instance
   - Requests generated by each node's [start_requests](file:///d:\dowell\projects\Crawlo\crawlo\spider\__init__.py#L24-L53) method are put into the shared Redis sorted set
   - Redis acts as a central coordinator to ensure task queue synchronization across all nodes

2. **Request-level Deduplication**:
   - Uses [AioRedisFilter](https://github.com/crawl-coder/Crawlo/blob/master/crawlo/filters/aioredis_filter.py#L36-L241) to deduplicate requests by fingerprint
   - When nodes attempt to add requests to the queue, they first check if the request fingerprint already exists in Redis's deduplication set
   - If it exists, the request is discarded to avoid duplicate queuing

3. **Competitive Task Consumption**:
   - Nodes compete to get tasks from the shared queue through atomic operations (such as ZPOPMIN)
   - Only one node can get a specific task at a time, ensuring tasks are not processed by multiple nodes simultaneously

4. **Dynamic Load Balancing**:
   - Nodes dynamically acquire tasks based on their processing capabilities
   - Faster processing nodes will get more tasks, achieving natural load balancing

#### Example Code

```
class TenThousandPageSpider(Spider):
    name = 'ten_thousand_page'
    
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'CONCURRENCY': 16,
        'DUPEFILTER_CLASS': 'crawlo.filters.aioredis_filter.AioRedisFilter',
        'SCHEDULER': 'crawlo.scheduler.Scheduler',
    }
    
    def start_requests(self):
        """Each node will execute this method, but requests will be automatically deduplicated"""
        # Generate requests for 10,000 pages
        for page in range(1, 10001):
            yield Request(
                url=f'https://example.com/page/{page}',
                callback=self.parse,
                meta={'page': page},
                # Enable deduplication mechanism
                dont_filter=False
            )
    
    def parse(self, response):
        """Parse page content"""
        page = response.meta['page']
        # Process page data
        item = PageItem()
        item['page'] = page
        item['title'] = response.css('title::text').get()
        # ... other field processing
        yield item
```

#### Running Method

Run simultaneously on 10 different terminals or machines:

```
# Terminals 1-10 all run the same command
crawlo run ten_thousand_page
```

#### Execution Process

1. **Initialization Phase**:
   - 10 nodes start simultaneously, each executing the [start_requests](https://github.com/crawl-coder/Crawlo/crawlo/spider/__init__.py#L24-L53) method
   - All nodes attempt to generate 10,000 requests and add them to the shared queue
   - Due to the deduplication mechanism, only 10,000 unique requests will ultimately be in the queue

2. **Task Distribution Phase**:
   - Nodes compete to get tasks from the shared queue
   - Redis ensures the same task will only be obtained by one node
   - 10,000 tasks are automatically distributed among 10 nodes

3. **Processing Phase**:
   - Each node independently processes assigned tasks
   - Processing results are deduplicated at the data level through [RedisDedupPipeline](https://github.com/crawl-coder/Crawlo/blob/master/crawlo/pipelines/redis_dedup_pipeline.py#L33-L162)
   - Ultimately obtain 10,000 unique data records

#### Advantages

- **No Manual Pagination**: Developers don't need to manually distribute 10,000 pages to different nodes
- **Automatic Load Balancing**: Nodes automatically acquire tasks based on processing capabilities
- **Strong Fault Tolerance**: Failure of a single node doesn't affect overall task execution
- **Deduplication Guarantee**: Two-layer deduplication mechanism ensures data consistency

This design allows Crawlo to easily scale to any number of nodes without modifying crawler code, truly achieving efficient distributed crawling.

### Running Distributed Crawlers

1. Start Redis service:
   ```bash
   redis-server
   ```

2. Start crawler nodes in multiple terminals:
   ```bash
   # Terminal 1
   crawlo run api_data
   
   # Terminal 2
   crawlo run api_data
   
   # Terminal 3
   crawlo run api_data
   ```

## Comparison with Scrapy-Redis

| Feature | Crawlo | Scrapy-Redis |
|------|--------|--------------|
| **Asynchronous Support** | Native asyncio support, fully asynchronous | Requires additional configuration, mainly based on synchronous operations |
| **Queue Implementation** | Uses Redis sorted sets (ZSET) to implement priority queues | Uses Redis lists (LIST) to implement queues |
| **Deduplication Mechanism** | Two-layer deduplication: request-level + data-level | Mainly deduplicates requests, data deduplication needs additional implementation |
| **Task Acknowledgment** | Supports task acknowledgment and failure retry mechanism | Basic queue operations, retry mechanism needs self-implementation |
| **Configuration Management** | Automatic mode detection, intelligent switching between standalone/distributed | Requires manual configuration of all distributed components |
| **Performance Optimization** | Uses Pipeline batch operations to optimize Redis performance | More individual operations, relatively lower performance |
| **Error Handling** | Comprehensive exception handling and retry mechanism | Basic error handling |
| **Extensibility** | Modular design, easy to extend | Plugin-based design, good extensibility |
| **Learning Curve** | Modern Python asynchronous programming, requires asyncio knowledge | Traditional synchronous programming, lower learning threshold |
| **Community Support** | Emerging framework, smaller community | Mature framework, active community |

### Advantages Comparison

**Crawlo's Advantages:**
1. **Native Asynchronous**: Built on asyncio, higher performance
2. **Intelligent Configuration**: Automatically detects running mode, simplifies configuration
3. **Two-layer Deduplication**: Request-level and data-level dual deduplication guarantee
4. **Task Acknowledgment**: Comprehensive task acknowledgment and failure handling mechanism
5. **Performance Optimization**: Uses Redis Pipeline to optimize batch operations

**Scrapy-Redis's Advantages:**
1. **Mature and Stable**: Proven over years, high stability
2. **Active Community**: Abundant documentation and community support
3. **Rich Ecosystem**: Fully compatible with Scrapy ecosystem
4. **Learning Resources**: Rich tutorials and best practices

### Applicable Scenarios

**Choose Crawlo for:**
- Need for high-performance asynchronous crawlers
- Higher requirements for distributed task scheduling
- Want to simplify distributed configuration
- Need comprehensive task acknowledgment and retry mechanism

**Choose Scrapy-Redis for:**
- Need to integrate with existing Scrapy projects
- Team is more familiar with Scrapy
- Require a large number of existing extensions and plugins
- Have higher requirements for community support

## Summary

Crawlo's distributed crawler mechanism achieves efficient multi-node collaborative work through Redis, with a complete task scheduling, deduplication, and error handling mechanism. Compared to Scrapy-Redis, Crawlo has advantages in asynchronous performance and configuration simplification, but Scrapy-Redis is superior in maturity and community support. Developers can choose the appropriate framework based on project requirements.