# crawlo.network.response

HTTP Response 封装模块
=====================
提供功能丰富的HTTP响应封装，支持:
- 智能编码检测和解码
- XPath/CSS 选择器
- JSON 解析和缓存
- 正则表达式支持
- Cookie 处理

## 导入的类

- SimpleCookie
- Selector
- SelectorList
- Dict
- Any
- List
- Optional
- Union
- _urljoin
- DecodeError

## 类

### Response
HTTP响应的封装，提供数据解析的便捷方法。

功能特性:
- 智能编码检测和缓存
- 懒加载 Selector 实例
- JSON 解析和缓存
- 多类型数据提取

#### 方法

##### __init__

##### _determine_encoding
智能检测响应编码

##### text
将响应体(body)以正确的编码解码为字符串，并缓存结果。

##### is_success
检查响应是否成功 (2xx)

##### is_redirect
检查响应是否为重定向 (3xx)

##### is_client_error
检查响应是否为客户端错误 (4xx)

##### is_server_error
检查响应是否为服务器错误 (5xx)

##### content_type
获取响应的 Content-Type

##### content_length
获取响应的 Content-Length

##### json
将响应文本解析为 JSON 对象。

##### urljoin
拼接 URL，自动处理相对路径。

##### _selector
懒加载 Selector 实例

##### xpath
使用 XPath 选择器查询文档。

##### css
使用 CSS 选择器查询文档。

##### _is_xpath
判断查询语句是否为XPath

##### _extract_text_from_elements
从元素列表中提取文本并拼接

:param elements: SelectorList元素列表
:param join_str: 文本拼接分隔符
:return: 拼接后的文本

##### extract_text
提取单个元素的文本内容，支持CSS和XPath选择器

参数:
    xpath_or_css: XPath或CSS选择器
    join_str: 文本拼接分隔符(默认为空格)
    default: 默认返回值，当未找到元素时返回

返回:
    拼接后的纯文本字符串

##### extract_texts
提取多个元素的文本内容列表，支持CSS和XPath选择器

参数:
    xpath_or_css: XPath或CSS选择器
    join_str: 单个节点内文本拼接分隔符
    default: 默认返回值，当未找到元素时返回

返回:
    纯文本列表(每个元素对应一个节点的文本)

##### extract_attr
提取单个元素的属性值，支持CSS和XPath选择器

参数:
    xpath_or_css: XPath或CSS选择器
    attr_name: 属性名称
    default: 默认返回值

返回:
    属性值或默认值

##### extract_attrs
提取多个元素的属性值列表，支持CSS和XPath选择器

参数:
    xpath_or_css: XPath或CSS选择器
    attr_name: 属性名称
    default: 默认返回值

返回:
    属性值列表

##### re_search
在响应文本上执行正则表达式搜索。

##### re_findall
在响应文本上执行正则表达式查找。

##### get_cookies
从响应头中解析并返回Cookies。

##### meta
获取关联的 Request 对象的 meta 字典。

##### __str__
