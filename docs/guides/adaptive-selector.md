# 自适应选择器 (Adaptive Selector)

> 基于元素指纹 + 多维度加权相似度匹配的 CSS/XPath 自愈机制

## 概述

网站改版是爬虫最常见的痛点。自适应选择器通过**元素指纹记忆 + 多维度相似度匹配**，让选择器在页面 HTML 发生变化（class 名称、标签类型、DOM 层级、文本内容等）时自动恢复。

### 核心原理

```
首次抓取:  选择器命中 → 提取元素指纹 → 保存到 SQLite/Redis
网站改版:  选择器失效 → 加载保存的指纹 → 遍历页面匹配 → 返回最相似元素
```

### 适用场景

| 改版类型 | 示例 | 是否生效 |
|---|---|---|
| class 名称变化 | `.product` → `.item-card` | ✅ |
| DOM 层级调整 | `<div><p>` → `<section><p>` | ✅ |
| 属性新增/变化 | `class="btn"` → `class="btn primary"` | ✅ |
| 文本微调 | `"Price: $10"` → `"Price: $12"` | ✅ |
| 标签类型变化 | `<h3>` → `<h2>` | ⚠️ 需重新抓取指纹 |

> 标签类型变化受同标签预过滤策略影响，详见[算法设计](#算法设计)。

## 快速开始

### 基本用法

```python
class MySpider(Spider):
    def parse(self, response):
        # 自适应模式：首次命中时保存指纹，失效时自动匹配恢复
        items = response.css('.product-list li', adaptive=True, identifier='products')

        for item in items:
            title = item.xpath('.//h2/a/text()', adaptive=True, identifier='title').get()
            price = item.css('.price', adaptive=True, identifier='price').get()
            yield {'title': title, 'price': price}
```

### 参数说明

| 参数 | 默认值 | 说明 |
|---|---|---|
| `adaptive` | `False` | 启用自适应追踪 |
| `identifier` | query 字符串 | 指纹标识符，同页面复用的选择器应使用不同 identifier |
| `percentage` | `50.0` | 改版匹配时的最低相似度阈值（0-100） |

### 配置

```python
# settings.py — 无需额外配置即可使用（默认 SQLite 存储）
# 高级配置（可选）：
ADAPTIVE_STORAGE_BACKEND = 'sqlite'       # 'sqlite'（单机）或 'redis'（分布式）
ADAPTIVE_SQLITE_PATH = 'adaptive_fingerprints.db'
ADAPTIVE_SIMILARITY_THRESHOLD = 0.0       # 全局最低相似度阈值
```

### 手动配置（不使用 settings）

```python
from crawlo.network.response import Response

Response.configure_adaptive(
    backend='sqlite',                     # 或 'redis'
    storage_file='my_fingerprints.db',    # SQLite 路径
    threshold=30.0,                       # 相似度阈值
)
```

## 算法设计

### 1. 元素指纹（8 维度）

从 lxml 元素中提取结构特征，排除框架动态属性：

| 维度 | 权重 | 说明 |
|---|---|---|
| `text` | 2.0 | 元素文本内容（通常最稳定） |
| `important_attrs` | 2.0 | 关键属性：class/id/href/src |
| `attributes` | 1.5 | 属性键值集合（Jaccard 比较，**序无关**） |
| `tag` | 1.0 | 标签名（精确匹配） |
| `path` | 1.0 | DOM 层级路径（如 `html > body > div > p`） |
| `parent` | 1.0 | 父节点信息（标签/属性/文本） |
| `siblings` | 0.5 | 兄弟节点标签名（变化多，权重低） |

### 2. 多维度加权相似度

```
总分 = Σ(维度分数 × 权重) / Σ权重 × 100

各维度分数:
  tag:     精确匹配 → 1 或 0
  text:    SequenceMatcher 模糊匹配 → 0.0~1.0
  attrs:   key 用 Jaccard(交集/并集) + value 用 SequenceMatcher → 0.0~1.0
  path:    SequenceMatcher 比较标签路径元组
  parent:  SequenceMatcher 比较父标签名/属性/文本
  siblings: SequenceMatcher 比较兄弟元组
```

### 3. 性能优化

- **同标签预过滤**：只扫描与目标标签相同的元素（`xpath('.//tag')`）
- **扫描上限**：单次匹配最多扫描 `MAX_SCAN_ELEMENTS = 5000` 个元素
- **LRU 缓存**：内存缓存 128 条指纹，避免频繁磁盘 I/O

### 4. 指纹锁定

指纹仅在**首次选择器命中时保存**，后续命中不覆盖。确保网站渐进改版时始终用原始指纹作为恢复基准。

### 5. 存储 Key 隔离

存储 key 为 `domain + identifier + @path_hash`，同域名不同页面的相同 identifier 不会冲突。

## 存储后端

### SQLite（默认，单机）

```python
ADAPTIVE_STORAGE_BACKEND = 'sqlite'
ADAPTIVE_SQLITE_PATH = 'adaptive_fingerprints.db'
```

- WAL 模式，支持并发
- 文件零配置，开箱即用
- `INSERT OR REPLACE` 语义，同 key 覆盖

### Redis（分布式）

```python
ADAPTIVE_STORAGE_BACKEND = 'redis'
# 复用项目已有的 Redis 配置
```

- Hash 结构：`crawlo:adaptive:{domain}` → `{sha256(identifier)[:32]}` → JSON
- 多 Worker 共享指纹，一台抓取保存，所有 Worker 受益

## 独立使用核心类

```python
from crawlo.helpers import ElementFingerprint, SimilarityMatcher, FingerprintStorage
from lxml.html import fromstring

# 1. 保存指纹
html = fromstring(response.body)
element = html.xpath('//div[@class="product"]')[0]
fp = ElementFingerprint.from_element(element)

storage = FingerprintStorage(backend='sqlite')
storage.save(response.url, 'product_list', fp)

# 2. 改版后恢复
matcher = SimilarityMatcher(threshold=30)
data = storage.retrieve(response.url, 'product_list')
if data:
    target = ElementFingerprint.from_dict(data)
    matches = matcher.find_best_matches(target, modified_html)
```

## 调试

设置日志级别为 `DEBUG` 可查看匹配详情：

```python
LOG_LEVEL = 'DEBUG'
```

输出示例：
```
[SimilarityMatcher] DEBUG: Best match score: 87.5% (3 element(s))
[SimilarityMatcher] DEBUG:   87.5% -> 3 element(s)
[SimilarityMatcher] DEBUG:   72.3% -> 1 element(s)
[SimilarityMatcher] DEBUG:   45.1% -> 2 element(s)
```

## 限制与建议

| 限制 | 说明 | 建议 |
|---|---|---|
| 标签变化 | 同标签预过滤会跳过不同标签的元素 | 标签变化后手动删除指纹或重命名 identifier |
| 文本大幅变化 | 文本权重最高(2.0)，完全改版后可能低于阈值 | 降低 `percentage` 或使用更稳定的属性做 identifier |
| 跨域不共享 | 指纹按域名分区存储 | 多域名网站为每个域名使用不同的 identifier |
| 指纹不自动刷新 | 首次保存后锁定不覆盖 | 调用 `Response.cleanup_adaptive()` 清除所有指纹后重新建立 |

## 示例项目

完整示例见 `examples/ofweek_standalone/ofweek_standalone/spiders/of_week_adaptive.py`。
