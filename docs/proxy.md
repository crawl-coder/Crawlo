# 🛠 ProxyMiddleware 使用手册

`ProxyMiddleware` 是一个通用、灵活、可扩展的代理中间件，支持从 API 动态获取代理 IP，并自动为请求添加代理。适用于各类需要动态代理的爬虫场景。

---

## ✅ 一、快速启用

在 `settings.py` 中启用代理功能：

```python
PROXY_ENABLED = True  # 设为 False 可禁用代理
```

---

## ✅ 二、基础配置

将以下配置添加到 `settings.py`：

```python
# 代理 API 地址（必填）
PROXY_API_URL = "https://api.proxy-provider.com/get"

# 代理提取方式（见下文详细说明）
PROXY_EXTRACTOR = "proxy"

# 代理刷新间隔（秒，避免频繁请求 API）
PROXY_REFRESH_INTERVAL = 60

# API 请求超时时间（秒）
PROXY_API_TIMEOUT = 10

# 日志级别（建议调试时使用 DEBUG）
LOG_LEVEL = "DEBUG"
```

> ✅ 所有参数均为可选，但 `PROXY_API_URL` 在启用时必须填写。

---

## ✅ 三、`PROXY_EXTRACTOR` 配置方式

`PROXY_EXTRACTOR` 决定如何从 API 响应中提取代理信息，支持三种方式：

| 方式 | 适用人群 | 示例 |
|------|----------|------|
| 字符串路径 | 普通用户 | `"proxy"` |
| 纯文本提取 | 普通用户 | `"__raw_text__"` |
| 自定义函数 | 开发者 | `custom_extractor_proxy` |

---

### 1. 字符串路径（推荐给普通用户）

适用于返回 JSON 的 API，使用 `.` 表示嵌套层级。

| API 返回示例 | `PROXY_EXTRACTOR` 配置 |
|-------------|------------------------|
```json
{ "proxy": "http://1.1.1.1:8080" }
```
```python
PROXY_EXTRACTOR = "proxy"
```
---
```json
{ "data": { "ip": "http://..." } }
```
```python
PROXY_EXTRACTOR = "data.ip"
```
---
```json
{ "result": { "http": "...", "https": "..." } }
```
```python
PROXY_EXTRACTOR = "result"
```

✅ **特点**：无需写代码，只需填写字段路径。

---

### 2. 纯文本响应（直接返回 IP）

如果 API 直接返回 IP 地址文本：

```text
http://user:pass@61.156.51.5:58131
```

使用特殊字段：

```python
PROXY_EXTRACTOR = "__raw_text__"
```

✅ 中间件会自动识别并使用该文本作为代理。

---

### 3. 自定义函数（高级用户）

当需要判断状态码、处理数组、或复杂逻辑时，可使用函数。

---

## 🧩 四、推荐模板：`custom_extractor_proxy`

这是一个通用模板函数，适用于大多数“带状态码”的代理 API。

### 📁 步骤1：创建 `utils/proxy_extractors.py`

```python
# utils/proxy_extractors.py

def custom_extractor_proxy(data: dict, key: str = 'proxy') -> dict | str | None:
    """
    通用代理提取函数：仅当 status == 0 时提取指定字段的代理信息。

    Args:
        data (dict): API 返回的 JSON 解析后的字典
        key (str): 代理字段名，默认为 'proxy'

    Returns:
        dict | str | None: 返回代理字符串或字典，失败返回 None
    """
    if data.get("status") == 0:
        return data.get(key)
    return None
```

---

### 🧩 步骤2：在 `settings.py` 中引用

```python
# settings.py

from utils.proxy_extractors import custom_extractor_proxy

PROXY_EXTRACTOR = custom_extractor_proxy
```

> ✅ 注意：`custom_extractor_proxy` 是函数对象，**不要加括号**。

---

### 🔧 高级用法：适配不同字段名

