# Cloudflare 5 秒盾？Crawlo 一行配置直接绕过

> 你还在手动等 5 秒过验证？让框架帮你搞定。

---

## 反爬的终极 Boss：Cloudflare

当你看到这个页面，就知道事情不简单：

```
Checking your browser before accessing example.com.
This process is automatic. Your browser will redirect shortly.
Please wait 5 seconds...
```

Cloudflare 的防护手段：

| 防护类型 | 检测内容 | 传统爬虫能过吗 |
|----------|---------|--------------|
| JS Challenge | 执行 JS 计算令牌 | ❌ |
| 5 秒盾 | JS 执行 + 等待 | ❌ |
| TLS 指纹 | JA3/JA4 指纹匹配 | ❌ |
| Canvas 指纹 | 浏览器渲染特征 | ❌ |
| 行为分析 | 鼠标/键盘事件 | ❌ |

**用 aiohttp/requests 发请求？直接 403。**

---

## Crawlo 的三种绕过方案

### 方案一：CloakBrowser（推荐）

**专治 Cloudflare，一行配置：**

```python
# settings.py
DOWNLOADER = 'cloakbrowser'
```

CloakBrowser 的原理：
1. 启动真实 Chromium 浏览器
2. 注入反检测脚本（隐藏 WebDriver 特征）
3. 模拟真实用户行为（鼠标移动、键盘输入）
4. 自动等待 Cloudflare 验证通过
5. 返回页面内容

```python
import crawlo

class CfSpider(crawlo.Spider):
    name = 'cf_spider'
    start_urls = ['https://nowsecure.nl/']  # Cloudflare 防护站点

    def parse(self, response):
        # response 已经是过验证后的页面内容！
        yield {
            'title': response.css('h1::text').get(),
            'content': response.css('.content::text').get(),
        }
```

### 方案二：Camoufox

**浏览器指纹伪装：**

```python
# settings.py
DOWNLOADER = 'camoufox'
```

Camoufox 基于 Firefox，通过修改浏览器底层参数来伪造指纹：

- 修改 WebGL 渲染器信息
- 修改 Canvas 指纹
- 修改 Audio 上下文指纹
- 修改 Navigator 属性
- 随机化 TLS 握手参数

**适用**：需要长期稳定访问、指纹检测严格的站点。

### 方案三：Playwright

**通用 JS 渲染：**

```python
# settings.py
DOWNLOADER = 'playwright'
```

Playwright 适合需要 JS 渲染但不需要反检测的场景：
- SPA 单页应用
- 页面依赖 JavaScript 动态加载内容

---

## 三种方案对比

| 维度 | CloakBrowser | Camoufox | Playwright |
|------|-------------|----------|------------|
| **Cloudflare 绕过** | ✅ 专治 | ✅ 能过 | ⚠️ 部分 |
| **反检测能力** | ★★★★★ | ★★★★★ | ★★★ |
| **JS 渲染** | ✅ | ✅ | ✅ |
| **速度** | ★★★ | ★★★ | ★★★★ |
| **资源占用** | 高（Chromium） | 高（Firefox） | 高（Chromium） |
| **适用场景** | Cloudflare 防护 | 指纹检测 | 通用 JS 渲染 |

---

## 性能优化：混合下载器

不是所有页面都需要浏览器。列表页用 aiohttp，详情页用 CloakBrowser：

```python
# settings.py
DOWNLOADER = 'hybrid'  # 混合下载器
```

```python
import crawlo

class HybridSpider(crawlo.Spider):
    name = 'hybrid'

    def start_requests(self):
        # 列表页：轻量级 aiohttp
        yield crawlo.Request('https://example.com/list', meta={'downloader': 'aiohttp'})

    def parse(self, response):
        for href in response.css('a.item::attr(href)'):
            # 详情页：CloakBrowser 绕过 Cloudflare
            yield crawlo.Request(
                response.urljoin(href),
                callback=self.parse_detail,
                meta={'downloader': 'cloakbrowser'}
            )

    def parse_detail(self, response):
        yield {'title': response.css('h1::text').get()}
```

**效果**：列表页速度提升 10 倍 + 详情页绕过防护，兼顾性能与反爬。

---

## 安装额外依赖

```bash
# CloakBrowser
pip install crawlo[stealth]

# Playwright
pip install crawlo[render]
playwright install chromium

# Camoufox
pip install crawlo[render]
```

---

## 实战案例：绕过 Cloudflare 5 秒盾

```python
import crawlo

class CloudflareSpider(crawlo.Spider):
    name = 'cf_bypass'

    custom_settings = {
        'DOWNLOADER': 'cloakbrowser',
        'CONCURRENCY': 4,  # 浏览器下载器并发不宜太高
    }

    start_urls = ['https://nowsecure.nl/']

    def parse(self, response):
        # 已经绕过 Cloudflare，直接解析
        title = response.css('h1::text').get()
        yield {'title': title}
```

运行：

```bash
crawlo run cf_bypass
```

输出：

```
[INFO] CloakBrowser downloader initialized
[INFO] Bypassing Cloudflare challenge for https://nowsecure.nl/
[INFO] Challenge solved, page loaded
[INFO] Scraped: {'title': 'nowSecure'}
```

---

---

*关注公众号，获取更多 Crawlo 技术干货和爬虫实战经验。*
