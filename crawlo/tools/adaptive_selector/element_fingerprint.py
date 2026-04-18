#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2026-04-07
# @Author  : crawl-coder
# @Desc    : 元素指纹生成器

提取 lxml 元素的结构特征，
生成可用于相似度比较的元素指纹。

指纹包含：
- tag: 标签名
- text: 文本内容
- attributes: 属性字典
- path: DOM 路径（标签名元组）
- parent_name: 父节点标签名
- parent_attribs: 父节点属性
- parent_text: 父节点文本
- siblings: 兄弟节点标签列表
- children: 子节点标签列表
"""
from typing import Dict, Optional, Tuple, List

from lxml.html import HtmlElement, HtmlComment


# 不计入指纹的属性（动态生成的，会导致误判）
_FORBIDDEN_ATTRS = ('data-reactid', 'data-react-checksum', 'ng-reflect-name')


class ElementFingerprint:
    """元素指纹 - 捕获元素的独特结构特征"""

    __slots__ = (
        'tag', 'text', 'attributes', 'path',
        'parent_name', 'parent_attribs', 'parent_text',
        'siblings', 'children',
    )

    def __init__(
        self,
        tag: str,
        text: Optional[str] = None,
        attributes: Optional[Dict[str, str]] = None,
        path: Tuple[str, ...] = (),
        parent_name: Optional[str] = None,
        parent_attribs: Optional[Dict[str, str]] = None,
        parent_text: Optional[str] = None,
        siblings: Optional[Tuple[str, ...]] = None,
        children: Optional[Tuple[str, ...]] = None,
    ):
        self.tag = tag
        self.text = text
        self.attributes = attributes or {}
        self.path = path
        self.parent_name = parent_name
        self.parent_attribs = parent_attribs or {}
        self.parent_text = parent_text
        self.siblings = siblings
        self.children = children

    @classmethod
    def from_element(cls, element: HtmlElement) -> 'ElementFingerprint':
        """从 lxml HtmlElement 生成指纹

        Args:
            element: lxml 的 HtmlElement 对象

        Returns:
            ElementFingerprint: 元素指纹
        """
        parent = element.getparent()

        # 清理属性：移除空值和禁用属性
        attributes = _clean_attributes(element, _FORBIDDEN_ATTRS)

        # 获取 DOM 路径
        path = _get_element_path(element)

        # 构建指纹
        fingerprint = cls(
            tag=str(element.tag),
            text=element.text.strip() if element.text else None,
            attributes=attributes,
            path=path,
        )

        # 父节点信息
        if parent is not None:
            fingerprint.parent_name = parent.tag
            fingerprint.parent_attribs = _clean_attributes(parent, _FORBIDDEN_ATTRS)
            fingerprint.parent_text = parent.text.strip() if parent.text else None

            # 兄弟节点（排除自身）
            siblings = [child.tag for child in parent.iterchildren() if child is not element]
            fingerprint.siblings = tuple(siblings) if siblings else None

        # 子节点信息
        children = [
            child.tag for child in element.iterchildren()
            if not isinstance(child, HtmlComment)
        ]
        fingerprint.children = tuple(children) if children else None

        return fingerprint

    def to_dict(self) -> Dict:
        """序列化为字典（用于存储）"""
        result = {
            'tag': self.tag,
            'text': self.text,
            'attributes': self.attributes,
            'path': list(self.path),  # tuple → list 方便 JSON 序列化
        }
        if self.parent_name is not None:
            result['parent_name'] = self.parent_name
            result['parent_attribs'] = self.parent_attribs
            result['parent_text'] = self.parent_text
        if self.siblings is not None:
            result['siblings'] = list(self.siblings)
        if self.children is not None:
            result['children'] = list(self.children)
        return result

    @classmethod
    def from_dict(cls, data: Dict) -> 'ElementFingerprint':
        """从字典反序列化

        Args:
            data: 序列化的指纹字典

        Returns:
            ElementFingerprint: 元素指纹
        """
        return cls(
            tag=data['tag'],
            text=data.get('text'),
            attributes=data.get('attributes', {}),
            path=tuple(data.get('path', ())),
            parent_name=data.get('parent_name'),
            parent_attribs=data.get('parent_attribs', {}),
            parent_text=data.get('parent_text'),
            siblings=tuple(data['siblings']) if 'siblings' in data else None,
            children=tuple(data['children']) if 'children' in data else None,
        )

    def __repr__(self) -> str:
        attrs_preview = ''
        if self.attributes:
            preview_items = list(self.attributes.items())[:3]
            attrs_preview = ' ' + ' '.join(f'{k}="{v}"' for k, v in preview_items)
            if len(self.attributes) > 3:
                attrs_preview += ' ...'
        return f'<Fingerprint <{self.tag}{attrs_preview}>>'


def _clean_attributes(element: HtmlElement, forbidden: Tuple[str, ...] = ()) -> Dict[str, str]:
    """清理元素属性，移除空值和禁用属性

    Args:
        element: lxml 元素
        forbidden: 需要排除的属性名

    Returns:
        Dict[str, str]: 清理后的属性字典
    """
    if not element.attrib:
        return {}
    return {
        k: v.strip()
        for k, v in element.attrib.items()
        if v and v.strip() and k not in forbidden
    }


def _get_element_path(element: HtmlElement) -> Tuple[str, ...]:
    """获取元素到根节点的标签路径

    示例: ('html', 'body', 'div', 'article', 'p')

    Args:
        element: lxml 元素

    Returns:
        Tuple[str, ...]: 标签路径
    """
    parent = element.getparent()
    if parent is None:
        return (element.tag,)
    return _get_element_path(parent) + (element.tag,)


def extract_domain_from_url(url: str) -> str:
    """从 URL 中提取域名，用作指纹存储的分区键

    Args:
        url: 完整 URL

    Returns:
        str: 域名，如 'example.com'
    """
    if not url:
        return 'default'
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        # 移除端口号
        if ':' in netloc:
            netloc = netloc.split(':')[0]
        # 移除 www 前缀
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        return netloc or 'default'
    except Exception:
        return 'default'
