# 代理配置指南

> 静态列表 + 动态 API — 两种代理模式，自动健康跟踪与失败降级。

## 概述

Crawlo 通过 `ProxyMiddleware` 实现代理分配与健康跟踪。

> **前置条件（必须）**：`ProxyMiddleware` 不在默认中间件装配中。仅在
> settings 里写 `PROXY_LIST` / `PROXY_API_URL` **不会生效**，必须先注册：
>
> ```python
> # settings.py
> MIDDLEWARES = {
>     'crawlo.middleware.ProxyMiddleware': 500,   # 短名或完整路径均可
> }
> ```

## 静态代理

```python
# settings.py
MIDDLEWARES = {
    'crawlo.middleware.ProxyMiddleware': 500,
}
PROXY_LIST = [
    "http://user:pass@proxy1.example.com:8080",
    "http://user:pass@proxy2.example.com:8080",
]
```

轮询策略：每次请求从池中**随机抽取**（排除已知失败项）。

支持的协议：`http`、`https`（下载器按 URL 隧道转发）。
> `socks5://` 仅 `curl-cffi` 下载器支持；aiohttp/httpx 下载器不支持 socks
> （如需请自建本地转换网关，如 gost/privoxy）。

## 动态代理 API

从代理 API 获取：

```python
PROXY_API_URL = "http://proxy-pool.example.com/api/get"
PROXY_EXTRACTOR = "proxy"   # 从 JSON 响应的 'proxy' 字段提取（仅支持字段名）
```

API 响应格式：

```json
{
    "proxy": "http://1.2.3.4:8080",
    "expire": 300
}
```

### 提取器说明

`PROXY_EXTRACTOR` **只支持 JSON 响应中的顶层字段名（字符串）**：

- `"proxy"`（默认）：取 `data["proxy"]`；
- 其他字段名：如 `"data"` 取 `data["data"]`；
- 提取结果必须是 `http://` 或 `https://` 前缀的字符串，否则视为本次无代理；
- **不支持** jsonpath 表达式或自定义函数——复杂响应结构请在代理网关侧
  聚合成 `{"proxy": "http://ip:port"}` 再接入（见
  [代理池部署](../deployment/proxy-rotation.md)）。

## 失败处理与自动切换

失败处理由两层协同完成：

**ProxyMiddleware（健康跟踪）**

- 连接类异常（超时/连接错误等）计入该代理失败次数；
- HTTP 响应 `403/407/429` 也计为该代理的失败信号（IP 被识别的典型特征）；
- 失败 ≥ `PROXY_MAX_FAILED_ATTEMPTS`（默认 3）→ 加入失败列表不再选用；
- 失败项经过 `PROXY_FAILED_TTL`（默认 300 秒）后自动恢复可选；
- 全部代理不可用时**降级直连**，并通过 stats 指标 `proxy/direct_downgrade`
  记录（可对接监控告警，见 [监控与告警](../deployment/monitoring-alerting.md)）。

**RetryMiddleware（重试与切换）**

```python
MAX_RETRY_TIMES = 3      # 最大重试次数
RETRY_PRIORITY = -100    # 重试请求优先级调整（负数降低优先级）
```

- 网络错误（连接失败/超时）→ 清除当前代理 → 重试时由代理中间件重新分配；
- HTTP 状态码错误（5xx 等）→ 先保留当前代理重试；连续超过内部切换阈值
  （约 `MAX_RETRY_TIMES` 一半，至少 1）后才清除代理直连；
- 重试带指数退避：第 n 次等待 `2^(n-1)` 秒。

> 注意：不存在名为 `PROXY_SWITCH_THRESHOLD` 的配置项——切换阈值由 <!-- phantom-guard: ignore -->
> `MAX_RETRY_TIMES` 自动推导，无需也无法单独配置。
> 同理，框架不读取 `PROXY_ENABLED`：注册中间件 + 配置任一代理来源即为启用， <!-- phantom-guard: ignore -->
> 不注册中间件即为禁用；也没有 `PROXY_WHITELIST` 免代理白名单功能 <!-- phantom-guard: ignore -->
> （可在自定义中间件中对请求置 `request.proxy = None` 前拦截实现）。

## 配置总览

```python
# settings.py — 全部有效代理配置
MIDDLEWARES = {
    'crawlo.middleware.ProxyMiddleware': 500,
}

# 静态代理
PROXY_LIST = [
    "http://proxy1:8080",
    "http://proxy2:8080",
]

# 动态代理（与 PROXY_LIST 二选一，同时配置时静态优先）
PROXY_API_URL = "http://proxy-api.com/get-proxy"
PROXY_EXTRACTOR = "proxy"                # JSON 顶层字段名
PROXY_API_TTL = 0                        # API 结果缓存秒数（默认 0=逐请求拉取）

# 健康跟踪
PROXY_MAX_FAILED_ATTEMPTS = 3            # 失败阈值，达到后拉黑
PROXY_FAILED_TTL = 300                   # 拉黑后的恢复时间（秒）

# 浏览器下载器代理（Playwright/Camoufox/CloakBrowser 走独立配置）
CLOAKBROWSER_PROXY = None                # 或 "http://proxy:7890"
```

在单个请求上显式指定代理（跳过中间件分配）：

```python
yield Request(url="https://example.com", proxy="http://proxy:8080")
```
