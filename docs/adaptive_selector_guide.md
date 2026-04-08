# 自适应元素追踪指南

## 概述

自适应元素追踪是 Crawlo 的核心功能之一，让爬虫选择器具备**自愈能力**。当网站改版导致 CSS/XPath 选择器失效时，通过元素指纹+相似度匹配自动重新定位元素。

## 核心特性

### 🎯 支持的改版场景

| 场景 | 说明 | 示例 |
|------|------|------|
| **Class 名称变化** | CSS 类名完全改变 | `.item` → `.product` |
| **DOM 结构层级调整** | 元素嵌套层级变化 | 从 3 层嵌套变为 2 层 |
| **标签类型变化** | HTML 标签类型改变 | `<div>` → `<article>`，`<h3>` → `<h4>` |
| **属性顺序/内容变化** | 属性增删改 | 增加 `data-*` 属性，修改 `id` 值 |
| **文本内容微调** | 文本格式变化 | `2024年01月15日` → `2024-01-15` |
| **混合变化** | 多种变化同时发生 | class+标签+结构+文本同时改变 |

### 🔧 工作原理

```
首次运行（选择器命中）
    ↓
自动保存元素指纹（tag、text、attributes、path、parent、siblings、children）
    ↓
网站改版（选择器失效）
    ↓
自动加载指纹 + 相似度匹配
    ↓
返回最相似的元素（7 维度等权平均算法）
```

### 📊 匹配维度

自适应追踪基于 **7 个维度**计算相似度：

1. **标签名**（1/7 权重）
2. **文本内容**（1/7 权重）- 使用 SequenceMatcher 模糊匹配
3. **属性特征**（1/7 权重）- class、id、data-* 等
4. **DOM 路径**（1/7 权重）- 元素在文档树中的位置
5. **父元素特征**（1/7 权重）- 父节点的 tag/属性/文本
6. **兄弟元素**（1/7 权重）- 前后兄弟节点的特征
7. **子元素结构**（1/7 权重）- 子节点的标签序列

**等权平均算法**：即使 2-3 个维度变化较大，只要其他维度相似度高，仍能成功匹配！

## 快速开始

### 基本用法

只需在 `xpath()` 或 `css()` 中传入 `adaptive=True`：

```python
from crawlo.spider import Spider
from crawlo import Request, Response

class MySpider(Spider):
    name = 'my_spider'
    
    def parse(self, response: Response):
        # 使用 adaptive=True 启用自适应追踪
        items = response.xpath(
            '//div[@class="item"]',
            adaptive=True,              # ← 只需这一个参数！
            identifier='list_items'     # 可选：自定义标识符
        )
        
        for item in items:
            title = item.xpath('./h3/text()').extract_first()
            print(title)
```

### 完整示例

```python
from crawlo.spider import Spider
from crawlo import Request, Response

class AdaptiveSpider(Spider):
    name = 'adaptive_example'
    start_urls = ['https://example.com/articles']
    
    def parse(self, response: Response):
        # 列表页 - 使用自适应追踪
        articles = response.xpath(
            '//div[@class="article-card"]',
            adaptive=True,
            identifier='article_list'
        )
        
        for article in articles:
            title = article.xpath('.//h2/a/text()', adaptive=True).extract_first()
            link = article.xpath('.//h2/a/@href', adaptive=True).extract_first()
            
            yield Request(
                url=response.urljoin(link),
                callback=self.parse_detail
            )
    
    def parse_detail(self, response: Response):
        # 详情页 - 同样使用自适应追踪
        content = response.xpath(
            '//div[@class="content"]',
            adaptive=True,
            identifier='article_content'
        )
        
        publish_time = response.xpath(
            '//span[@class="date"]',
            adaptive=True,
            identifier='publish_time'
        ).extract_first()
        
        yield {
            'title': response.meta.get('title'),
            'content': content.xpath('.//text()').extract(),
            'publish_time': publish_time
        }
```

## 配置选项

### 默认配置（无需修改即可使用）

框架已提供合理的默认配置，存储在 `adaptive_fingerprints.db`（项目根目录）：

