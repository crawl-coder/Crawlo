# curl 命令转换

将浏览器 DevTools 复制的 `curl` 命令自动转换为 Crawlo Request 对象，快速复现浏览器请求，绕过反爬机制。

## 1. 使用场景

- **快速调试**：从浏览器复制请求 → 在 Shell 中执行 → 验证反爬绕过
- **API 测试**：直接复用已知的 curl 命令，无需手动构造 Request
- **请求复现**：保留完整的 Cookie、Header、认证信息
- **逆向分析**：快速验证抓包分析结果

---

## 2. Shell 中使用

### 基本用法

```python
# 启动 Shell
crawlo shell

# 在 Shell 中执行
>>> from_curl('curl https://example.com')
<Response [200]>
```

### 完整示例：从浏览器复制

1. **浏览器 DevTools 复制 curl**
   - 打开 DevTools → Network 面板
   - 右键请求 → Copy → Copy as cURL (bash)

2. **粘贴到 Shell**

```python
>>> cmd = '''curl 'https://api.example.com/v1/items?page=1' \\
      -H 'accept: application/json' \\
      -H 'authorization: Bearer eyJhbGciOiJIUzI1NiJ9.x' \\
      -H 'cookie: session=abc123; user=john' \\
      --compressed'''

>>> resp = from_curl(cmd)
<Response [200]>

>>> resp.json()
{'items': [...], 'total': 100}
```

### 命令行直接传入

```bash
crawlo shell --curl 'curl https://httpbin.org/post -X POST -d "key=val"'
```

Shell 启动后会自动执行该 curl 命令并显示结果。

---

## 3. 支持的 curl 选项

### URL 与方法

| 选项 | 说明 | 示例 |
|------|------|------|
| *(URL)* | 请求地址（必需） | `curl https://example.com` |
| `--url` | 显式指定 URL | `curl --url https://example.com` |
| `-X`, `--request` | HTTP 方法 | `curl -X POST` |
| `-I`, `--head` | HEAD 请求 | `curl -I https://example.com` |

### 请求头与 Cookie

| 选项 | 说明 | 转换结果 |
|------|------|---------|
| `-H`, `--header` | 添加请求头 | `headers={}` |
| `-b`, `--cookie` | 添加 Cookie | `cookies={}` |
| `-H 'cookie: ...'` | Cookie Header | 自动提取为 `cookies={}` |

### 请求体

| 选项 | 说明 | 转换结果 |
|------|------|---------|
| `-d`, `--data` | POST 数据 | `body` 或 `form_data` 或 `json_body` |
| `--data-raw` | 原始数据 | `body` 或 `json_body` |
| `--data-binary` | 二进制数据 | `body` |

**自动 Content-Type 判断**：

| Content-Type | 转换结果 |
|--------------|---------|
| `application/json` | `json_body`（自动解析 JSON） |
| `application/x-www-form-urlencoded` | `form_data`（键值对字典） |
| 其他 | `body`（原始字符串） |

### 认证与代理

| 选项 | 说明 | 转换结果 |
|------|------|---------|
| `-u`, `--user` | 基本认证 | `auth=(user, password)` |
| `--proxy`, `-x` | 代理服务器 | `proxy='http://...'` |

### 其他选项

| 选项 | 说明 | 转换结果 |
|------|------|---------|
| `-A`, `--user-agent` | 用户代理 | `headers['User-Agent']` |
| `-e`, `--referer` | Referer | `headers['Referer']` |
| `-k`, `--insecure` | 跳过 SSL 验证 | `verify=False` |
| `-L`, `--location` | 跟随重定向 | `allow_redirects=True` |
| `--max-redirs 0` | 禁止重定向 | `allow_redirects=False` |
| `--connect-timeout` | 连接超时 | `timeout` |
| `--compressed` | 自动解压 | 忽略（自动处理） |

---

## 4. 编程接口

### CurlParser 解析器

```python
from crawlo.utils.curl_parser import CurlParser
from crawlo.network.request import Request

# 方式1：解析为参数字典
params = CurlParser.parse('curl https://api.com -H "Key: val"')
print(params)
# {'url': 'https://api.com', 'headers': {'Key': 'val'}, 'method': 'GET'}

# 方式2：直接生成 Request 对象
request = CurlParser.to_request('curl https://api.com -d "key=val"')
print(request.url, request.method, request.body)

# 方式3：覆盖额外参数
request = CurlParser.to_request(
    'curl https://api.com',
    meta={'retry': 2},
    timeout=30
)
```

