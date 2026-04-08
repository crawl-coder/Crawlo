# Scrapling 核心特性借鉴方案

## 一、背景分析

### Scrapling 是什么

Scrapling 是一个自适应 Web 爬虫框架（GitHub 9k+ stars），其核心创新点：
1. **自适应元素追踪**：当网站改版导致选择器失效时，通过元素指纹+相似度匹配自动重新定位
2. **反反爬虫利器**：通过 TLS 指纹模拟、Camoufox 浏览器、Rebrowser-Playwright 等技术绕过 Cloudflare 等反爬系统

### Crawlo 现有能力对照

| 能力 | Scrapling | Crawlo 现状 |
|------|-----------|-------------|
| CSS/XPath 选择器 | ✅ | ✅ Response.css() / Response.xpath() |
| TLS 指纹模拟 | ✅ Fetcher(impersonate='chrome') | ✅ CurlCffiDownloader(CURL_BROWSER_TYPE) |
| 浏览器自动化 | ✅ DynamicFetcher(Playwright) | ✅ PlaywrightDownloader / DrissionPageDownloader |
| 隐身浏览器 | ✅ StealthyFetcher(Camoufox) | ❌ 无 |
| 自适应元素追踪 | ✅ auto_save + adaptive | ❌ 无 |
| Cloudflare 绕过 | ✅ solve_cloudflare=True | ❌ 无内置支持 |
| 指纹伪造 | ✅ Camoufox 全链路伪造 | ⚠️ 仅 TLS 层（curl_cffi） |

---

## 二、特性一：自适应元素追踪

### 2.1 Scrapling 的实现原理

Scrapling 的自适应追踪分为两个阶段：

**Save 阶段**（首次选择元素时）：
```python
products = page.css('.product', auto_save=True)
```
存储元素的"指纹"，包括：
- 标签名、文本内容、属性（名+值）
- 兄弟节点（仅标签名）
- 路径（仅标签名）
- 父节点：标签名、属性、文本

存储键为 `domain + identifier`（identifier 默认为选择器字符串），存入 SQLite。

**Match 阶段**（选择器失效时）：
```python
products = page.css('.product', adaptive=True)
```
当原选择器匹配不到元素时：
1. 加载存储的指纹
2. 遍历页面所有元素，逐一计算相似度分数
3. 返回相似度最高的元素

### 2.2 Crawlo 适配方案

#### 核心思路

不引入 Scrapling 作为依赖，而是在 Crawlo 的 Response 层实现轻量级自适应选择器。
原因：Scrapling 的解析器是自研的（非 lxml），而 Crawlo 使用 lxml + parsel，
直接集成 Scrapling 会导致解析器冲突和性能退化。

#### 模块设计

```
crawlo/
├── tools/
│   └── adaptive_selector/       # 新增工具模块
│       ├── __init__.py
│       ├── element_fingerprint.py   # 元素指纹生成与存储
│       ├── similarity_matcher.py    # 相似度匹配算法
│       └── storage.py              # 指纹存储（SQLite/Redis）
└── network/
    └── response.py              # 扩展 Response API
```

#### 2.2.1 元素指纹（ElementFingerprint）

```python
# crawlo/tools/adaptive_selector/element_fingerprint.py

class ElementFingerprint:
    """元素指纹 - 捕获元素的结构特征"""
    
    def __init__(self, element, url=""):
        self.tag = element.tag                          # 标签名
        self.text = self._normalize_text(element.text)  # 文本内容（归一化）
        self.attributes = dict(element.attrib)          # 属性字典
        self.sibling_tags = self._get_sibling_tags(element)  # 兄弟标签列表
        self.path_tags = self._get_path_tags(element)        # 路径标签列表
        self.parent_tag = element.getparent().tag if element.getparent() else None
        self.parent_attributes = dict(element.getparent().attrib) if element.getparent() else {}
        self.parent_text = self._normalize_text(element.getparent().text) if element.getparent() else ""
    
    def to_dict(self) -> dict:
        """序列化为字典（用于存储）"""
        ...
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ElementFingerprint':
        """从字典反序列化"""
        ...
```

#### 2.2.2 相似度匹配（SimilarityMatcher）

