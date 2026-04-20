# 💡 实战案例库

Crawlo 内置了多个实战案例，您可以直接参考其项目结构和抓取逻辑。以下精选了两个基于同一站点的不同抓取模式案例，方便您对比学习。

---

## 1. OFweek 维科网自适应爬虫 (动态渲染 + 自愈 🌟)
这个案例深入展示了 Crawlo 最核心的**动态网页处理**能力及独有的**自适应选择器 (Adaptive Selector)**。

- **源码位置**: `examples/ofweek_standalone/ofweek_standalone/spiders/of_week_adaptive.py`
- **核心技术**:
    - **智能渲染**: 自动调用 Playwright 处理 JavaScript 加载的内容。
    - **`adaptive=True`**: 开启元素指纹追踪，当网站改版（如 Class 名变更）导致选择器失效时，框架能自动匹配相似元素。
    - **`identifier`**: 为每个选择器分配唯一 ID，实现跨运行周期的定位自愈。
- **适用场景**: 现代 SPA 应用、经常改版导致选择器失效、有一定反爬措施的网站。

---

## 2. OFweek 维科网基础抓取 (高性能协议模式)
这个案例展示了在目标网站支持直接请求时，如何利用 **协议模式** 实现极致的抓取性能。

- **源码位置**: `examples/ofweek_standalone/ofweek_standalone/spiders/of_week.py`
- **核心技术**: 
    - **异步 I/O**: 利用 `aiohttp` 或 `httpx` 进行非阻塞抓取。
    - **轻量级解析**: 直接解析返回的 HTML 源码，无需启动浏览器内核。
    - **极低资源占用**: 相比动态渲染模式，协议模式的并发能力提升 10 倍以上。
- **适用场景**: 接口公开、结构稳定、追求抓取速度的大规模项目。

---

## 🚀 如何运行这些示例？

1. **进入示例项目目录**:
   ```bash
   cd examples/ofweek_standalone
   ```
2. **安装依赖**:
   ```bash
   pip install -r requirements.txt
   ```
3. **运行指定爬虫**:
   ```bash
   # 运行自适应动态爬虫
   crawlo run of_week_adaptive
   
   # 运行基础协议爬虫
   crawlo run of_week
   ```

---

## 🛠️ 更多实用工具 (Tests 目录)
如果您想快速了解某个特定功能，`tests/` 目录下有许多“最小可行性”脚本：

- `tests/cloudflare_test_spider.py`: 如何自动绕过 Cloudflare 验证。
- `tests/proxy_middleware_example.py`: 动态与静态代理的配置示例。
- `tests/notification_demo.py`: 飞书、钉钉等通知渠道的集成演示。
