#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2026-04-07
# @Author  : crawl-coder
# @Desc    : Crawlo 自适应元素选择器模块

实现自适应元素追踪，让选择器具备自愈能力。
当网站改版导致 CSS/XPath 选择器失效时，通过元素指纹+相似度匹配自动重新定位元素。

核心流程：
- adaptive=True → 选择器命中时自动保存/更新指纹
               → 选择器失效时自动加载指纹，用相似度算法匹配最接近的元素

支持的改版场景：
1. Class 名称变化
2. DOM 结构层级调整
3. 标签类型变化（div→article, h3→h4 等）
4. 属性顺序/内容变化
5. 文本内容微调
6. 混合变化（多种变化同时发生）

使用示例：
    # 列表页提取
    items = response.xpath('//div[@class="item"]', adaptive=True, identifier='list_items')
    
    # 详情页提取
    title = response.css('.article-title', adaptive=True, identifier='article_title')
"""
from .element_fingerprint import ElementFingerprint
from .similarity_matcher import SimilarityMatcher
from .storage import FingerprintStorage, SqliteStorage, RedisStorage

__all__ = [
    'ElementFingerprint',
    'SimilarityMatcher',
    'FingerprintStorage',
    'SqliteStorage',
    'RedisStorage',
]