```python
# crawlo/tools/adaptive_selector/similarity_matcher.py

class SimilarityMatcher:
    """基于多维加权的元素相似度匹配"""
    
    # 权重配置（可通过 settings 覆盖）
    DEFAULT_WEIGHTS = {
        'tag': 0.25,           # 标签名相同 → 高权重
        'text': 0.20,          # 文本内容相似
        'attributes': 0.20,    # 属性重叠度
        'path': 0.15,          # DOM 路径相似
        'siblings': 0.10,      # 兄弟节点结构
        'parent': 0.10,        # 父节点特征
    }
    
    def calculate_similarity(self, fp1: ElementFingerprint, fp2: ElementFingerprint) -> float:
        """计算两个指纹的相似度 (0.0 ~ 1.0)"""
        score = 0.0
        score += self.DEFAULT_WEIGHTS['tag'] * (1.0 if fp1.tag == fp2.tag else 0.0)
        score += self.DEFAULT_WEIGHTS['text'] * self._text_similarity(fp1.text, fp2.text)
        score += self.DEFAULT_WEIGHTS['attributes'] * self._attr_overlap(fp1.attributes, fp2.attributes)
        score += self.DEFAULT_WEIGHTS['path'] * self._path_similarity(fp1.path_tags, fp2.path_tags)
        score += self.DEFAULT_WEIGHTS['siblings'] * self._sibling_similarity(fp1.sibling_tags, fp2.sibling_tags)
        score += self.DEFAULT_WEIGHTS['parent'] * self._parent_similarity(fp1, fp2)
        return score
    
    def find_best_match(self, target_fp: ElementFingerprint, 
                         candidates: List[ElementFingerprint],
                         threshold: float = 0.5) -> Optional[ElementFingerprint]:
        """在候选元素中找到最佳匹配"""
        best_score = 0.0
        best_match = None
        for candidate in candidates:
            score = self.calculate_similarity(target_fp, candidate)
            if score > best_score and score >= threshold:
                best_score = score
                best_match = candidate
        return best_match
```

#### 2.2.3 指纹存储（Storage）

```python
# crawlo/tools/adaptive_selector/storage.py

class FingerprintStorage:
    """指纹存储 - 支持 SQLite（单机）和 Redis（分布式）"""
    
    def __init__(self, backend='sqlite', redis_client=None):
        if backend == 'sqlite':
            self._storage = SqliteStorage()
        elif backend == 'redis':
            self._storage = RedisStorage(redis_client)
    
    def save(self, domain: str, identifier: str, fingerprint: ElementFingerprint):
        """保存指纹（同 domain+identifier 覆盖更新）"""
        ...
    
    def load(self, domain: str, identifier: str) -> Optional[ElementFingerprint]:
        """加载指纹"""
        ...
    
    def delete(self, domain: str, identifier: str):
        """删除指纹"""
        ...
```

#### 2.2.4 Response API 扩展

在 Response 层面提供最自然的 API，不改变现有用法：

```python
# 现有用法不变
items = response.css('.product')

# 新增：auto_save=True 保存指纹
items = response.css('.product', auto_save=True)

# 新增：adaptive=True 自适应匹配（选择器失效时自动降级为指纹匹配）
items = response.css('.product', adaptive=True)

# XPath 同样支持
items = response.xpath('//div[@class="product"]', adaptive=True)
```

#### 2.2.5 配置项

```python
# settings.py

# 自适应选择器开关（默认关闭，需要显式开启）
ADAPTIVE_SELECTOR_ENABLED = True

# 指纹存储后端：'sqlite' | 'redis'
ADAPTIVE_STORAGE_BACKEND = 'sqlite'

# SQLite 数据库路径
ADAPTIVE_SQLITE_PATH = '.crawlo/adaptive_fingerprints.db'

# 相似度阈值（低于此分数不返回匹配结果）
ADAPTIVE_SIMILARITY_THRESHOLD = 0.5

# 权重自定义
ADAPTIVE_SIMILARITY_WEIGHTS = {
    'tag': 0.25,
    'text': 0.20,
    'attributes': 0.20,
    'path': 0.15,
    'siblings': 0.10,
    'parent': 0.10,
}

# 是否在匹配失败时自动降级为自适应匹配
ADAPTIVE_AUTO_FALLBACK = False
```

#### 2.2.6 工作流程

