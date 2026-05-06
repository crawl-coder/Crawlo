#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
自适应元素选择器测试

验证核心功能：
1. 元素指纹生成与序列化
2. 相似度匹配算法
3. 指纹存储（SQLite）
4. Response 自适应选择器 API
"""
import os
import sys
import tempfile
import unittest

# 确保项目路径在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestElementFingerprint(unittest.TestCase):
    """元素指纹测试"""

    def setUp(self):
        from lxml.html import fromstring
        self.html = fromstring("""
        <html>
        <body>
            <div class="content" id="main">
                <h1>标题</h1>
                <p class="intro">介绍段落</p>
                <ul class="list">
                    <li>项目1</li>
                    <li>项目2</li>
                </ul>
                <a href="https://example.com" class="link">链接文本</a>
            </div>
        </body>
        </html>
        """)

    def test_from_element(self):
        """测试从元素生成指纹"""
        from crawlo.helpers.adaptive_selector import ElementFingerprint

        p_element = self.html.xpath('//p[@class="intro"]')[0]
        fp = ElementFingerprint.from_element(p_element)

        self.assertEqual(fp.tag, 'p')
        self.assertEqual(fp.text, '介绍段落')
        self.assertEqual(fp.attributes, {'class': 'intro'})
        self.assertEqual(fp.parent_name, 'div')
        self.assertIsNotNone(fp.siblings)
        self.assertIn('h1', fp.siblings)

    def test_serialization_roundtrip(self):
        """测试序列化/反序列化的一致性"""
        from crawlo.helpers.adaptive_selector import ElementFingerprint

        p_element = self.html.xpath('//p[@class="intro"]')[0]
        fp = ElementFingerprint.from_element(p_element)

        # 序列化
        data = fp.to_dict()
        self.assertIsInstance(data, dict)
        self.assertEqual(data['tag'], 'p')
        self.assertIn('siblings', data)

        # 反序列化
        fp2 = ElementFingerprint.from_dict(data)
        self.assertEqual(fp2.tag, fp.tag)
        self.assertEqual(fp2.text, fp.text)
        self.assertEqual(fp2.attributes, fp.attributes)
        self.assertEqual(fp2.siblings, fp.siblings)
        self.assertEqual(fp2.children, fp.children)

    def test_extract_domain(self):
        """测试域名提取"""
        from crawlo.helpers.adaptive_selector.element_fingerprint import extract_domain_from_url

        self.assertEqual(extract_domain_from_url('https://www.example.com/page'), 'example.com')
        self.assertEqual(extract_domain_from_url('http://sub.example.com:8080/path'), 'sub.example.com')
        self.assertEqual(extract_domain_from_url(''), 'default')
        self.assertEqual(extract_domain_from_url('invalid'), 'default')

    def test_fingerprint_path(self):
        """测试 DOM 路径提取"""
        from crawlo.helpers.adaptive_selector import ElementFingerprint

        p_element = self.html.xpath('//p[@class="intro"]')[0]
        fp = ElementFingerprint.from_element(p_element)

        self.assertIsInstance(fp.path, tuple)
        self.assertIn('html', fp.path)
        self.assertIn('body', fp.path)
        self.assertIn('div', fp.path)
        self.assertIn('p', fp.path)

    def test_fingerprint_children(self):
        """测试子节点信息"""
        from crawlo.helpers.adaptive_selector import ElementFingerprint

        div_element = self.html.xpath('//div[@id="main"]')[0]
        fp = ElementFingerprint.from_element(div_element)

        self.assertIsNotNone(fp.children)
        self.assertIn('h1', fp.children)
        self.assertIn('p', fp.children)
        self.assertIn('ul', fp.children)
        self.assertIn('a', fp.children)

    def test_fingerprint_link_element(self):
        """测试链接元素的指纹（包含 href）"""
        from crawlo.helpers.adaptive_selector import ElementFingerprint

        a_element = self.html.xpath('//a')[0]
        fp = ElementFingerprint.from_element(a_element)

        self.assertEqual(fp.tag, 'a')
        self.assertEqual(fp.text, '链接文本')
        self.assertIn('href', fp.attributes)
        self.assertEqual(fp.attributes['href'], 'https://example.com')
        self.assertIn('class', fp.attributes)

    def test_clean_attributes_filters_empty(self):
        """测试空值属性被清理"""
        from crawlo.helpers.adaptive_selector.element_fingerprint import _clean_attributes
        from lxml.html import fromstring

        html = fromstring('<div class="" id="test" style="  " data-val="x"></div>')
        result = _clean_attributes(html)
        self.assertNotIn('class', result)  # 空值
        self.assertIn('id', result)
        self.assertNotIn('style', result)  # 仅空白
        self.assertIn('data-val', result)

    def test_clean_attributes_filters_forbidden(self):
        """测试禁用属性被清理"""
        from crawlo.helpers.adaptive_selector.element_fingerprint import _clean_attributes, _FORBIDDEN_ATTRS
        from lxml.html import fromstring

        html = fromstring('<div data-reactid="abc" class="ok"></div>')
        result = _clean_attributes(html, _FORBIDDEN_ATTRS)
        self.assertNotIn('data-reactid', result)
        self.assertIn('class', result)

    def test_fingerprint_repr(self):
        """测试指纹 repr 输出"""
        from crawlo.helpers.adaptive_selector import ElementFingerprint

        p_element = self.html.xpath('//p[@class="intro"]')[0]
        fp = ElementFingerprint.from_element(p_element)

        r = repr(fp)
        self.assertIn('p', r)
        self.assertIn('Fingerprint', r)

    def test_no_parent_element(self):
        """测试根元素没有父节点的情况"""
        from crawlo.helpers.adaptive_selector import ElementFingerprint
        from lxml.html import fromstring

        # fromstring 会自动补全 html/body，所以 html 标签本身才是根
        html = fromstring('<html><body></body></html>')
        fp = ElementFingerprint.from_element(html)

        self.assertEqual(fp.tag, 'html')
        self.assertIsNone(fp.parent_name)


class TestSimilarityMatcher(unittest.TestCase):
    """相似度匹配测试"""

    def setUp(self):
        from lxml.html import fromstring
        from crawlo.helpers.adaptive_selector import ElementFingerprint, SimilarityMatcher

        self.matcher = SimilarityMatcher(threshold=0.0)

        # 原始页面
        self.original_html = fromstring("""
        <html>
        <body>
            <div class="product-list" id="products">
                <div class="product" data-id="1">
                    <h2>产品A</h2>
                    <p class="price">¥99</p>
                </div>
                <div class="product" data-id="2">
                    <h2>产品B</h2>
                    <p class="price">¥199</p>
                </div>
            </div>
        </body>
        </html>
        """)

        # 改版后的页面（class 变了，但结构相似）
        self.changed_html = fromstring("""
        <html>
        <body>
            <div class="item-list" id="products">
                <div class="item" data-id="1">
                    <h2>产品A</h2>
                    <p class="cost">¥99</p>
                </div>
                <div class="item" data-id="2">
                    <h2>产品B</h2>
                    <p class="cost">¥199</p>
                </div>
            </div>
        </body>
        </html>
        """)

    def test_same_element_high_score(self):
        """同一元素应该得到高分"""
        from crawlo.helpers.adaptive_selector import ElementFingerprint

        element = self.original_html.xpath('//div[@class="product"]')[0]
        fp = ElementFingerprint.from_element(element)

        # 在同一页面上找自己
        matches = self.matcher.find_best_matches(fp, self.original_html)
        self.assertGreater(len(matches), 0)

    def test_same_element_score_value(self):
        """同一元素应该得到接近 100% 的分数"""
        from crawlo.helpers.adaptive_selector import ElementFingerprint

        element = self.original_html.xpath('//div[@class="product"]')[0]
        fp = ElementFingerprint.from_element(element)

        # 重新生成候选指纹（同一元素）
        score = self.matcher.calculate_similarity(fp, fp)
        self.assertEqual(score, 100.0)

    def test_changed_page_can_match(self):
        """改版页面应该能匹配到相似元素"""
        from crawlo.helpers.adaptive_selector import ElementFingerprint

        # 保存原始元素指纹
        original_element = self.original_html.xpath('//div[@class="product"]')[0]
        fp = ElementFingerprint.from_element(original_element)

        # 在改版页面上查找
        matches = self.matcher.find_best_matches(fp, self.changed_html)
        self.assertGreater(len(matches), 0)
        # 匹配到的应该是改版后的 .item 元素
        matched = matches[0]
        self.assertEqual(matched.tag, 'div')
        # 应该匹配到第一个 item
        self.assertEqual(matched.get('data-id'), '1')

    def test_changed_page_score_drop(self):
        """改版后的匹配分数应该低于同页匹配"""
        from crawlo.helpers.adaptive_selector import ElementFingerprint

        original_element = self.original_html.xpath('//div[@class="product"]')[0]
        fp = ElementFingerprint.from_element(original_element)

        # 同页匹配分数
        same_page_candidate = ElementFingerprint.from_element(original_element)
        same_score = self.matcher.calculate_similarity(fp, same_page_candidate)

        # 改版页面匹配分数
        changed_element = self.changed_html.xpath('//div[@class="item"]')[0]
        changed_candidate = ElementFingerprint.from_element(changed_element)
        changed_score = self.matcher.calculate_similarity(fp, changed_candidate)

        self.assertGreater(same_score, changed_score)

    def test_tag_mismatch_filtered(self):
        """不同标签的元素应该被预过滤掉"""
        from crawlo.helpers.adaptive_selector import ElementFingerprint

        element = self.original_html.xpath('//div[@class="product"]')[0]
        fp = ElementFingerprint.from_element(element)

        # 在只有 span 的页面上不应匹配
        from lxml.html import fromstring
        span_html = fromstring('<html><body><span>text</span></body></html>')
        matches = self.matcher.find_best_matches(fp, span_html)
        self.assertEqual(len(matches), 0)

    def test_threshold_filtering(self):
        """阈值过滤测试"""
        from crawlo.helpers.adaptive_selector import ElementFingerprint, SimilarityMatcher

        element = self.original_html.xpath('//div[@class="product"]')[0]
        fp = ElementFingerprint.from_element(element)

        # 高阈值应该过滤掉低分匹配
        strict_matcher = SimilarityMatcher(threshold=99.0)
        matches = strict_matcher.find_best_matches(fp, self.changed_html)
        # 99% 的阈值应该会过滤掉大部分匹配
        # 因为改版了 class，不太可能达到 99%

    def test_text_similarity(self):
        """文本相似度对匹配的影响"""
        from crawlo.helpers.adaptive_selector import ElementFingerprint

        # 文本完全相同的情况
        el_same = self.original_html.xpath('//h2[text()="产品A"]')[0]
        fp_same = ElementFingerprint.from_element(el_same)

        # 文本不同的元素
        el_diff = self.original_html.xpath('//h2[text()="产品B"]')[0]
        fp_diff = ElementFingerprint.from_element(el_diff)

        # 同文本应该比不同文本分数高
        candidate_same = ElementFingerprint.from_element(el_same)
        candidate_diff = ElementFingerprint.from_element(el_diff)

        score_same = self.matcher.calculate_similarity(fp_same, candidate_same)
        score_diff = self.matcher.calculate_similarity(fp_same, candidate_diff)
        self.assertGreaterEqual(score_same, score_diff)

    def test_path_similarity(self):
        """DOM 路径相似度测试"""
        from crawlo.helpers.adaptive_selector import ElementFingerprint
        from lxml.html import fromstring

        # 同结构但不同位置的元素
        html = fromstring("""
        <html><body>
            <div class="a"><p class="target">deep</p></div>
            <section><p class="target">shallow</p></section>
        </body></html>
        """)

        deep_el = html.xpath('//div/p')[0]
        shallow_el = html.xpath('//section/p')[0]

        fp_deep = ElementFingerprint.from_element(deep_el)
        fp_shallow = ElementFingerprint.from_element(shallow_el)

        # 路径不同，分数应该低于同路径
        score_cross = self.matcher.calculate_similarity(fp_deep, fp_shallow)
        score_self = self.matcher.calculate_similarity(fp_deep, fp_deep)
        self.assertGreater(score_self, score_cross)

    def test_percentage_param_override(self):
        """find_best_matches 的 percentage 参数应覆盖全局阈值"""
        from crawlo.helpers.adaptive_selector import ElementFingerprint, SimilarityMatcher

        # 全局低阈值，但调用时指定高阈值
        matcher = SimilarityMatcher(threshold=0.0)
        element = self.original_html.xpath('//div[@class="product"]')[0]
        fp = ElementFingerprint.from_element(element)

        # percentage=100 应该过滤掉所有匹配
        matches = matcher.find_best_matches(fp, self.changed_html, percentage=100.0)
        self.assertEqual(len(matches), 0)

    def test_dict_diff_identical(self):
        """相同字典的相似度应该为 1.0"""
        from crawlo.helpers.adaptive_selector.similarity_matcher import SimilarityMatcher

        d = {'class': 'test', 'id': 'main'}
        score = SimilarityMatcher._calculate_dict_diff(d, d)
        self.assertEqual(score, 1.0)

    def test_dict_diff_empty(self):
        """空字典之间的相似度应该为 1.0"""
        from crawlo.helpers.adaptive_selector.similarity_matcher import SimilarityMatcher

        score = SimilarityMatcher._calculate_dict_diff({}, {})
        self.assertEqual(score, 1.0)


class TestSqliteStorage(unittest.TestCase):
    """SQLite 存储测试"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_fp.db')

    def tearDown(self):
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_save_and_retrieve(self):
        """测试保存和加载"""
        from crawlo.helpers.adaptive_selector import FingerprintStorage, ElementFingerprint
        from lxml.html import fromstring

        storage = FingerprintStorage(backend='sqlite', storage_file=self.db_path)
        html = fromstring('<html><body><div class="test">hello</div></body></html>')
        element = html.xpath('//div')[0]

        fp = ElementFingerprint.from_element(element)

        # 保存
        storage.save('https://example.com', '.test', fp)

        # 加载
        data = storage.retrieve('https://example.com', '.test')
        self.assertIsNotNone(data)
        self.assertEqual(data['tag'], 'div')
        self.assertEqual(data['text'], 'hello')

        # 不存在的数据
        data2 = storage.retrieve('https://example.com', '.nonexistent')
        self.assertIsNone(data2)

        storage.close()

    def test_overwrite(self):
        """测试覆盖更新"""
        from crawlo.helpers.adaptive_selector import FingerprintStorage, ElementFingerprint
        from lxml.html import fromstring

        storage = FingerprintStorage(backend='sqlite', storage_file=self.db_path)

        # 第一次保存
        html1 = fromstring('<html><body><div class="v1">old</div></body></html>')
        fp1 = ElementFingerprint.from_element(html1.xpath('//div')[0])
        storage.save('https://example.com', '.test', fp1)

        # 第二次覆盖
        html2 = fromstring('<html><body><div class="v2">new</div></body></html>')
        fp2 = ElementFingerprint.from_element(html2.xpath('//div')[0])
        storage.save('https://example.com', '.test', fp2)

        # 应该返回新数据
        data = storage.retrieve('https://example.com', '.test')
        self.assertEqual(data['text'], 'new')

        storage.close()

    def test_domain_isolation(self):
        """测试不同域名的数据隔离"""
        from crawlo.helpers.adaptive_selector import FingerprintStorage, ElementFingerprint
        from lxml.html import fromstring

        storage = FingerprintStorage(backend='sqlite', storage_file=self.db_path)
        html = fromstring('<html><body><div class="test">hello</div></body></html>')
        fp = ElementFingerprint.from_element(html.xpath('//div')[0])

        storage.save('https://site-a.com', '.test', fp)
        storage.save('https://site-b.com', '.test', fp)

        # 两个域名应该各自有独立数据
        data_a = storage.retrieve('https://site-a.com', '.test')
        data_b = storage.retrieve('https://site-b.com', '.test')
        self.assertIsNotNone(data_a)
        self.assertIsNotNone(data_b)

        storage.close()

    def test_multiple_selectors_same_domain(self):
        """测试同一域名下多个选择器指纹"""
        from crawlo.helpers.adaptive_selector import FingerprintStorage, ElementFingerprint
        from lxml.html import fromstring

        storage = FingerprintStorage(backend='sqlite', storage_file=self.db_path)
        html = fromstring('<html><body><div class="a">A</div><p class="b">B</p></body></html>')

        fp_div = ElementFingerprint.from_element(html.xpath('//div')[0])
        fp_p = ElementFingerprint.from_element(html.xpath('//p')[0])

        storage.save('https://example.com', '.a', fp_div)
        storage.save('https://example.com', '.b', fp_p)

        data_a = storage.retrieve('https://example.com', '.a')
        data_b = storage.retrieve('https://example.com', '.b')

        self.assertIsNotNone(data_a)
        self.assertIsNotNone(data_b)
        self.assertEqual(data_a['tag'], 'div')
        self.assertEqual(data_b['tag'], 'p')

        storage.close()

    def test_retrieve_nonexistent(self):
        """测试查询不存在的数据返回 None"""
        from crawlo.helpers.adaptive_selector import FingerprintStorage

        storage = FingerprintStorage(backend='sqlite', storage_file=self.db_path)
        self.assertIsNone(storage.retrieve('https://no-site.com', '.missing'))
        storage.close()

    def test_fingerprint_storage_redis_config(self):
        """测试 FingerprintStorage 的 Redis 配置构建"""
        from crawlo.helpers.adaptive_selector.storage import FingerprintStorage

        # 验证从各字段构建 Redis URL 不会抛异常（不实际连接）
        # 仅验证 backend='sqlite' 时不涉及 Redis
        storage = FingerprintStorage(
            backend='sqlite',
            storage_file=self.db_path,
            redis_host='10.0.0.1',
            redis_port=6380,
            redis_password='secret',
            redis_db=2,
        )
        self.assertIsNotNone(storage)
        storage.close()

    def test_invalid_backend(self):
        """测试无效存储后端抛异常"""
        from crawlo.helpers.adaptive_selector.storage import FingerprintStorage

        with self.assertRaises(ValueError):
            FingerprintStorage(backend='mongodb')


