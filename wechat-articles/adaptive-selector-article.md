# 爬虫选择器"自愈术"：网站改版，你的代码为什么不报错了？

> 一行 `adaptive=True`，让你的爬虫学会"找人"。

---

做爬虫的都知道这痛苦：

昨天还跑得好好的，今天突然全崩了。

打开一看，网站 UI 改版了——产品列表从 `class="product"` 变成了 `class="item-card"`。就这一个字符的变化，你的爬虫直接罢工。如果你有 100 个爬虫，每个爬虫 20 个选择器，恭喜，你接下来的周末没了。

**但如果你的爬虫会"认人"呢？**

---

## 01. 人类的"认人"能力

想象你去参加同学聚会。十年不见，当年的瘦子成了胖子，平头变成了卷发，T恤变成了西装。但你一眼就认出他——因为你的大脑不是靠"精确匹配"来认人的，而是靠**多维特征加权匹配**。

这就像自适应选择器的工作方式。

传统爬虫的选择器逻辑是"精确匹配"：
```
//div[@class="product" and @data-id="123"]
```
只要任何一个属性变了，就找不到。这就是为什么网站改版会直接让爬虫"瘫痪"。

自适应选择器的工作方式则是"特征匹配"：
1. **记住**：首次抓取时，把元素的 7 个特征（标签、文本、class、层级、兄弟节点等）保存下来。
2. **寻找**：改版后，遍历页面所有元素，找到和"记忆"最相似的。
3. **返回**：把最相似的元素当作"目标元素"返回。

---

## 02. 内部原理

### 指纹：8 个维度刻画一个元素

| 维度 | 权重 | 作用 |
|------|------|------|
| 文本内容 | 2.0 | "产品名称"大概率不会变，最高权重 |
| 关键属性 (class/id/href) | 2.0 | class 可能变但不会面目全非 |
| 属性键值集合 | 1.5 | 用 Jaccard 集合比较，**不看顺序** |
| 标签名 | 1.0 | `<div>` 变成 `<section>`？这个不能变 |
| DOM 路径 | 1.0 | 从 `<html>` 到目标元素的标签链 |
| 父节点 | 1.0 | 爸爸是谁，长什么样 |
| 兄弟节点 | 0.5 | 邻居变化太快，权重最低 |

### 相似度：加权平均，比单纯的"等于/不等于"聪明 10 倍

```
总分 = (文本相似度 × 2.0 + class 相似度 × 2.0 + ... ) / 总权重 × 100
```

`difflib.SequenceMatcher` 负责模糊比对——"Product Title v1.0" 和 "Product Title v2.0" 的相似度高达 85% 以上，而传统选择器的精确比对只能返回 0。

### 真实案例

网站改版前后：
```html
<!-- 改版前 -->
<div class="product">
  <h2 class="name">Widget Pro</h2>
  <span class="price">$99</span>
</div>

<!-- 改版后 -->
<section>
  <article class="item">
    <h3 class="title">Widget Pro Max</h3>
    <span class="current-price">$99</span>
  </article>
</section>
```

自适应匹配结果：
- **DOM 路径相似度**：87.5% （虽然嵌套变了，但标签链仍有大量重合）
- **文本相似度**：93.3% （"Widget Pro" vs "Widget Pro Max"）
- **综合得分**：76.2% — 超过阈值，匹配成功！

---

## 03. 如何使用

只需在 `response.css()` 或 `response.xpath()` 中添加一个参数：

```python
# 之前：改版就崩溃
title = response.css('.product .name').get()

# 之后：改版自动恢复
title = response.css('.product .name', adaptive=True, identifier='product_name').get()
```

### 三个参数的完整形态

```python
response.xpath(
    '//div[@class="price"]',
    adaptive=True,          # 开启自适应
    identifier='price',     # 指纹标识（同页面不同选择器用不同 ID）
    percentage=50.0,        # 最低相似度阈值
)
```

### 高手进阶：find_similar() — 找到一个，定位全部

还有一个隐藏大招。你找到第一个商品后，能不能自动定位到其余商品？

```python
# 1. 先找到第一个商品（保存指纹）
response.css('.product-item', adaptive=True, identifier='product')

# 2. 自动找到列表中所有同类商品
all_products = response.find_similar('product', threshold=50)

# 3. 每个商品提取信息
for item in all_products:
    title = item.css('.name').get()
    price = item.css('.price').get()
    yield {'title': title, 'price': price}
```

`find_similar()` 基于 DOM 层级（同父元素 + 同深度 + 同标签）+ 属性/文本相似度，自动找到所有结构相同的相邻元素。原来需要精确选择器定位的"商品列表"，现在只需要找到一个参考物就够了。

### 实战技巧：ignore_attributes — 跳过 URL 噪音

`href`、`src` 这类属性在不同的页面元素间完全不同，会干扰匹配精度：

```python
from crawlo.helpers.adaptive_selector import SimilarityMatcher

# 忽略 href 和 src，提高匹配精度
matcher = SimilarityMatcher(ignore_attributes={'href', 'src'})

# 或直接在 find_similar 中指定
response.find_similar('nav_link', threshold=60, ignore_attributes={'href', 'src'})
```