```
Spider 调用 response.css('.product', auto_save=True)
  ↓
Response.css() 正常执行，返回 SelectorList
  ↓
遍历结果，为每个元素生成 ElementFingerprint
  ↓
存储到 FingerprintStorage（key = domain + selector）

--- 网站改版后 ---

Spider 调用 response.css('.product', adaptive=True)
  ↓
先尝试原始选择器
  ↓ 匹配成功 → 直接返回
  ↓ 匹配失败（0个结果）
从 FingerprintStorage 加载之前保存的指纹
  ↓
遍历页面所有同标签元素，生成候选指纹
  ↓
SimilarityMatcher 计算相似度，返回最佳匹配
  ↓
返回匹配的 SelectorList
```

---

## 三、特性二：反反爬虫利器

### 3.1 Scrapling 的实现原理

Scrapling 提供了三种 Fetcher：

| Fetcher | 底层技术 | 反爬能力 | 适用场景 |
|---------|---------|---------|---------|
| **Fetcher** | curl_cffi (httpx) | TLS 指纹模拟 | 普通反爬 |
| **StealthyFetcher** | Camoufox (Firefox) | 全链路指纹伪造 + Cloudflare 绕过 | 强反爬 |
| **DynamicFetcher** | Playwright | 浏览器自动化 | JS 渲染 |

核心反爬技术：
1. **TLS/JA3 指纹模拟**：curl_cffi 的 `impersonate` 参数，模拟真实浏览器的 TLS 握手
2. **Camoufox**：基于 Firefox 的隐身浏览器，全链路指纹伪造（Canvas、WebGL、AudioContext 等）
3. **Rebrowser-Playwright**：修补了 Playwright 的自动化检测漏洞（navigator.webdriver 等）
4. **Cloudflare Turnstile 自动解决**：StealthyFetcher 内置 solve_cloudflare=True

### 3.2 Crawlo 适配方案

#### 现有基础

Crawlo 已有的反爬能力：
- ✅ **CurlCffiDownloader**：支持 TLS 指纹模拟（`CURL_BROWSER_TYPE` 配置）
- ✅ **PlaywrightDownloader**：浏览器自动化
- ✅ **DrissionPageDownloader**：浏览器自动化
- ✅ **ProxyMiddleware**：代理轮换
- ❌ 无隐身浏览器支持
- ❌ 无 Cloudflare 自动绕过
- ❌ Playwright/DrissionPage 无反检测补丁

#### 3.2.1 方案一：隐身浏览器集成（推荐优先级：⭐⭐⭐）

**Camoufox 集成方案**

Camoufox 是基于 Firefox 的反检测浏览器，能伪造浏览器指纹的全链路特征。
它通过修改 Firefox 源码实现，比 Playwright 的 stealth 插件更可靠。

```
crawlo/
└── downloader/
    └── camoufox_downloader.py    # 新增
```

```python
# 配置示例
DOWNLOADER = 'crawlo.downloader.camoufox_downloader.CamoufoxDownloader'

# Camoufox 配置
CAMOUFOX_HEADLESS = True
CAMOUFOX_PROXY = None                    # 代理配置
CAMOUFOX_HUMANIZE = True                 # 模拟人类操作
CAMOUFOX_SOLVECLOUDFLARE = True          # 自动解决 Cloudflare
CAMOUFOX_BLOCK_RESOURCES = ['image', 'font', 'media']  # 屏蔽资源
```

**关键实现**：
- Camoufox 提供了 `AsyncCamoufox` 上下文管理器
- 返回的是 Playwright 的 Page 对象，可以复用 PlaywrightDownloader 的大部分逻辑
- 差异仅在浏览器启动方式不同（Camoufox vs 标准 Firefox）

**与 HybridDownloader 的集成**：
```python
# settings.py
HYBRID_DEFAULT_DYNAMIC_DOWNLOADER = 'camoufox'  # 使用 Camoufox 作为默认动态下载器

# 或在请求级别指定
yield Request(url, callback=self.parse, meta={
    'use_dynamic_loader': True,
    'dynamic_downloader_type': 'camoufox',  # 仅此请求使用 Camoufox
})
```

#### 3.2.2 方案二：Playwright 反检测增强（推荐优先级：⭐⭐⭐）

**Rebrowser-Playwright 集成方案**

Rebrowser-patches 修补了 Playwright 的自动化检测漏洞：
- `navigator.webdriver` 泄露
- CDP (Chrome DevTools Protocol) 检测
- `Runtime.enable` 检测
- Console API 检测

