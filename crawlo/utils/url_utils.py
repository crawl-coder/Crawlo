from urllib.parse import urldefrag
from w3lib.url import add_or_replace_parameter


def escape_ajax(url: str) -> str:
    """
    根据Google AJAX爬取规范转换URL（处理哈希片段#!）：
    https://developers.google.com/webmasters/ajax-crawling/docs/getting-started

    规则说明：
    1. 仅当URL包含 `#!` 时才转换（表示这是AJAX可爬取页面）
    2. 将 `#!key=value` 转换为 `?_escaped_fragment_=key%3Dvalue`
    3. 保留原始查询参数（如果有）

    示例：
    >>> escape_ajax("www.example.com/ajax.html#!key=value")
    'www.example.com/ajax.html?_escaped_fragment_=key%3Dvalue'
    >>> escape_ajax("www.example.com/ajax.html?k1=v1#!key=value")
    'www.example.com/ajax.html?k1=v1&_escaped_fragment_=key%3Dvalue'
    >>> escape_ajax("www.example.com/ajax.html#!")
    'www.example.com/ajax.html?_escaped_fragment_='

    非AJAX可爬取的URL（无#!）原样返回：
    >>> escape_ajax("www.example.com/ajax.html#normal")
    'www.example.com/ajax.html#normal'
    """
    # 分离URL的基础部分和哈希片段
    de_frag, frag = urldefrag(url)

    # 仅处理以"!"开头的哈希片段（Google规范）
    if not frag.startswith("!"):
        return url  # 不符合规则则原样返回

    # 调用辅助函数添加 `_escaped_fragment_` 参数
    return add_or_replace_parameter(de_frag, "_escaped_fragment_", frag[1:])


if __name__ == '__main__':
    f = escape_ajax('http://example.com/page#!')
    print(f)