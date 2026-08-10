# 进阶爬虫示例

> 从 basic-examples 拆分：动态渲染、API、登录。

## 进阶案例

### 案例4: 动态渲染

**场景**：抓取 JavaScript 渲染的页面

**目标网站**：https://example.com/dynamic

**完整代码**：

```python
from crawlo import Spider


class DynamicSpider(Spider):
 """动态页面爬虫"""
 
 name = 'dynamic'
 start_urls = ['https://example.com/dynamic']
 
 async def parse(self, response):
 # 使用浏览器渲染
 # 方式1: 在请求中指定
 yield Request(
 url='https://example.com/dynamic',
 callback=self.parse_dynamic,
 meta={'use_dynamic_loader': True}
 )
 
 async def parse_dynamic(self, response):
 # 现在可以提取 JavaScript 渲染的内容
 yield {
 'title': response.css('h1::text').get(),
 'data': response.css('.dynamic-content::text').get(),
 }
```

**配置**：
```python
# settings.py
DYNAMIC_LOADER_ENABLED = True
```

---

### 案例5: API 抓取

**场景**：抓取 REST API 返回的 JSON 数据

**目标网站**：https://api.example.com/data

**完整代码**：

```python
import json
from crawlo import Spider
from crawlo import Request


class APISpider(Spider):
 """API 爬虫"""
 
 name = 'api'
 
 async def start_requests(self):
 # 请求 API
 yield Request(
 url='https://api.example.com/data',
 headers={'Authorization': 'Bearer YOUR_TOKEN'},
 callback=self.parse_api
 )
 
 async def parse_api(self, response):
 # 解析 JSON
 data = json.loads(response.text)
 
 # 提取数据
 for item in data.get('results', []):
 yield {
 'id': item.get('id'),
 'name': item.get('name'),
 'value': item.get('value'),
 }
 
 # 处理分页
 if data.get('next_page'):
 yield Request(
 url=data['next_page'],
 callback=self.parse_api
 )
```

---

### 案例6: 登录抓取

**场景**：先登录，再抓取需要认证的数据

**目标网站**：https://example.com/login

**完整代码**：

```python
from crawlo import Spider
from crawlo import Request


class LoginSpider(Spider):
 """登录爬虫"""
 
 name = 'login'
 login_url = 'https://example.com/login'
 start_urls = ['https://example.com/dashboard']
 
 async def start_requests(self):
 # 先登录
 yield Request(
 url=self.login_url,
 method='POST',
 form_data={
 'username': 'your_username',
 'password': 'your_password',
 },
 callback=self.after_login
 )
 
 async def after_login(self, response):
 # 检查登录是否成功
 if 'logout' in response.text:
 self.logger.info("登录成功")
 
 # 登录后抓取
 for url in self.start_urls:
 yield Request(url, callback=self.parse_dashboard)
 else:
 self.logger.error("登录失败")
 
 async def parse_dashboard(self, response):
 # 提取需要登录才能看到的数据
 yield {
 'user_info': response.css('.user-info::text').get(),
 'data': response.css('.private-data::text').get(),
 }
```

---