实现方式：不引入 rebrowser-patches 库，而是在 PlaywrightDownloader 的 `_create_context` 中注入反检测脚本：

```
crawlo/
└── downloader/
    ├── playwright_downloader.py       # 修改：添加反检测脚本注入
    └── stealth_scripts/               # 新增：反检测脚本集
        ├── __init__.py
        ├── navigator.py               # navigator.webdriver 隐藏
        ├── chrome_runtime.py          # Chrome Runtime API 伪装
        ├── webgl.py                   # WebGL 指纹伪造
        └── canvas.py                  # Canvas 指纹噪声
```

```python
# settings.py
# Playwright 反检测级别：'none' | 'basic' | 'advanced'
PLAYWRIGHT_STEALTH_LEVEL = 'basic'

# basic：仅隐藏 navigator.webdriver
# advanced：全链路指纹伪造（WebGL、Canvas、AudioContext 等）
```

**在 PlaywrightDownloader 中的实现位置**：

```python
async def _create_context(self):
    context = await self.browser.new_context(...)
    
    # 注入反检测脚本（根据配置级别）
    if self.stealth_level != 'none':
        await self._inject_stealth_scripts(context)
    
    return context

async def _inject_stealth_scripts(self, context):
    """注入反检测脚本"""
    # basic 级别
    await context.add_init_script(self._load_stealth_script('navigator'))
    
    if self.stealth_level == 'advanced':
        await context.add_init_script(self._load_stealth_script('chrome_runtime'))
        await context.add_init_script(self._load_stealth_script('webgl'))
        await context.add_init_script(self._load_stealth_script('canvas'))
```

#### 3.2.3 方案三：DrissionPage 反检测增强（推荐优先级：⭐⭐）

DrissionPage 使用的是真实 Chrome 浏览器，天然比 Playwright 更难被检测。
但仍有一些特征会被识别，需要增强：

```python
# settings.py
# DrissionPage 反检测配置
DRISSIONPAGE_STEALTH_ENABLED = True
DRISSIONPAGE_STEALTH_LEVEL = 'basic'  # 'none' | 'basic'
```

主要增强：
- 移除 `navigator.webdriver` 标记
- 移除 Chrome 自动化扩展标识
- 伪造 `navigator.plugins` 和 `navigator.languages`

#### 3.2.4 方案四：Cloudflare 自动绕过（推荐优先级：⭐⭐）

**检测 + 自动降级策略**

```
请求发送
  ↓
收到响应
  ↓
检测是否为 Cloudflare 挑战页面
  ↓ 是
自动降级到隐身浏览器重新请求
  ↓
解决挑战，获取真实页面
  ↓
返回响应
```

实现方式：作为中间件 `CloudflareBypassMiddleware`：

```python
# settings.py
DOWNLOADER_MIDDLEWARES = {
    'crawlo.middleware.cloudflare_bypass.CloudflareBypassMiddleware': 355,
}

# Cloudflare 绕过配置
CLOUDFLARE_BYPASS_ENABLED = True
CLOUDFLARE_BYPASS_MAX_RETRIES = 2
CLOUDFLARE_BYPASS_DOWNLOADER = 'camoufox'  # 使用哪个下载器来绕过
```

中间件逻辑：
```python
class CloudflareBypassMiddleware:
    """Cloudflare 自动绕过中间件"""
    
    async def process_response(self, request, response):
        # 1. 检测 Cloudflare 挑战页面
        if self._is_cloudflare_challenge(response):
            self.logger.info(f"Detected Cloudflare challenge for {request.url}")
            
            # 2. 自动降级到隐身浏览器
            new_request = request.replace(meta={
                **request.meta,
                'use_dynamic_loader': True,
                'dynamic_downloader_type': self.bypass_downloader,
                '_cloudflare_bypass': True,  # 标记，避免无限循环
            })
            return new_request  # 返回新请求重新调度
        
        return response
    
    def _is_cloudflare_challenge(self, response):
        """检测是否为 Cloudflare 挑战页面"""
        # 特征1：状态码 403 + Cloudflare header
        if response.status_code == 403:
            if 'cloudflare' in response.headers.get('server', '').lower():
                return True
        
        # 特征2：页面包含 Cloudflare 挑战标识
        if 'cf-browser-verification' in response.text:
            return True
        if 'challenge-platform' in response.text:
            return True
        if 'Just a moment' in response.text and 'cloudflare' in response.text.lower():
            return True
        
        return False
```

