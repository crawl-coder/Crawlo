# 生产级爬虫示例

> 从 basic-examples 拆分：分布式、定时、监控。

## 生产案例

### 案例7: 分布式抓取

**场景**：使用多节点并行抓取大量数据，支持 ACK 确认、故障转移和自动协调退出

**配置**（使用分布式系统模式）：

```python
# settings.py
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis_stream'

# Redis 配置
REDIS_HOST = 'redis.example.com'
REDIS_PORT = 6379
REDIS_PASSWORD = 'your_password'

# 并发控制
CONCURRENCY = 16
DOWNLOAD_DELAY = 0.5

# 集群配置（可选，默认自动启用）
CLUSTER_HEARTBEAT_INTERVAL = 15
CLUSTER_WORKER_TIMEOUT = 90
CLUSTER_FAILOVER_CHECK_INTERVAL = 30
```

> 详细说明见：[部署模式](../concepts/architecture.md#2-部署模式-deployment-modes)、[Redis Key 说明](../concepts/redis-keys.md)

**爬虫代码**：

```python
from crawlo import Spider
from crawlo import Request


class DistributedSpider(Spider):
 """分布式爬虫"""
 
 name = 'distributed'
 start_urls = ['https://example.com/list']
 
 async def parse(self, response):
 # 提取详情页链接
 for link in response.css('a.detail::attr(href)').getall():
 yield Request(
 url=response.urljoin(link),
 callback=self.parse_detail
 )
 
 # 提取下一页
 next_page = response.css('a.next::attr(href)').get()
 if next_page:
 yield response.follow(next_page, callback=self.parse)
 
 async def parse_detail(self, response):
 yield {
 'title': response.css('h1::text').get(),
 'content': response.css('.content::text').get(),
 }
```

**启动多个 Worker**：

```bash
# 终端 1 — Worker 1
cd examples/ofweek_distributed
python run.py

# 终端 2 — Worker 2（间隔若干秒启动）
python run.py

# 终端 3~N
python run.py
```

各 Worker 自动注册到 Redis，通过 Consumer Group 分配任务。
当所有任务完成时，Leader Worker 自动广播 shutdown 信号，所有 Worker 优雅退出。

---

### 案例8: 定时任务

**场景**：每天定时运行爬虫

**方式1: 使用 Crontab（Linux/Mac）**```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每天凌晨2点运行）
0 2 * * * cd /path/to/project && crawlo run myspider -o output.json
```

**方式2: 使用 Python 脚本**```python
import asyncio
from datetime import datetime, time
from crawlo.crawler import Crawler


async def run_spider_daily():
 """每天运行爬虫"""
 
 while True:
 now = datetime.now()
 
 # 如果是凌晨2点
 if now.hour == 2 and now.minute == 0:
 print(f"开始运行爬虫: {now}")
 
 # 运行爬虫
 crawler = Crawler()
 await crawler.crawl('myspider')
 
 # 等待1小时，避免重复运行
 await asyncio.sleep(3600)
 
 # 每分钟检查一次
 await asyncio.sleep(60)


if __name__ == '__main__':
 asyncio.run(run_spider_daily())
```

---

### 案例9: 数据监控

**场景**：监控商品价格变化

**完整代码**：

```python
from crawlo import Spider


class PriceMonitorSpider(Spider):
 """价格监控爬虫"""
 
 name = 'price_monitor'
 start_urls = [
 'https://example.com/product/1',
 'https://example.com/product/2',
 'https://example.com/product/3',
 ]
 
 async def parse(self, response):
 # 提取当前价格
 current_price = response.css('.price::text').get()
 product_name = response.css('h1::text').get()
 
 # 获取历史价格（从数据库）
 old_price = await self.get_old_price(response.url)
 
 # 检查价格变化
 if old_price and current_price != old_price:
 self.logger.warning(
 f"价格变化: {product_name}\n"
 f" 旧价格: {old_price}\n"
 f" 新价格: {current_price}"
 )
 
 # 发送通知
 await self.send_notification(
 f"价格提醒: {product_name} 从 {old_price} 变为 {current_price}"
 )
 
 # 保存当前价格
 await self.save_price(response.url, current_price)
 
 yield {
 'product': product_name,
 'price': current_price,
 'changed': current_price != old_price,
 }
 
 async def get_old_price(self, url):
 """从数据库获取旧价格"""
 # 实现数据库查询逻辑
 pass
 
 async def save_price(self, url, price):
 """保存价格到数据库"""
 # 实现数据库保存逻辑
 pass
 
 async def send_notification(self, message):
 """发送通知"""
 # 实现通知逻辑（邮件、飞书、钉钉等）
 pass
```

**配置**：

```python
# settings.py
# 定时运行
CHECKPOINT_ENABLED = True
CHECKPOINT_INTERVAL = 3600 # 每小时保存一次

# 通知配置
NOTIFICATION_ENABLED = True
NOTIFICATION_ON_ERROR = True
NOTIFICATION_CHANNELS = ['feishu']
```

---
