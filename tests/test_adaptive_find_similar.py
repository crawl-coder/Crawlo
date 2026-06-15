#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
find_similar + ignore_attributes 功能测试
"""
import os
import tempfile
import unittest

from lxml.html import fromstring as parse_html

from crawlo.helpers.adaptive_selector import (
    ElementFingerprint, SimilarityMatcher, FingerprintStorage
)


class TestIgnoreAttributes(unittest.TestCase):
    """P1: ignore_attributes — 比较时跳过易变属性"""

    def test_ignore_href_increases_score(self):
        """忽略 href 后，不同 URL 的元素得分应提升"""
        fp1 = ElementFingerprint(
            tag='a', text='Read more',
            attributes={'href': '/article/123', 'class': 'link'},
            path=('html', 'body', 'a'), parent_name='body',
            parent_attribs={}, parent_text='', siblings=(), children=(),
        )
        fp2 = ElementFingerprint(
            tag='a', text='Read more',
            attributes={'href': '/article/999', 'class': 'link'},
            path=('html', 'body', 'a'), parent_name='body',
            parent_attribs={}, parent_text='', siblings=(), children=(),
        )

        matcher_default = SimilarityMatcher()
        score_default = matcher_default.calculate_similarity(fp1, fp2)

        matcher_ignore = SimilarityMatcher(ignore_attributes={'href'})
        score_ignore = matcher_ignore.calculate_similarity(fp1, fp2)

        # 跳过 href 的得分应更高（不受 URL 差异影响）
        self.assertGreater(score_ignore, score_default,
            f"忽略 href: {score_ignore} vs 默认: {score_default}")

    def test_ignore_multiple_attributes(self):
        """忽略多个属性（href + src）"""
        fp1 = ElementFingerprint(
            tag='img', text='',
            attributes={'src': '/img/1.jpg', 'href': '/link/1', 'class': 'thumb', 'alt': 'Photo'},
            path=('html', 'body', 'img'), parent_name='body',
            parent_attribs={}, parent_text='', siblings=(), children=(),
        )
        fp2 = ElementFingerprint(
            tag='img', text='',
            attributes={'src': '/img/999.jpg', 'href': '/link/999', 'class': 'thumb', 'alt': 'Photo'},
            path=('html', 'body', 'img'), parent_name='body',
            parent_attribs={}, parent_text='', siblings=(), children=(),
        )

        matcher = SimilarityMatcher(ignore_attributes={'href', 'src'})
        score = matcher.calculate_similarity(fp1, fp2)
        # class + alt 相同，应接近满分
        self.assertGreaterEqual(score, 80.0, f"忽略 href+src 得分: {score}")

    def test_ignore_attributes_no_effect_on_empty(self):
        """无被忽略属性时不影响结果"""
        fp = ElementFingerprint(
            tag='div', text='Test', attributes={'class': 'x'},
            path=('html', 'body', 'div'), parent_name='body',
            parent_attribs={}, parent_text='', siblings=(), children=(),
        )
        matcher1 = SimilarityMatcher()
        matcher2 = SimilarityMatcher(ignore_attributes={'href', 'src'})
        s1 = matcher1.calculate_similarity(fp, fp)
        s2 = matcher2.calculate_similarity(fp, fp)
        self.assertEqual(s1, s2)


class TestFindSimilar(unittest.TestCase):
    """P0: find_similar_elements — 相邻结构元素查找"""

    def test_product_list_similar_elements(self):
        """商品列表：找到第一个后自动定位其余"""
        html = parse_html("""
        <html><body>
            <div class="products">
                <div class="product"><h3 class="name">Item 1</h3><span class="price">$10</span></div>
                <div class="product"><h3 class="name">Item 2</h3><span class="price">$20</span></div>
                <div class="product"><h3 class="name">Item 3</h3><span class="price">$30</span></div>
            </div>
        </body></html>
        """)
        # 定位第一个商品
        target = html.xpath('//div[@class="product"]')[0]
        target_fp = ElementFingerprint.from_element(target)

        matcher = SimilarityMatcher(threshold=30)
        results = matcher.find_similar_elements(target_fp, html, threshold=30)

        # 应找到 2 个相似商品（Item 2, Item 3）
        self.assertEqual(len(results), 2)
        for r in results:
            self.assertEqual(r.tag, 'div')
            self.assertIn('product', r.attrib.get('class', ''))

    def test_single_item_no_similar(self):
        """只有一个商品时返回空"""
        html = parse_html("""
        <html><body>
            <div class="products">
                <div class="product"><h3>Only Item</h3></div>
            </div>
        </body></html>
        """)
        target = html.xpath('//div[@class="product"]')[0]
        target_fp = ElementFingerprint.from_element(target)

        matcher = SimilarityMatcher(threshold=30)
        results = matcher.find_similar_elements(target_fp, html, threshold=30)
        self.assertEqual(len(results), 0)

    def test_dissimilar_siblings_filtered(self):
        """不相关的同级元素被阈值过滤"""
        html = parse_html("""
        <html><body>
            <div class="products">
                <div class="product"><h3>Item 1</h3><span class="price">$10</span></div>
                <div class="ad"><h3>Advertisement</h3></div>
                <div class="product"><h3>Item 2</h3><span class="price">$20</span></div>
            </div>
        </body></html>
        """)
        target = html.xpath('//div[@class="product"]')[0]
        target_fp = ElementFingerprint.from_element(target)

        matcher = SimilarityMatcher(threshold=70)  # 高阈值过滤掉 ad
        results = matcher.find_similar_elements(target_fp, html, threshold=70)

        # 第二个 product 被匹配，ad 因 class/text 差异低于阈值被过滤
        self.assertGreaterEqual(len(results), 1)
        # 所有结果都应有 class='product'
        for r in results:
            self.assertIn('product', r.attrib.get('class', ''))

    def test_find_similar_with_storage(self):
        """通过 FingerprintStorage 保存后调用 find_similar_elements"""
        tmpfile = tempfile.mktemp(suffix='.db')
        storage = FingerprintStorage(backend='sqlite', storage_file=tmpfile)
        try:
            html = parse_html("""
            <html><body><div class="list">
                <a class="link" href="/1">Link 1</a>
                <a class="link" href="/2">Link 2</a>
                <a class="link" href="/3">Link 3</a>
            </div></body></html>
            """)
            target = html.xpath('//a[@class="link"]')[0]
            fp = ElementFingerprint.from_element(target)
            storage.save('https://example.com', 'mylink', fp)

            data = storage.retrieve('https://example.com', 'mylink')
            self.assertIsNotNone(data)

            target_fp = ElementFingerprint.from_dict(data)
            matcher = SimilarityMatcher(threshold=30, ignore_attributes={'href'})
            results = matcher.find_similar_elements(target_fp, html, threshold=30)

            # 应找到另外 2 个链接
            self.assertGreaterEqual(len(results), 2)
        finally:
            storage.close()
            if os.path.exists(tmpfile):
                os.remove(tmpfile)

    def test_find_similar_deep_nesting(self):
        """深层嵌套元素"""
        html = parse_html("""
        <html><body>
            <div class="container"><div class="list"><ul>
                <li class="item"><span>Alpha</span></li>
                <li class="item"><span>Beta</span></li>
                <li class="item"><span>Gamma</span></li>
            </ul></div></div>
        </body></html>
        """)
        target = html.xpath('//li[@class="item"]')[0]
        target_fp = ElementFingerprint.from_element(target)

        matcher = SimilarityMatcher(threshold=40)
        results = matcher.find_similar_elements(target_fp, html, threshold=40)

        self.assertEqual(len(results), 2)


if __name__ == '__main__':
    unittest.main()