---

## 四、实施优先级与路线图

### Phase 1：反反爬虫基础（优先级最高）

| 任务 | 工作量 | 依赖 | 效果 |
|------|--------|------|------|
| Playwright 反检测脚本注入（basic） | 2天 | 无 | 隐藏 navigator.webdriver，解决 80% 的基础检测 |
| DrissionPage 反检测增强 | 1天 | 无 | 移除自动化标识 |
| CurlCffiDownloader impersonate 增强 | 0.5天 | 无 | 完善 TLS 指纹模拟 |

### Phase 2：隐身浏览器集成

| 任务 | 工作量 | 依赖 | 效果 |
|------|--------|------|------|
| CamoufoxDownloader 实现 | 3天 | camoufox 库 | 全链路指纹伪造，绕过 Cloudflare |
| HybridDownloader 集成 camoufox 类型 | 1天 | CamoufoxDownloader | 混合策略支持隐身浏览器 |
| CloudflareBypassMiddleware | 2天 | CamoufoxDownloader | 自动检测和绕过 Cloudflare |

### Phase 3：自适应元素追踪

| 任务 | 工作量 | 依赖 | 效果 |
|------|--------|------|------|
| ElementFingerprint 实现 | 2天 | 无 | 元素指纹生成 |
| SimilarityMatcher 实现 | 3天 | ElementFingerprint | 相似度匹配算法 |
| FingerprintStorage（SQLite） | 1天 | 无 | 单机指纹存储 |
| FingerprintStorage（Redis） | 1天 | 无 | 分布式指纹存储 |
| Response API 扩展 | 1天 | 上述全部 | css/xpath 支持 auto_save/adaptive |
| 配置系统完善 | 0.5天 | 上述全部 | settings 配置项 |

### Phase 4：高级特性

| 任务 | 工作量 | 依赖 | 效果 |
|------|--------|------|------|
| Playwright 反检测脚本（advanced） | 2天 | Phase 1 | WebGL/Canvas 指纹伪造 |
| 自适应匹配自动降级 | 1天 | Phase 3 | 选择器失效时自动切换指纹匹配 |
| 指纹相似度权重调优 | 2天 | Phase 3 | 根据实际场景优化权重 |

---

## 五、风险评估

### 5.1 自适应元素追踪的风险

| 风险 | 级别 | 应对措施 |
|------|------|---------|
| 误匹配：相似度计算不准确，匹配到错误元素 | 高 | 设置阈值（默认0.5），匹配时输出警告日志 |
| 性能：遍历页面所有元素计算相似度较慢 | 中 | 仅在同标签元素中搜索；限制候选数量；缓存计算结果 |
| 存储膨胀：大量指纹占用磁盘 | 低 | 按 domain 分区存储；支持过期清理 |
| 兼容性：与 lxml 的 SelectorList 集成 | 中 | 返回与 css() 相同类型的 SelectorList 对象 |

### 5.2 反反爬虫的风险

| 风险 | 级别 | 应对措施 |
|------|------|---------|
| Camoufox 依赖稳定性 | 中 | 作为可选依赖，不影响核心功能 |
| 反检测脚本过时 | 高 | 脚本独立文件管理，便于快速更新 |
| Cloudflare 检测升级 | 高 | 中间件方式实现，便于替换绕过策略 |
| 法律合规风险 | 低 | 框架仅提供技术手段，使用者自行承担合规责任 |

---

## 六、总结

本方案借鉴 Scrapling 的两大核心特性，结合 Crawlo 的实际架构设计：

1. **自适应元素追踪**：在 Response 层面扩展 css()/xpath() API，通过元素指纹 + 相似度匹配实现选择器自愈，降低网站改版导致的维护成本

2. **反反爬虫利器**：
   - 短期：为现有 Playwright/DrissionPage 注入反检测脚本（低风险、高收益）
   - 中期：集成 Camoufox 隐身浏览器 + CloudflareBypassMiddleware（完整反爬方案）
   - 长期：全链路指纹伪造（advanced stealth）

两个特性相对独立，可以并行开发。建议优先实施 Phase 1（反检测基础），因为投入小、见效快；Phase 3（自适应追踪）作为差异化特性，可以在反爬基础稳固后推进。
