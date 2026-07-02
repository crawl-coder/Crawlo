#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2026-04-07
# @Author  : crawl-coder
# @Desc    : Element Fingerprint Generator

Extracts structural features from lxml elements
to generate element fingerprints for similarity comparison.

Fingerprint includes:
- tag: Tag name
- text: Text content
- attributes: Attributes dictionary
- path: DOM path (tuple of tag names)
- parent_name: Parent tag name
- parent_attribs: Parent attributes
- parent_text: Parent text
- siblings: Sibling tag list
- children: Children tag list
"""
from typing import Dict, Optional, Tuple, List, Any

from lxml.html import HtmlElement, HtmlComment


# Excluded attributes (dynamically generated, may cause false positives)
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
        """Generate fingerprint from lxml HtmlElement

        Args:
            element: lxml HtmlElement object

        Returns:
            ElementFingerprint: Element fingerprint
        """
        parent = element.getparent()

        # Clean attributes: remove empty and forbidden attributes
        attributes = _clean_attributes(element, _FORBIDDEN_ATTRS)

        # Get DOM path
        path = _get_element_path(element)

        # Build fingerprint
        fingerprint = cls(
            tag=str(element.tag),
            text=element.text.strip() if element.text else None,
            attributes=attributes,
            path=path,
        )

        # Parent node information
        if parent is not None:
            fingerprint.parent_name = parent.tag
            fingerprint.parent_attribs = _clean_attributes(parent, _FORBIDDEN_ATTRS)
            fingerprint.parent_text = parent.text.strip() if parent.text else None

            # Sibling nodes (exclude self)
            siblings = [child.tag for child in parent.iterchildren() if child is not element]
            fingerprint.siblings = tuple(siblings) if siblings else None

        # Children node information
        children = [
            child.tag for child in element.iterchildren()
            if not isinstance(child, HtmlComment)
        ]
        fingerprint.children = tuple(children) if children else None

        return fingerprint

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary (for storage)"""
        result = {
            'tag': self.tag,
            'text': self.text,
            'attributes': self.attributes,
            'path': list(self.path),  # tuple → list for JSON serialization
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
        """Deserialize from dictionary

        Args:
            data: Serialized fingerprint dictionary

        Returns:
            ElementFingerprint: Element fingerprint
        """
        return cls(
            tag=data['tag'],
            text=data.get('text'),
            attributes=data.get('attributes') or {},
            path=(
                tuple(data['path'])
                if data.get('path') is not None else ()
            ),
            parent_name=data.get('parent_name'),
            parent_attribs=data.get('parent_attribs') or {},
            parent_text=data.get('parent_text'),
            siblings=(
                tuple(data['siblings'])
                if data.get('siblings') is not None else None
            ),
            children=(
                tuple(data['children'])
                if data.get('children') is not None else None
            ),
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
    """Clean element attributes, remove empty and forbidden attributes

    Args:
        element: lxml element
        forbidden: Attribute names to exclude

    Returns:
        Dict[str, str]: Cleaned attributes dictionary
    """
    if not element.attrib:
        return {}
    return {
        k: v.strip()
        for k, v in element.attrib.items()
        if v and v.strip() and k not in forbidden
    }


def _get_element_path(element: HtmlElement) -> Tuple[str, ...]:
    """Get tag path from element to root

    Example: ('html', 'body', 'div', 'article', 'p')

    Args:
        element: lxml element

    Returns:
        Tuple[str, ...]: Tag path
    """
    parent = element.getparent()
    if parent is None:
        return (element.tag,)
    return _get_element_path(parent) + (element.tag,)


def extract_domain_from_url(url: str) -> str:
    """Extract domain from URL for fingerprint storage partitioning

    Args:
        url: Full URL

    Returns:
        str: Domain name, e.g., 'example.com'
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