```python
# settings.py（可选，使用默认值时无需配置）
ADAPTIVE_STORAGE_BACKEND = 'sqlite'           # 存储后端
ADAPTIVE_SQLITE_PATH = 'adaptive_fingerprints.db'  # SQLite 数据库路径
ADAPTIVE_SIMILARITY_THRESHOLD = 0.0           # 最低相似度阈值（0-100）
```

### 分布式部署（Redis）

多节点爬虫共享指纹数据，使用 Redis 存储：

```python
# settings.py
ADAPTIVE_STORAGE_BACKEND = 'redis'

# Redis 配置（复用框架统一配置）
REDIS_HOST = 'redis-server.example.com'
REDIS_PORT = 6379
REDIS_PASSWORD = 'your_password'
REDIS_DB = 0
```

### 自定义配置

如需调整配置，可在 Spider 的 `custom_settings` 中覆盖：

```python
class MySpider(Spider):
    name = 'my_spider'
    
    custom_settings = {
        'ADAPTIVE_STORAGE_BACKEND': 'sqlite',
        'ADAPTIVE_SQLITE_PATH': 'fingerprints.db',
        'ADAPTIVE_SIMILARITY_THRESHOLD': 60.0,  # 只接受 60% 以上相似度
    }
```

## 参数说明

### xpath() / css() 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | str | ✅ | XPath 或 CSS 选择器表达式 |
| `adaptive` | bool | ❌ | 启用自适应追踪（默认 False） |
| `identifier` | str | ❌ | 指纹标识符（默认使用 query 字符串） |
| `percentage` | float | ❌ | 最低匹配百分比阈值（0-100，默认 0） |

### identifier 使用建议

- **推荐使用**：为每个选择器设置唯一的 identifier，便于管理和调试
- **命名规范**：使用描述性名称，如 `article_list`、`detail_title`、`publish_time`
- **不设置时**：默认使用 query 字符串作为 identifier

```python
# 推荐：明确的 identifier
response.xpath('//div[@class="item"]', adaptive=True, identifier='list_items')

# 也可以：使用默认 identifier（query 字符串）
response.xpath('//div[@class="item"]', adaptive=True)
```

## 存储后端

### SQLite（单机模式）

**适用场景**：单节点爬虫，本地开发

**特点**：
- ✅ 线程安全（RLock + WAL 模式）
- ✅ 按 domain + identifier 分区存储
- ✅ 自动创建数据库文件
- ✅ 零配置，开箱即用

**数据库结构**：
```sql
CREATE TABLE adaptive_fingerprints (
    id INTEGER PRIMARY KEY,
    domain TEXT,           -- 域名（分区键）
    identifier TEXT,       -- 标识符
    fingerprint_data TEXT, -- JSON 格式的指纹数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (domain, identifier)
)
```

### Redis（分布式模式）

**适用场景**：多节点爬虫，生产环境

**特点**：
- ✅ 天然支持分布式部署
- ✅ 多节点共享指纹数据
- ✅ 高性能，支持高并发
- ✅ 自动管理连接池

**Key 格式**：
```
crawlo:adaptive:{domain}
```

使用 Hash 结构存储，field 为 identifier 的 SHA256 哈希（32位）。

## 最佳实践

### 1. 为关键选择器启用自适应

不需要为所有选择器启用，只为容易变化的关键选择器启用：

```python
# ✅ 推荐：为易变的选择器启用
articles = response.xpath(
    '//div[@class="article-list"]/div[@class="item"]',
    adaptive=True,
    identifier='article_items'
)

# ❌ 不推荐：为稳定的结构启用（如 HTML/Body）
html = response.xpath('/html', adaptive=True)  # 没必要
```

### 2. 使用描述性 identifier

```python
# ✅ 好的 identifier
response.xpath('//div[@class="news"]', adaptive=True, identifier='news_list')
response.xpath('//h1[@class="title"]', adaptive=True, identifier='article_title')

# ❌ 不好的 identifier
response.xpath('//div[@class="news"]', adaptive=True, identifier='div1')
```

### 3. 合理设置阈值

```python
# 宽松匹配（容忍较大变化）
response.xpath('//div[@class="item"]', adaptive=True, percentage=30)

# 严格匹配（只接受高度相似）
response.xpath('//div[@class="item"]', adaptive=True, percentage=80)
```

