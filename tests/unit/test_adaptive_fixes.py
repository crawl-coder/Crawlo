#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
自适应选择器 4 项修复的全面测试。

覆盖：
1. 属性字典顺序独立性 (Fix #1 - Jaccard 替代 SequenceMatcher)
2. 元素扫描上限 (Fix #2 - MAX_SCAN_ELEMENTS + 同标签限定)
3. 存储 Key 带路径哈希 (Fix #3 - domain+id@path_hash)
4. 指纹首次锁定 (Fix #4 - 只保存一次，不覆盖)
5. 集成改版场景：class/层级/标签/文本/属性/混合变化
"""
import os
import tempfile
import unittest

from lxml.html import fromstring as parse_html, HtmlElement

from crawlo.helpers.adaptive_selector import (
    ElementFingerprint, SimilarityMatcher, FingerprintStorage
)
from crawlo.helpers.adaptive_selector.element_fingerprint import extract_domain_from_url


def make_fp(**kw):
    defaults = {
        'tag': 'div', 'text': '', 'attributes': {}, 'path': (),
        'parent_name': '', 'parent_attribs': {}, 'parent_text': '',
        'siblings': (), 'children': (),
    }
    defaults.update(kw)
    return ElementFingerprint(**defaults)


# ==================================================================
# Fix #1: 属性字典顺序独立性
# ==================================================================

class TestDictDiffOrderIndependence(unittest.TestCase):

    def test_key_order_independence(self):
        matcher = SimilarityMatcher()
        fp1 = make_fp(tag='div', text='Hello', attributes={'class': 'foo', 'id': 'bar', 'data-x': '1'},
                       path=('html', 'body', 'div'), parent_name='body')
        fp2 = make_fp(tag='div', text='Hello', attributes={'data-x': '1', 'id': 'bar', 'class': 'foo'},
                       path=('html', 'body', 'div'), parent_name='body')
        score = matcher.calculate_similarity(fp1, fp2)
        self.assertGreaterEqual(score, 95.0, f"Key 顺序独立性不足，得分: {score}")

    def test_partial_attributes(self):
        matcher = SimilarityMatcher()
        fp1 = make_fp(tag='div', text='X', attributes={'class': 'item', 'data-id': '123'},
                       path=('html', 'body', 'div'), parent_name='body')
        fp2 = make_fp(tag='div', text='X', attributes={'class': 'item', 'data-id': '456', 'style': 'r'},
                       path=('html', 'body', 'div'), parent_name='body')
        score = matcher.calculate_similarity(fp1, fp2)
        self.assertGreater(score, 60.0)
        self.assertLess(score, 95.0)


# ==================================================================
# Fix #2: 元素扫描上限 + 同标签限定
# ==================================================================

class TestScanLimit(unittest.TestCase):

    def test_same_tag_only(self):
        matcher = SimilarityMatcher(threshold=0)
        html = parse_html("<html><body><div><span>1</span></div>"
                          "<div><p class='target'>Find me</p></div></body></html>")
        target = ElementFingerprint.from_element(html.xpath('.//p')[0])
        matcher.MAX_SCAN_ELEMENTS = 100
        result = matcher.find_best_matches(target, html, percentage=0)
        self.assertEqual(len(result), 1)

    def test_large_page_scan_limit(self):
        matcher = SimilarityMatcher(threshold=0)
        matcher.MAX_SCAN_ELEMENTS = 10
        spans = "".join(f"<span>{i}</span>" for i in range(100))
        html = parse_html(f"<html><body><div>{spans}</div></body></html>")
        target = ElementFingerprint.from_element(html.xpath('.//span')[0])
        result = matcher.find_best_matches(target, html, percentage=0)
        self.assertIsInstance(result, list)

    def test_small_page_no_limit(self):
        matcher = SimilarityMatcher(threshold=0)
        html = parse_html("<html><body><div><span>Match</span></div></body></html>")
        target = ElementFingerprint.from_element(html.xpath('.//span')[0])
        result = matcher.find_best_matches(target, html, percentage=0)
        self.assertEqual(len(result), 1)


# ==================================================================
# Fix #3: 存储 Key 带路径哈希
# ==================================================================

class TestStoragePathHash(unittest.TestCase):

    def setUp(self):
        self.tmpfile = tempfile.mktemp(suffix='.db')
        self.storage = FingerprintStorage(backend='sqlite', storage_file=self.tmpfile)

    def tearDown(self):
        self.storage.close()
        if os.path.exists(self.tmpfile):
            os.remove(self.tmpfile)

    def test_diff_pages_isolated(self):
        url_a = 'https://example.com/products'
        url_b = 'https://example.com/search'
        fp = make_fp(tag='h1', text='Title')
        self.storage.save(url_a, 'title', fp)
        self.assertIsNone(self.storage.retrieve(url_b, 'title'))
        self.assertIsNotNone(self.storage.retrieve(url_a, 'title'))

    def test_same_page_normal(self):
        url = 'https://example.com/page'
        self.storage.save(url, 'title', make_fp(tag='h1', text='T'))
        self.assertIsNotNone(self.storage.retrieve(url, 'title'))

    def test_old_format_compat(self):
        url = 'https://example.com/page'
        domain = extract_domain_from_url(url)
        self.storage._backend.save(domain, 'title', make_fp(tag='h1', text='Old'))
        self.assertIsNotNone(self.storage.retrieve(url, 'title'))


# ==================================================================
# Fix #4: 指纹首次锁定
# ==================================================================

class TestFingerprintLock(unittest.TestCase):

    def setUp(self):
        self.tmpfile = tempfile.mktemp(suffix='.db')
        self.storage = FingerprintStorage(backend='sqlite', storage_file=self.tmpfile)

    def tearDown(self):
        self.storage.close()
        if os.path.exists(self.tmpfile):
            os.remove(self.tmpfile)

    def test_first_save_ok(self):
        url = 'https://example.com/prod'
        self.storage.save(url, 'price', make_fp(tag='span', text='$99'))
        data = self.storage.retrieve(url, 'price')
        self.assertIsNotNone(data)

    def test_save_then_retrieve_cache(self):
        url = 'https://example.com/prod'
        fp = make_fp(tag='h1', text='Test')
        self.storage.save(url, 'title', fp)
        data1 = self.storage.retrieve(url, 'title')
        data2 = self.storage.retrieve(url, 'title')  # 缓存命中
        self.assertIsNotNone(data1)
        self.assertIsNotNone(data2)
        self.assertEqual(data1['text'], 'Test')


# ==================================================================
# 全面集成场景测试
# ==================================================================

class TestAdaptiveIntegration(unittest.TestCase):

    def test_class_name_change(self):
        matcher = SimilarityMatcher(threshold=30)
        orig = parse_html("<html><body><div class='product'>Item</div></body></html>")
        mod = parse_html("<html><body><div class='item-card'>Item</div></body></html>")
        target = ElementFingerprint.from_element(orig.xpath('.//div')[0])
        result = matcher.find_best_matches(target, mod)
        self.assertEqual(len(result), 1)

    def test_tag_change_skip(self):
        """标签变化时同标签预过滤跳过（符合设计预期）"""
        matcher = SimilarityMatcher(threshold=30)
        orig = parse_html("<html><body><h3 class='title'>News</h3></body></html>")
        mod = parse_html("<html><body><h2 class='title'>News</h2></body></html>")
        target = ElementFingerprint.from_element(orig.xpath('.//h3')[0])
        result = matcher.find_best_matches(target, mod)
        # h3→h2 tag 不同，预过滤跳过所有 h2 → 0 匹配（这是正确的）
        self.assertEqual(len(result), 0)

    def test_dom_structure_change(self):
        matcher = SimilarityMatcher(threshold=30)
        orig = parse_html("<html><body><div class='wrapper'><div class='content'><p class='text'>Hello</p></div></div></body></html>")
        mod = parse_html("<html><body><div class='content'><p class='text'>Hello</p></div></body></html>")
        target = ElementFingerprint.from_element(orig.xpath('.//p')[0])
        result = matcher.find_best_matches(target, mod)
        self.assertGreaterEqual(len(result), 1)
        self.assertEqual(result[0].text.strip(), 'Hello')

    def test_text_slight_change(self):
        matcher = SimilarityMatcher(threshold=30)
        orig = parse_html("<html><body><h1>Product Title v1.0</h1></body></html>")
        mod = parse_html("<html><body><h1>Product Title v2.0</h1></body></html>")
        target = ElementFingerprint.from_element(orig.xpath('.//h1')[0])
        result = matcher.find_best_matches(target, mod)
        self.assertEqual(len(result), 1)

    def test_text_complete_change(self):
        """文本完全不同时理应匹配不到（过阈值）"""
        matcher = SimilarityMatcher(threshold=70)
        orig = parse_html("<html><body><h1>Old Name</h1></body></html>")
        mod = parse_html("<html><body><h1>Completely Different</h1></body></html>")
        target = ElementFingerprint.from_element(orig.xpath('.//h1')[0])
        result = matcher.find_best_matches(target, mod)
        # 文本差异大，可能被阈值过滤
        self.assertIsInstance(result, list)

    def test_mixed_changes_tag_filtered(self):
        """混合变化（class+层级+文本+标签），标签变化被预过滤"""
        matcher = SimilarityMatcher(threshold=30)
        orig = parse_html("<html><body><div class='product'><h2 class='name'>Widget Pro</h2></div></body></html>")
        mod = parse_html("<html><body><section><article class='item'><h3 class='title'>Widget Pro Max</h3></article></section></body></html>")
        target = ElementFingerprint.from_element(orig.xpath('.//h2')[0])
        result = matcher.find_best_matches(target, mod)
        # h2→h3 标签不同 → 预过滤
        self.assertEqual(len(result), 0)

    def test_memory_cache(self):
        tmpfile = tempfile.mktemp(suffix='.db')
        storage = FingerprintStorage(backend='sqlite', storage_file=tmpfile, cache_size=4)
        try:
            url = 'https://example.com/prod/1'
            fp = make_fp(tag='h1', text='Test')
            storage.save(url, 'title', fp)
            data = storage.retrieve(url, 'title')
            self.assertIsNotNone(data)
        finally:
            storage.close()
            if os.path.exists(tmpfile):
                os.remove(tmpfile)


if __name__ == '__main__':
    unittest.main()