### 自定义请求处理

```python
# 解析后修改
params = CurlParser.parse('curl https://api.com -d "data"')
params['headers']['X-Custom'] = 'value'
params['meta'] = {'spider': 'myspider'}

request = Request(**params)
```

---

## 5. 完整示例

### 示例1：GET 请求带认证

```python
cmd = '''curl 'https://api.github.com/user' \\
  -H 'Accept: application/vnd.github.v3+json' \\
  -H 'Authorization: token ghp_xxxxx' \\
  -H 'User-Agent: MyBot/1.0' '''

resp = from_curl(cmd)
data = resp.json()
print(data['login'])
```

### 示例2：POST JSON 请求

```python
cmd = '''curl 'https://api.example.com/login' \\
  -X POST \\
  -H 'Content-Type: application/json' \\
  -d '{"username":"admin","password":"secret"}' '''

resp = from_curl(cmd)
print(resp.json())
```

### 示例3：表单提交

```python
cmd = '''curl 'https://example.com/submit' \\
  -X POST \\
  -H 'Content-Type: application/x-www-form-urlencoded' \\
  -d 'name=John&age=30&email=john@example.com' '''

resp = from_curl(cmd)
```

### 示例4：带 Cookie 的复杂请求

```python
cmd = '''curl 'https://shop.example.com/cart' \\
  -H 'Cookie: session=abc123; user_id=12345; csrf_token=xyz' \\
  -H 'Accept: text/html' \\
  -H 'Referer: https://shop.example.com/' '''

resp = from_curl(cmd)
# Cookie 自动提取为字典
print(resp.request.cookies)
# {'session': 'abc123', 'user_id': '12345', 'csrf_token': 'xyz'}
```

### 示例5：代理请求

```python
cmd = '''curl 'https://api.ipify.org' \\
  --proxy http://127.0.0.1:8080 \\
  --connect-timeout 10'''

resp = from_curl(cmd)
print(resp.text)
```

---

## 6. 注意事项

### 多行命令

- **Linux/macOS (bash)**：使用 `\` 续行
- **Windows (cmd)**：使用 `^` 续行
- **Shell 中**：建议使用三引号字符串

```python
# ✅ 推荐：三引号
cmd = '''curl https://example.com \\
  -H "Key: val"'''

# ⚠️ 单行命令（注意转义）
cmd = 'curl https://example.com -H "Key: val"'
```

### 引号处理

- curl 命令中的单引号和双引号需保持原样
- Shell 中建议使用三引号避免转义冲突

```python
# ✅ 正确
cmd = '''curl https://api.com -d '{"key":"val"}' '''

# ❌ 错误：引号冲突
cmd = 'curl https://api.com -d '{"key":"val"}' '
```

### 特殊字符

- curl 命令中的特殊字符（如 `$`、`!`）在 Shell 中可能被解释
- 建议将 curl 命令保存为变量后再传入

### Cookie Header vs -b 选项

```bash
# 方式1：Cookie Header（自动提取为 cookies 字典）
-H 'cookie: session=abc123; user=john'

# 方式2：-b 选项（标准方式）
-b 'session=abc123; user=john'
```

两种方式效果相同，解析器会自动处理。

---

## 7. 故障排查

### 解析失败：No URL found

- curl 命令中缺少 URL
- URL 被错误地当作参数值

**解决**：确保 URL 位置正确

```python
# ✅ 正确
CurlParser.parse('curl https://example.com')

# ❌ 错误
CurlParser.parse('curl -H "Key: val"')
```

### 解析失败：Option requires a value

- 某个选项（如 `-X`、`-H`）后面缺少值

**解决**：检查 curl 命令格式

```python
# ✅ 正确
CurlParser.parse('curl -X POST https://example.com')

# ❌ 错误
CurlParser.parse('curl -X')
```

### 请求体未正确解析

- 检查 Content-Type 是否正确设置
- JSON 数据需确保格式正确

```python
# ✅ 正确：JSON 会被解析
cmd = 'curl https://api.com -H "Content-Type: application/json" -d \'{"key":"val"}\''

# ⚠️ JSON 格式错误时会降级为 body 字符串
cmd = 'curl https://api.com -d \'{"key":val}\''
```

### 网络请求失败

- curl 命令中的 Cookie/Token 可能已过期
- 部分网站会校验 Referer 或 User-Agent

**解决**：从浏览器重新复制最新的 curl 命令