### 4. 监控匹配日志

框架会自动记录自适应匹配日志：

```
INFO: Adaptive matched 3 element(s) for selector '//div[@class="item"]'
```

如果看到匹配数量异常，检查网站是否有重大改版。

## 故障排查

### 问题1：选择器失效但未匹配到元素

**可能原因**：
- 网站改版过大，结构完全改变
- 相似度阈值设置过高

**解决方案**：
```python
# 降低阈值
response.xpath('//div[@class="item"]', adaptive=True, percentage=0)

# 检查指纹是否保存
# 查看 adaptive_fingerprints.db 是否有数据
```

### 问题2：匹配到错误的元素

**可能原因**：
- 页面中有多个相似元素
- 指纹不够独特

**解决方案**：
```python
# 提高阈值
response.xpath('//div[@class="item"]', adaptive=True, percentage=70)

# 使用更具体的选择器
response.xpath(
    '//div[@class="main"]/div[@class="list"]/div[@class="item"]',
    adaptive=True
)
```

### 问题3：Redis 连接失败

**错误信息**：
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**解决方案**：
```python
# 检查 Redis 配置
REDIS_HOST = 'localhost'  # 确保地址正确
REDIS_PORT = 6379
REDIS_PASSWORD = ''       # 如果不需要密码

# 或切换回 SQLite
ADAPTIVE_STORAGE_BACKEND = 'sqlite'
```

## 示例项目

查看完整示例：`examples/ofweek_standalone/ofweek_standalone/spiders/of_week_adaptive.py`

```bash
cd examples/ofweek_standalone
python run.py of_week_adaptive
```

## 测试验证

运行自适应元素追踪的完整测试：

```bash
# 测试真实场景（首次保存 + 改版匹配）
python tests/test_adaptive_real_scenario.py

# 测试多种改版场景（6种场景）
python tests/test_adaptive_multiple_scenarios.py

# 测试存储后端（SQLite + Redis）
python tests/test_storage_backends.py
```

所有测试通过，确保功能稳定可靠。

## 技术架构

### 核心模块

```
crawlo/tools/adaptive_selector/
├── __init__.py                  # 模块入口
├── element_fingerprint.py       # 元素指纹提取
├── similarity_matcher.py        # 相似度匹配算法
└── storage.py                   # 存储后端（SQLite/Redis）
```

### 集成点

```
crawlo/network/response.py
├── xpath(adaptive=True)         # XPath 自适应查询
├── css(adaptive=True)           # CSS 自适应查询
├── _save_element_fingerprint()  # 自动保存指纹
├── _retrieve_element_fingerprint()  # 自动加载指纹
└── _adaptive_relocate()         # 自适应重新定位
```

## 更新日志

### v1.6.0 (2026-04-08)

- ✨ 新增自适应元素追踪功能
- ✨ 支持 7 维度等权平均相似度算法
- ✨ SQLite 和 Redis 两种存储后端
- ✨ 支持 6 种网站改版场景
- 🎯 简化 API：单一 `adaptive=True` 参数
- 📦 默认数据库路径改为项目根目录
- 🧪 完整测试覆盖（36+ 测试用例）

## 常见问题

**Q: 需要手动配置存储后端吗？**  
A: 不需要。只需传入 `adaptive=True`，框架会自动初始化存储。

**Q: 指纹数据会无限增长吗？**  
A: 不会。相同 domain+identifier 的指纹会覆盖更新，不会重复存储。

**Q: 可以在分布式环境使用吗？**  
A: 可以。配置 `ADAPTIVE_STORAGE_BACKEND = 'redis'` 即可。

**Q: 性能影响大吗？**  
A: 影响很小。首次保存指纹增加 <10ms，匹配失效选择器增加 <100ms。

**Q: 如何查看已保存的指纹？**  
A: 直接查询 SQLite 数据库或 Redis key：
```bash
# SQLite
sqlite3 adaptive_fingerprints.db "SELECT domain, identifier FROM adaptive_fingerprints;"

# Redis
redis-cli HGETALL "crawlo:adaptive:example.com"
```