| API 字段名 | 配置方式 |
|-----------|----------|
| `"proxy"` | `PROXY_EXTRACTOR = custom_extractor_proxy` |
| `"result"` | `PROXY_EXTRACTOR = lambda d: custom_extractor_proxy(d, key="result")` |
| `"data"` | `PROXY_EXTRACTOR = lambda d: custom_extractor_proxy(d, key="data")` |

✅ 使用 `lambda` 包装，无需修改原函数。

---

### 🧪 示例：支持多种返回格式

#### ✅ 示例1：标准格式（推荐）

```json
{
  "status": 0,
  "desc": "success",
  "proxy": {
    "http": "http://user:pass@61.156.51.5:58131",
    "https": "http://user:pass@61.156.51.5:58131"
  }
}
```

✅ 配置：
```python
PROXY_EXTRACTOR = custom_extractor_proxy
```

#### ✅ 示例2：字段名为 `result`

```json
{
  "status": 0,
  "result": "http://user:pass@61.156.51.5:58131"
}
```

✅ 配置：
```python
PROXY_EXTRACTOR = lambda d: custom_extractor_proxy(d, key="result")
```

#### ✅ 示例3：状态码为 `code == 1`

> ❌ 不匹配，需扩展新函数：

```python
def custom_extractor_v2(data):
    if data.get("code") == 1:
        return data.get("proxy")
    return None
```

```python
PROXY_EXTRACTOR = custom_extractor_v2
```

---

## ✅ 五、支持的代理格式

| 格式 | 示例 |
|------|------|
| HTTP 代理 | `http://ip:port` |
| 带认证代理 | `http://用户名:密码@ip:port` |
| 多协议支持 | `{"http": "...", "https": "..."}` |

> 🔔 所有代理必须为完整 URL 格式。

---

## ✅ 六、完整 `settings.py` 示例

```python
# settings.py

# 启用代理
PROXY_ENABLED = True

# API 地址
PROXY_API_URL = "https://api.proxy-provider.com/get"

# 提取方式（根据实际返回结构选择）
PROXY_EXTRACTOR = "proxy"
# 或
# from utils.proxy_extractors import custom_extractor_proxy
# PROXY_EXTRACTOR = custom_extractor_proxy

# 刷新间隔
PROXY_REFRESH_INTERVAL = 60

# 超时时间
PROXY_API_TIMEOUT = 10

# 日志
LOG_LEVEL = "DEBUG"
```

---

## ✅ 七、日志调试

启用 `DEBUG` 日志查看代理获取过程：

```python
LOG_LEVEL = "DEBUG"
```

日志输出示例：

```
[ProxyMiddleware] 请求代理 API: https://api.example.com/get
[ProxyMiddleware] 更新代理缓存: http://user:pass@61.156.51.5:58131
[ProxyMiddleware] 分配代理 → http://... | https://example.com
```

---

## ✅ 八、注意事项

- ❗ `PROXY_API_URL` 必须返回 **可访问的 JSON 或纯文本**
- ❗ 代理必须为完整 URL 格式（含 `http://`）
- ❗ 自定义函数需提前导入，不能写在 `settings.py` 内部（除非是模块级）
- ⚠️ 若 `PROXY_ENABLED = False`，中间件将跳过所有代理逻辑
- ✅ 建议将提取器统一放在 `utils/proxy_extractors.py` 中，便于维护

---

## 📚 总结

| 用户类型 | 推荐方式 |
|--------|----------|
| 普通用户 | 使用 `字符串路径`，如 `"proxy"` |
| 进阶用户 | 使用 `__raw_text__` 处理纯文本 |
| 开发用户 | 使用 `custom_extractor_proxy` 模板函数 |

> ✅ 一行配置，轻松使用动态代理！

---

## 🧰 附：模板文件下载

你可以直接复制以下内容保存为 `utils/proxy_extractors.py`：

```python
# utils/proxy_extractors.py

def custom_extractor_proxy(data: dict, key: str = 'proxy') -> dict | str | None:
    """
    通用代理提取函数：仅当 status == 0 时提取指定字段的代理信息。
    """
    if data.get("status") == 0:
        return data.get(key)
    return None
```

---

