#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
选择器辅助工具模块
==================
提供用于处理parsel选择器的辅助函数，用于提取文本和属性等操作。

该模块包含以下主要函数：
- extract_text: 从元素列表中提取文本并拼接
- extract_texts: 从元素列表中提取多个文本列表
- extract_attr: 从元素列表中提取单个元素的属性值
- extract_attrs: 从元素列表中提取多个元素的属性值列表
- is_xpath: 判断查询语句是否为XPath

所有方法都采用了简洁直观的命名风格，便于记忆和使用。
"""

from typing import List, Any

from parsel import SelectorList


def extract_text(elements: SelectorList, join_str: str = " ") -> str:
    """
    从元素列表中提取文本并拼接
    
    :param elements: SelectorList元素列表
    :param join_str: 文本拼接分隔符
    :return: 拼接后的文本
    
    示例:
        title_elements = selector.css('title')
        title_text = extract_text(title_elements)
    """
    texts = []
    for element in elements:
        # 获取元素的所有文本节点
        if hasattr(element, 'xpath'):
            element_texts = element.xpath('.//text()').getall()
        else:
            element_texts = [str(element)]
        # 清理并添加非空文本
        for text in element_texts:
            cleaned = text.strip()
            if cleaned:
                texts.append(cleaned)
    return join_str.join(texts)


def extract_texts(elements: SelectorList, join_str: str = " ") -> List[str]:
    """
    从元素列表中提取多个文本列表
    
    :param elements: SelectorList元素列表
    :param join_str: 单个节点内文本拼接分隔符
    :return: 纯文本列表(每个元素对应一个节点的文本)
    
    示例:
        li_elements = selector.css('.list li')
        li_texts = extract_texts(li_elements)
    """
    result = []
    for element in elements:
        # 对每个元素提取文本
        if hasattr(element, 'xpath'):
            texts = element.xpath('.//text()').getall()
        else:
            texts = [str(element)]
            
        # 清理文本并拼接
        clean_texts = [text.strip() for text in texts if text.strip()]
        if clean_texts:
            result.append(join_str.join(clean_texts))
            
    return result


def extract_attr(elements: SelectorList, attr_name: str, default: Any = None) -> Any:
    """
    从元素列表中提取单个元素的属性值
    
    :param elements: SelectorList元素列表
    :param attr_name: 属性名称
    :param default: 默认返回值
    :return: 属性值或默认值
    
    示例:
        link_elements = selector.css('.link')
        link_href = extract_attr(link_elements, 'href')
    """
    # 使用parsel的attrib属性获取第一个匹配元素的属性值
    if hasattr(elements, 'attrib'):
        return elements.attrib.get(attr_name, default)
    # 如果elements是SelectorList，获取第一个元素的属性
    elif len(elements) > 0 and hasattr(elements[0], 'attrib'):
        return elements[0].attrib.get(attr_name, default)
    return default


def extract_attrs(elements: SelectorList, attr_name: str) -> List[Any]:
    """
    从元素列表中提取多个元素的属性值列表
    
    :param elements: SelectorList元素列表
    :param attr_name: 属性名称
    :return: 属性值列表
    
    示例:
        all_links = selector.css('a')
        all_hrefs = extract_attrs(all_links, 'href')
    """
    result = []
    for element in elements:
        # 使用parsel的attrib属性获取元素的属性值
        if hasattr(element, 'attrib'):
            attr_value = element.attrib.get(attr_name)
            if attr_value is not None:
                result.append(attr_value)
                
    return result


def is_xpath(query: str) -> bool:
    """
    判断查询语句是否为XPath
    
    :param query: 查询语句
    :return: 是否为XPath
    """
    return query.startswith(('/', '//', './'))


__all__ = [
    "extract_text",
    "extract_texts",
    "extract_attr",
    "extract_attrs",
    "is_xpath"
]