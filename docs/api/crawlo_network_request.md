# crawlo.network.request

HTTP Request 封装模块
====================
提供功能完善的HTTP请求封装，支持:
- JSON/表单数据自动处理
- 优先级排序机制
- 安全的深拷贝操作
- 灵活的请求配置

## 导入的类

- deepcopy
- urlencode
- safe_url_string
- Dict
- Optional
- Callable
- Union
- Any
- TypeVar
- List
- escape_ajax

## 类

### RequestPriority
请求优先级常量和工具类

#### 方法

##### get_all_priorities
获取所有优先级常量

##### from_string
从字符串获取优先级值

### Request
封装一个 HTTP 请求对象，用于爬虫框架中表示一个待抓取的请求任务。
支持 JSON、表单、原始 body 提交，自动处理 Content-Type 与编码。
不支持文件上传（multipart/form-data），保持轻量。

#### 方法

##### __init__
初始化请求对象。

:param url: 请求 URL（必须）
:param callback: 成功回调函数
:param method: HTTP 方法，默认 GET
:param headers: 请求头
:param body: 原始请求体（bytes/str），若为 dict 且未使用 json_body/form_data，则自动转为 JSON
:param form_data: 表单数据，自动转为 application/x-www-form-urlencoded
:param json_body: JSON 数据，自动序列化并设置 Content-Type
:param cb_kwargs: 传递给 callback 的额外参数
:param cookies: Cookies 字典
:param meta: 元数据（跨中间件传递数据）
:param priority: 优先级（数值越小越优先）
:param dont_filter: 是否跳过去重
:param timeout: 超时时间（秒）
:param proxy: 代理地址，如 http://127.0.0.1:8080
:param allow_redirects: 是否允许重定向
:param auth: 认证元组 (username, password)
:param verify: 是否验证 SSL 证书
:param flags: 标记（用于调试或分类）
:param encoding: 字符编码，默认 utf-8

##### _safe_deepcopy_meta
安全地 deepcopy meta，移除 logger 后再复制

##### copy
创建当前请求的副本，保留所有高层语义（json_body/form_data）。

##### set_meta
设置 meta 中的某个键值，支持链式调用。

##### add_header
添加请求头，支持链式调用。

##### add_headers
批量添加请求头，支持链式调用。

##### set_proxy
设置代理，支持链式调用。

##### set_timeout
设置超时时间，支持链式调用。

##### add_flag
添加标记，支持链式调用。

##### remove_flag
移除标记，支持链式调用。

##### set_dynamic_loader
设置使用动态加载器，支持链式调用。

##### set_protocol_loader
强制使用协议加载器，支持链式调用。

##### _set_url
安全设置 URL，确保格式正确。

##### url

##### meta

##### __str__

##### __repr__

##### __lt__
用于按优先级排序