### 场景覆盖表

| 网站变化类型 | 是否恢复 |
|---|---|
| class 名称改了 | ✅ |
| DOM 层级调整 | ✅ |
| 新增/替换属性 | ✅ |
| 文本内容微调 | ✅ |
| 相邻结构元素 | ✅ `find_similar()` |
| 标签类型变了 (`<h3>`→`<h2>`) | ⚠️ 受同标签预过滤影响 |

---

## 04. 性能：不会拖慢你的爬虫

有人会担心：每次改版都要遍历页面所有元素做相似计算？会不会很慢？

答案：几乎不影响，原因有三：

1. **同标签预过滤**：只扫描与目标相同标签的元素。比如你找的是 `<p>`，就只看 `<p>`，不看 `<div>`、`<span>`。

2. **扫描上限**：单次匹配最多 5000 个元素。即使是很长的文章页面，同标签元素也不会超过这个数。

3. **命中时零开销**：只在选择器失效时才触发匹配流程。正常运行时不增加任何计算。

---

## 05. 存储：SQLite 还是 Redis？

**SQLite**（默认）：
- 数据存在本地文件 `adaptive_fingerprints.db`
- 零配置，开箱即用
- 适合单机爬虫

**Redis**：
- 指纹存在 Redis，多个 Worker 共享
- 一台机器抓取并保存指纹，其他 Worker 直接受益
- 适合分布式爬虫集群

---

## 06. 一份配置，永久生效

```python
# settings.py
ADAPTIVE_STORAGE_BACKEND = 'sqlite'         # 或 'redis'
ADAPTIVE_SIMILARITY_THRESHOLD = 0.0         # 全局阈值，越低越包容
```

默认阈值 0.0 意味着不做限制，完全由算法在候选元素中选最优。如果你担心误匹配，可以适当调高。

---

## 07. 不只是"改版恢复"

自适应选择器还有一个隐藏价值：**自动识别页面布局**。

假设你要爬取多个电商网站的商品价格：
- 淘宝的 class 是 `.tm-price`
- 京东的 class 是 `.p-price`
- 拼多多的 class 是 `.goods-price`

传统做法是为每个网站单独写选择器。但如果你先用一个网站"教会"爬虫"价格元素长什么样"，自适应选择器就可以在其他网站上自动定位到价格——因为它记住的是"价格元素的特征"（通常包含数字、货币符号、特定标签和位置），而不是具体的 class 名称。

---

## 08. 实战案例：电商全站爬取

来看一个完整的电商爬虫，感受一下真实世界的威力：

```python
class ECommerceSpider(Spider):
    name = 'ecommerce'

    def parse(self, response):
        # === 列表页 ===
        # ① 自适应定位商品列表容器
        items = response.css('.product-grid .item', adaptive=True,
                             identifier='product_list')

        for item in items:
            # ② 自适应提取每条商品信息
            title = item.css('.title', adaptive=True, identifier='prod_title').get()
            price = item.css('.price', adaptive=True, identifier='prod_price').get()
            link = item.css('a::attr(href)', adaptive=True, identifier='prod_link').get()

            if title and link:
                yield Request(url=response.urljoin(link),
                              meta={'title': title, 'price': price},
                              callback=self.parse_detail)

        # ③ 如果商品列表定位失败（大改版），用 find_similar 兜底
        if not items:
            items = response.find_similar('product_list', threshold=40)
            for item in items:
                # 重新尝试提取
                ...

    def parse_detail(self, response):
        # === 详情页 ===
        # ④ 自适应提取正文（忽略 href/src 噪音）
        body = response.css('.article-body', adaptive=True,
                           identifier='article_body')
        content = body.css('::text').getall() if body else []

        # ⑤ 提取元数据
        author = response.xpath('//span[@class="author"]/text()',
                                adaptive=True, identifier='author').get()
        date = response.xpath('//time[@class="date"]/@datetime',
                              adaptive=True, identifier='pub_date').get()

        yield {
            'title': response.meta.get('title'),
            'price': response.meta.get('price'),
            'author': author,
            'date': date,
            'content': '\n'.join(content) if content else '',
        }
```

这个爬虫在网站改版时能够：
- **列表页**：class 变化 → 自适应恢复；完全找不到 → `find_similar()` 兜底
- **详情页**：content/author/date 三个选择器独立恢复
- **URL 噪音**：`ignore_attributes` 排除 href 干扰

一个爬虫、一次配置、长期免疫改版。

---

## 写在最后

爬虫领域有两个永恒的痛点：**反爬对抗**和**网站改版**。Crawlo 的自适应选择器解决的是后者——用算法替代人工修复，把时间还给真正重要的事。

**一行 `adaptive=True`，从此忘记改版。**

---

*本文技术基于 Crawlo 框架的自适应选择器模块。完整文档见 [Crawlo Docs](https://crawlo.readthedocs.io/)。*