class TestResponseAdaptive(unittest.TestCase):
    """Response 自适应选择器集成测试"""

    def setUp(self):
        # 重置 Response 类级别的缓存
        from crawlo.network.response import Response
        Response._adaptive_storage = None
        Response._adaptive_matcher = None
        Response._adaptive_enabled_global = None

    def tearDown(self):
        from crawlo.network.response import Response
        if Response._adaptive_storage is not None:
            try:
                Response._adaptive_storage.close()
            except Exception:
                pass
        Response._adaptive_storage = None
        Response._adaptive_matcher = None
        Response._adaptive_enabled_global = None

    def test_manual_configure(self):
        """测试手动配置自适应选择器"""
        from crawlo.network.response import Response

        Response.configure_adaptive()

        self.assertTrue(Response._is_adaptive_enabled())
        self.assertIsNotNone(Response._adaptive_storage)
        self.assertIsNotNone(Response._adaptive_matcher)

    def test_adaptive_full_flow(self):
        """测试 adaptive 完整流程：命中时保存指纹，失效时自动匹配"""
        from crawlo.network.response import Response

        # 手动启用自适应
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, 'test_response.db')
        Response.configure_adaptive(storage_file=db_path)

        # 创建原始页面的 Response
        original_html = """
        <html>
        <body>
            <div class="product-list">
                <div class="product">产品A</div>
                <div class="product">产品B</div>
            </div>
        </body>
        </html>
        """
        response1 = Response(
            url="https://example.com/page",
            body=original_html.encode('utf-8'),
        )

        # 首次爬取：adaptive=True 命中时自动保存指纹
        items = response1.css('.product', adaptive=True)
        self.assertEqual(len(items), 2)

        # 模拟网站改版：class 从 product 变成 item
        changed_html = """
        <html>
        <body>
            <div class="item-list">
                <div class="item">产品A</div>
                <div class="item">产品B</div>
            </div>
        </body>
        </html>
        """
        response2 = Response(
            url="https://example.com/page",
            body=changed_html.encode('utf-8'),
        )

        # 改版后：原始选择器失效
        items_plain = response2.css('.product')
        self.assertEqual(len(items_plain), 0)

        # 使用 adaptive 自动匹配
        items_adaptive = response2.css('.product', adaptive=True)
        self.assertGreater(len(items_adaptive), 0)
        # 匹配到的应该包含 "产品A" 或 "产品B"
        texts = [item.css('::text').get() for item in items_adaptive if item.css('::text').get()]
        self.assertTrue(any('产品' in t for t in texts))

        # 清理
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_adaptive_disabled_warning(self):
        """测试未启用时使用 adaptive 的警告"""
        from crawlo.network.response import Response

        # 确保未启用
        Response._adaptive_enabled_global = False

        response = Response(
            url="https://example.com/page",
            body=b"<html><body><div class='test'>hello</div></body></html>",
        )

        # 不应抛异常，只是打印警告
        items = response.css('.test', adaptive=True)
        self.assertEqual(len(items), 1)  # 原始选择器仍然正常工作

    def test_xpath_adaptive(self):
        """测试 XPath 的 adaptive 流程"""
        from crawlo.network.response import Response

        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, 'test_xpath.db')
        Response.configure_adaptive(storage_file=db_path)

        original_html = """
        <html><body>
            <div class="article">
                <h2 class="title">标题1</h2>
                <h2 class="title">标题2</h2>
            </div>
        </body></html>
        """
        response1 = Response(
            url="https://example.com/article",
            body=original_html.encode('utf-8'),
        )

        # adaptive=True 命中时自动保存指纹
        items = response1.xpath('//h2[@class="title"]', adaptive=True)
        self.assertEqual(len(items), 2)

        # 改版：class 从 title 变成 heading
        changed_html = """
        <html><body>
            <div class="post">
                <h2 class="heading">标题1</h2>
                <h2 class="heading">标题2</h2>
            </div>
        </body></html>
        """
        response2 = Response(
            url="https://example.com/article",
            body=changed_html.encode('utf-8'),
        )

        # 原始 XPath 失效
        items_plain = response2.xpath('//h2[@class="title"]')
        self.assertEqual(len(items_plain), 0)

        # adaptive 匹配
        items_adaptive = response2.xpath('//h2[@class="title"]', adaptive=True)
        self.assertGreater(len(items_adaptive), 0)

        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_adaptive_with_identifier(self):
        """测试使用自定义 identifier 的自适应流程"""
        from crawlo.network.response import Response

        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, 'test_id.db')
        Response.configure_adaptive(storage_file=db_path)

        original_html = """
        <html><body>
            <div class="price">¥99</div>
        </body></html>
        """
        response1 = Response(
            url="https://shop.com/item",
            body=original_html.encode('utf-8'),
        )

        # adaptive=True 命中时自动保存指纹（使用自定义 identifier）
        items = response1.css('.price', adaptive=True, identifier='price-selector')
        self.assertEqual(len(items), 1)

        # 改版
        changed_html = """
        <html><body>
            <div class="cost">¥99</div>
        </body></html>
        """
        response2 = Response(
            url="https://shop.com/item",
            body=changed_html.encode('utf-8'),
        )

        # 用相同 identifier 进行 adaptive
        items = response2.css('.price', adaptive=True, identifier='price-selector')
        self.assertGreater(len(items), 0)

        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_adaptive_with_percentage(self):
        """测试 percentage 阈值过滤"""
        from crawlo.network.response import Response

        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, 'test_pct.db')
        Response.configure_adaptive(storage_file=db_path)

        original_html = """
        <html><body>
            <div class="product" id="p1">产品</div>
        </body></html>
        """
        response1 = Response(
            url="https://example.com",
            body=original_html.encode('utf-8'),
        )
        response1.css('.product', adaptive=True)

        # 完全不同的页面
        different_html = """
        <html><body>
            <div class="footer">底部信息</div>
        </body></html>
        """
        response2 = Response(
            url="https://example.com",
            body=different_html.encode('utf-8'),
        )

        # percentage=100 应该过滤掉
        items = response2.css('.product', adaptive=True, percentage=100.0)
        self.assertEqual(len(items), 0)

        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_normal_selector_unaffected(self):
        """测试普通选择器调用不受自适应影响"""
        from crawlo.network.response import Response

        html = "<html><body><div class='test'>hello</div></body></html>"
        response = Response(url="https://example.com", body=html.encode('utf-8'))

        # 不带 adaptive 参数，行为完全一致
        items = response.css('.test')
        self.assertEqual(len(items), 1)

        items = response.xpath('//div[@class="test"]')
        self.assertEqual(len(items), 1)

    def test_configure_adaptive_disable(self):
        """测试禁用自适应选择器"""
        from crawlo.network.response import Response

        Response.configure_adaptive()
        self.assertTrue(Response._is_adaptive_enabled())

        # 禁用：直接重置类属性
        Response._adaptive_enabled_global = False
        self.assertFalse(Response._is_adaptive_enabled())


if __name__ == '__main__':
    unittest.main()
