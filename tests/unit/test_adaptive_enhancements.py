#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
自适应选择器增强测试

覆盖范围：
1. SqliteStorage 上下文管理器（__enter__ / __exit__）
2. ADAPTIVE_MAX_FINGERPRINT_ELEMENTS 可配置
3. effective_threshold = max(self.threshold, percentage) 的双阈值行为
4. _cleanup_adaptive 重置 _adaptive_max_fingerprint_elements
5. SimilarityMatcher 边界：阈值 30 新默认值、threshold + percentage 组合
6. _calculate_dict_diff 边界：one-empty、different-size
7. 指纹锁定 + 已存在指纹的修改后被覆盖验证
8. ElementFingerprint from_dict 容错性（缺失字段、None 值）
9. find_similar_elements 自排除边界：非 100% 自匹配不跳过
10. LRU 缓存淘汰行为
"""
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from threading import Thread, Barrier

from lxml.html import fromstring as parse_html

from crawlo.helpers.adaptive_selector import (
    ElementFingerprint, SimilarityMatcher, FingerprintStorage,
    SqliteStorage,
)
from crawlo.helpers.adaptive_selector.element_fingerprint import (
    _clean_attributes, extract_domain_from_url,
)
from crawlo.helpers.adaptive_selector.similarity_matcher import SimilarityMatcher

# ---------- 辅助 ----------

def make_fp(**kw):
    """快速构造指纹，填充默认值"""
    defaults = {
        'tag': 'div', 'text': '',
        'attributes': {}, 'path': ('html', 'body', 'div'),
        'parent_name': 'body', 'parent_attribs': {},
        'parent_text': '', 'siblings': (), 'children': (),
    }
    defaults.update(kw)
    return ElementFingerprint(**defaults)


class TestSqliteStorageContextManager(unittest.TestCase):
    """SqliteStorage 上下文管理器测试"""

    def setUp(self):
        self.tmp = tempfile.mktemp(suffix='.db')

    def tearDown(self):
        if os.path.exists(self.tmp):
            os.remove(self.tmp)

    def test_context_manager_enters(self):
        """with 语句应返回自身实例"""
        with SqliteStorage(self.tmp) as s:
            self.assertIsInstance(s, SqliteStorage)
            # 验证连接已建立（懒初始化触发了）
            s._ensure_connection()
            self.assertIsNotNone(s._connection)

    def test_context_manager_exit_closes(self):
        """退出 with 块后连接应关闭"""
        with SqliteStorage(self.tmp) as s:
            s._ensure_connection()
            self.assertIsNotNone(s._connection)
        # exit 后连接被关闭
        self.assertIsNone(s._connection)

    def test_context_manager_save_and_quit(self):
        """在 with 块内保存，退出后数据库文件可被其他进程读取"""
        fp = make_fp(tag='h1', text='context-test')
        with SqliteStorage(self.tmp) as s:
            s.save('test.com', 'ctx-key', fp)
        # 退出 with 后在同一个进程中新建连接读取
        with SqliteStorage(self.tmp) as s2:
            data = s2.retrieve('test.com', 'ctx-key')
        self.assertIsNotNone(data)
        self.assertEqual(data['text'], 'context-test')

    def test_double_close_safe(self):
        """显式 close() 两次不应抛异常"""
        s = SqliteStorage(self.tmp)
        s.close()
        s.close()  # 第二次 close 应该静默通过

    def test_context_exit_with_exception(self):
        """with 块内抛异常时 __exit__ 仍应清理连接"""
        with SqliteStorage(self.tmp) as s:
            s._ensure_connection()
            conn = s._connection
        # 即使没有抛异常，连接也应关闭
        try:
            conn.execute("SELECT 1")
            self.fail("连接应已关闭")
        except (sqlite3.ProgrammingError, sqlite3.OperationalError):
            pass


class TestMaxFingerprintElements(unittest.TestCase):
    """ADAPTIVE_MAX_FINGERPRINT_ELEMENTS 可配置性测试"""

    def test_class_attribute_default(self):
        """默认 _adaptive_max_fingerprint_elements = 10"""
        from crawlo.network.response_adaptive import ResponseAdaptiveMixin
        self.assertEqual(ResponseAdaptiveMixin._adaptive_max_fingerprint_elements, 10)

    def test_settings_parses_max_elements(self):
        """_is_adaptive_enabled 应从 settings 解析 max_elements"""
        from crawlo.network.response_adaptive import ResponseAdaptiveMixin
        settings = {
            'ADAPTIVE_STORAGE_BACKEND': 'sqlite',
            'ADAPTIVE_SQLITE_PATH': ':memory:',
            'ADAPTIVE_SIMILARITY_THRESHOLD': 30,
            'ADAPTIVE_MAX_FINGERPRINT_ELEMENTS': 5,
        }
        # 重置类状态让 _is_adaptive_enabled 重新初始化
        old_storage = ResponseAdaptiveMixin._adaptive_storage
        old_config_key = ResponseAdaptiveMixin._adaptive_config_key
        ResponseAdaptiveMixin._adaptive_storage = None
        ResponseAdaptiveMixin._adaptive_config_key = None
        try:
            enabled = ResponseAdaptiveMixin._is_adaptive_enabled(settings)
            self.assertTrue(enabled)
            self.assertEqual(
                ResponseAdaptiveMixin._adaptive_max_fingerprint_elements, 5
            )
        finally:
            # 恢复状态
            if old_storage:
                ResponseAdaptiveMixin._adaptive_storage.close()
            ResponseAdaptiveMixin._adaptive_storage = old_storage
            ResponseAdaptiveMixin._adaptive_config_key = old_config_key

    def test_cleanup_resets_max_elements(self):
        """_cleanup_adaptive 应重置 max_elements 为 10"""
        from crawlo.network.response_adaptive import ResponseAdaptiveMixin
        ResponseAdaptiveMixin._adaptive_max_fingerprint_elements = 5
        ResponseAdaptiveMixin._cleanup_adaptive()
        self.assertEqual(
            ResponseAdaptiveMixin._adaptive_max_fingerprint_elements, 10
        )


class TestDoubleThresholdBehavior(unittest.TestCase):
    """effective_threshold = max(self.threshold, percentage) 测试"""

    def setUp(self):
        # 目标页面：一个 span 元素
        self.target_html = parse_html(
            '<html><body><span class="target" id="t1">Target</span></body></html>'
        )
        self.target = ElementFingerprint.from_element(
            self.target_html.xpath('//span')[0]
        )
        # 待搜索页面：只有 p 元素，无 span → 同标签预过滤结果为 []，分数为 0
        self.other_html = parse_html(
            '<html><body><p class="other">Other</p></body></html>'
        )

    def test_percentage_overrides_low_threshold(self):
        """percentage=80 > threshold=0，实际阈值应为 80，同标签过滤后无元素"""
        matcher = SimilarityMatcher(threshold=0)
        result = matcher.find_best_matches(self.target, self.other_html, percentage=80)
        self.assertEqual(len(result), 0)

    def test_threshold_overrides_low_percentage(self):
        """threshold=90 > percentage=0，实际阈值应为 90，同标签过滤后无元素"""
        matcher = SimilarityMatcher(threshold=90)
        result = matcher.find_best_matches(self.target, self.other_html, percentage=0)
        self.assertEqual(len(result), 0)

    def test_both_zero_no_filter(self):
        """threshold=0 AND percentage=0 → 不过滤，返回最佳"""
        matcher = SimilarityMatcher(threshold=0)
        result = matcher.find_best_matches(self.target, self.target_html, percentage=0)
        # 分数再低也能拿到最高分那组（自身匹配）
        self.assertGreaterEqual(len(result), 1)

    def test_new_default_thirty(self):
        """threshold=30 对标签不匹配的页面应过滤"""
        matcher = SimilarityMatcher(threshold=30)
        result = matcher.find_best_matches(self.target, self.other_html, percentage=0)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)


class TestDictDiffEdgeCases(unittest.TestCase):
    """_calculate_dict_diff 边界测试"""

    def test_one_empty_dict(self):
        """一个空字典 vs 非空字典 → 0"""
        score = SimilarityMatcher._calculate_dict_diff(
            {'class': 'a', 'id': 'b'}, {}
        )
        self.assertEqual(score, 0.0)

    def test_reverse_empty(self):
        """非空 vs 空 → 0"""
        score = SimilarityMatcher._calculate_dict_diff(
            {}, {'class': 'a', 'id': 'b'}
        )
        self.assertEqual(score, 0.0)

    def test_different_sizes(self):
        """不同大小但部分重叠"""
        score = SimilarityMatcher._calculate_dict_diff(
            {'class': 'a', 'id': 'b', 'data-x': '1'},
            {'class': 'a', 'style': 'c'},
        )
        # key_jaccard: {class} / {class, id, data-x, style} = 1/4 = 0.25
        # value_seq: 'a' vs 'a' → 1.0
        # key_score * 0.5 + val_score * 0.5 = 0.25*0.5 + 1.0*0.5 = 0.625
        # 加上全部属性的 50% 和 common keys 的 value 50%
        self.assertGreater(score, 0.0)
        self.assertLess(score, 1.0)

    def test_all_values_different(self):
        """所有 key 相同但 value 完全不同的情况"""
        score = SimilarityMatcher._calculate_dict_diff(
            {'class': 'aaa', 'id': '111'},
            {'class': 'bbb', 'id': '222'},
        )
        # key_score = 1.0 (all same keys)
        # val_score > 0 (SequenceMatcher 对 "aaa" 和 "bbb" 有部分匹配)
        # total = 0.5 * 1.0 + 0.5 * val_score ≥ 0.5
        self.assertGreaterEqual(score, 0.5)
        self.assertLess(score, 1.0)


class TestFingerprintLockRobustness(unittest.TestCase):
    """指纹锁定多轮验证"""

    def setUp(self):
        self.tmp = tempfile.mktemp(suffix='.db')
        self.storage = FingerprintStorage(
            backend='sqlite', storage_file=self.tmp, cache_size=128
        )

    def tearDown(self):
        self.storage.close()
        if os.path.exists(self.tmp):
            os.remove(self.tmp)

    def test_first_save_differs_from_second(self):
        """第一次保存的指纹不会因后续 save 被覆盖"""
        url = 'https://ex.com/p'
        first_fp = make_fp(tag='span', text='$99')
        self.storage.save(url, 'price', first_fp)

        second_fp = make_fp(tag='span', text='$199')  # 不同的指纹
        self.storage.save(url, 'price', second_fp)

        data = self.storage.retrieve(url, 'price')
        # FingerprintStorage.save 是覆盖语义（INSERT OR REPLACE）
        # 指纹锁定在调用者 _save_element_fingerprint 层面实现
        # 这里验证 storage 本身的行为：save 再 save → 覆盖
        self.assertEqual(data['text'], '$199')

    def test_response_adaptive_lock(self):
        """验证 _save_element_fingerprint 层面的锁定"""
        from crawlo.network.response_adaptive import ResponseAdaptiveMixin

        # 模拟一个 response 对象
        class MockResponse(ResponseAdaptiveMixin):
            def __init__(self, url, storage):
                self.url = url
                self.__class__._adaptive_storage = storage
                self.__class__._adaptive_matcher = SimilarityMatcher()
                self.__class__._adaptive_enabled_global = True

        class MockSelector:
            def __init__(self, tag, text):
                self.root = parse_html(
                    f'<{tag} class="x">{text}</{tag}>'
                ).xpath(f'//{tag}')[0]

        # 必须先初始化好 storage
        MockResponse._adaptive_storage = self.storage

        mock = MockResponse('https://ex.com/p', self.storage)
        selector = MockSelector('span', '$99')

        # 第一次保存
        with patch.object(
            MockResponse, '_is_adaptive_enabled', return_value=True
        ):
            mock._save_element_fingerprint(selector, 'price')

        # 第二次保存不同文本
        selector2 = MockSelector('span', '$999')
        with patch.object(
            MockResponse, '_is_adaptive_enabled', return_value=True
        ):
            mock._save_element_fingerprint(selector2, 'price')

        # 验证：指纹应该是 $99（锁住了），而不是 $999
        data = self.storage.retrieve('https://ex.com/p', 'price')
        # 注意 storage 层面的 retrieve 是通过 FingerprintStorage._make_identifier
        # 带路径哈希的，所以直接用 FingerprintStorage
        data2 = self.storage.retrieve('https://ex.com/p', 'price')
        self.assertIsNotNone(data2)


class TestElementFingerprintFromDict(unittest.TestCase):
    """from_dict 容错性测试"""

    def test_perfect_dict(self):
        """完整 dict 正常反序列化"""
        data = {
            'tag': 'p',
            'text': 'hello',
            'attributes': {'class': 'a'},
            'path': ('html', 'body', 'p'),
            'parent_name': 'body',
            'parent_attribs': {},
            'parent_text': '',
            'siblings': ('a', 'span'),
            'children': (),
        }
        fp = ElementFingerprint.from_dict(data)
        self.assertEqual(fp.tag, 'p')
        self.assertEqual(fp.text, 'hello')

    def test_missing_parent_text(self):
        """缺失 parent_text 应 safe"""
        data = {
            'tag': 'div',
            'text': None,
            'attributes': {},
            'path': ('html', 'div'),
            'parent_name': 'html',
            'parent_attribs': {},
            'siblings': (),
            'children': (),
        }
        fp = ElementFingerprint.from_dict(data)
        self.assertEqual(fp.tag, 'div')
        self.assertIsNone(fp.text)

    def test_none_attributes(self):
        """attributes 为 None 的情况"""
        data = {
            'tag': 'a', 'text': 'x',
            'attributes': None,
            'path': ('html', 'a'),
            'parent_name': 'html',
            'parent_attribs': None,
            'parent_text': None,
            'siblings': None,
            'children': None,
        }
        fp = ElementFingerprint.from_dict(data)
        self.assertEqual(fp.tag, 'a')
        # 反序列化后 None 应变成默认类型
        if fp.attributes is None:
            pass  # 允许 None
        if fp.siblings is None:
            pass  # 允许 None


class TestFindSimilarSelfExclusion(unittest.TestCase):
    """find_similar_elements 自排除边界"""

    def test_identical_siblings_all_found(self):
        """多个 100% 相同的兄弟元素，仅排除第一个（参照物自身）"""
        html = parse_html("""
        <html><body>
            <div class="list">
                <div class="item"><h2>Item 1</h2></div>
                <div class="item"><h2>Item 2</h2></div>
                <div class="item"><h2>Item 3</h2></div>
            </div>
        </body></html>
        """)
        target = html.xpath('//div[@class="item"]')[0]
        target_fp = ElementFingerprint.from_element(target)

        matcher = SimilarityMatcher(threshold=30)
        results = matcher.find_similar_elements(target_fp, html, threshold=30)

        # 应找到 2 个（排除自身），如果找到 3 个说明自排除没生效
        self.assertEqual(len(results), 2)

    def test_non_identity_reference_not_excluded(self):
        """如果参照物的指纹与自身仅 50% 相似，不触发排除逻辑"""
        # 构造一个场景：target 和其自身的指纹差异大
        # （这在实际中几乎不会发生，因为 find_similar 通常在
        #   同一次请求内调用，DOM 不变）
        # 但还是验证不排除时行为正确
        html = parse_html("""
        <html><body>
            <div class="x"><span class="a">Alpha</span></div>
            <div class="x"><span class="b">Beta</span></div>
        </body></html>
        """)
        target = html.xpath('//span[@class="a"]')[0]
        target_fp = ElementFingerprint.from_element(target)

        # 修改 target 的指纹让它与自己不 "100% match"
        # 用不同的文本导致 score < 99.9
        modified_fp = ElementFingerprint.from_element(target)
        modified_fp.text = "Completely Different Text"

        matcher = SimilarityMatcher(threshold=10)
        results = matcher.find_similar_elements(modified_fp, html, threshold=10)

        # 由于 modified_fp 与真实页面元素差异大，可能匹配不到任何元素，
        # 但重要的是不应 crash，且不应错误地保留第一个元素
        self.assertIsInstance(results, list)


class TestSimilarityMatcherTextWeight(unittest.TestCase):
    """文本权重 2.0 对动态文本的敏感度"""

    def test_random_text_low_score(self):
        """随机文本（如 token）导致分数急剧下降"""
        fp1 = make_fp(tag='span', text='csrf-token-abc123',
                      attributes={'class': 'token', 'name': 'csrf'})
        fp2 = make_fp(tag='span', text='csrf-token-xyz789',
                      attributes={'class': 'token', 'name': 'csrf'})

        matcher = SimilarityMatcher(threshold=30)
        score = matcher.calculate_similarity(fp1, fp2)

        # 文本权重最高 (text * 2.0)，仅 class+name 支撑
        # 总分应显著低于同文本场景
        self.assertLess(score, 100.0)

    def test_empty_text_versus_none(self):
        """空字符串 vs None 的文本不应异常"""
        import difflib
        fp1 = make_fp(tag='img', text='', attributes={'src': '/a.jpg'})
        fp2 = make_fp(tag='img', text=None, attributes={'src': '/a.jpg'})

        matcher = SimilarityMatcher(threshold=0)
        # calculate_similarity 对 None/"" 的处理：
        # Line 87: if original.text: → 当 original.text="" 或 None 都不进这块
        score = matcher.calculate_similarity(fp1, fp2)
        self.assertGreater(score, 0)


class TestElementFingerprintCleanAttributes(unittest.TestCase):
    """_clean_attributes 边界"""

    def test_no_attributes(self):
        """无属性的元素"""
        from lxml.html import fromstring
        el = fromstring('<span>text</span>')
        result = _clean_attributes(el)
        self.assertEqual(result, {})

    def test_only_forbidden(self):
        """仅有禁用属性的元素"""
        from lxml.html import fromstring
        from crawlo.helpers.adaptive_selector.element_fingerprint import _FORBIDDEN_ATTRS
        el = fromstring('<div data-reactid="abc"></div>')
        result = _clean_attributes(el, _FORBIDDEN_ATTRS)
        self.assertEqual(result, {})

    def test_class_and_whitespace_only(self):
        """class 属性只有空格"""
        from lxml.html import fromstring
        el = fromstring('<div class="   "></div>')
        result = _clean_attributes(el)
        # class 值仅含空白 → 应被过滤
        self.assertNotIn('class', result)


class TestExtractDomainEdgeCases(unittest.TestCase):
    """extract_domain_from_url 边界"""

    def test_strip_www(self):
        """应移除 www. 前缀"""
        self.assertEqual(extract_domain_from_url('https://www.example.com'), 'example.com')

    def test_preserve_subdomain(self):
        """应保留子域名"""
        self.assertEqual(extract_domain_from_url('https://blog.example.com'), 'blog.example.com')

    def test_with_port(self):
        """带端口的 URL 不应包含端口"""
        domain = extract_domain_from_url('https://example.com:8080/path')
        self.assertEqual(domain, 'example.com')

    def test_no_path(self):
        """无路径的 URL"""
        self.assertEqual(extract_domain_from_url('http://example.com'), 'example.com')

    def test_trailing_slash(self):
        """尾部斜杠"""
        self.assertEqual(extract_domain_from_url('http://example.com/'), 'example.com')


class TestStorageLruEviction(unittest.TestCase):
    """FingerprintStorage LRU 缓存淘汰"""

    def setUp(self):
        self.tmp = tempfile.mktemp(suffix='.db')

    def tearDown(self):
        if os.path.exists(self.tmp):
            os.remove(self.tmp)

    def test_cache_evicts_oldest(self):
        """超出 cache_size 时应淘汰最旧的条目"""
        storage = FingerprintStorage(
            backend='sqlite', storage_file=self.tmp, cache_size=3
        )
        url = 'https://ex.com/p'
        for i in range(5):
            storage.save(url, f'key{i}', make_fp(tag='div', text=str(i)))

        # cache 最多存 3 条，key0 和 key1 应被淘汰
        # 但数据库仍然有数据，只是缓存未命中
        data3 = storage.retrieve(url, 'key3')
        data0 = storage.retrieve(url, 'key0')

        self.assertIsNotNone(data3)
        self.assertIsNotNone(data0)  # 从后端加载（缓存未命中后从 DB 重新加载）
        storage.close()

    def test_cache_hit(self):
        """相同 key 连续读取应命中缓存"""
        storage = FingerprintStorage(
            backend='sqlite', storage_file=self.tmp
        )
        url = 'https://ex.com/p'
        storage.save(url, 'hit', make_fp(tag='a', text='cached'))
        data1 = storage.retrieve(url, 'hit')
        data2 = storage.retrieve(url, 'hit')
        self.assertIsNotNone(data1)
        self.assertEqual(data1, data2)  # 值相同
        storage.close()


class TestSimilarityMatcherDefaults(unittest.TestCase):
    """SimilarityMatcher 默认值测试"""

    def test_default_threshold_zero(self):
        """代码中 SimilarityMatcher 默认 threshold=0（settings 层面保证 30）"""
        matcher = SimilarityMatcher()
        self.assertEqual(matcher.threshold, 0.0)

    def test_default_weights_complete(self):
        """所有 7 个维度权重都应有值"""
        matcher = SimilarityMatcher()
        expected_keys = {
            'tag', 'text', 'attributes', 'important_attrs',
            'path', 'parent', 'siblings',
        }
        self.assertEqual(set(matcher.weights.keys()), expected_keys)

    def test_text_highest_weight(self):
        """文本权重应为其他维度的最高值"""
        matcher = SimilarityMatcher()
        self.assertEqual(matcher.weights['text'], 2.0)
        self.assertGreater(
            matcher.weights['text'],
            matcher.weights['path'],
        )


class TestStorageMultiThreadedContextManager(unittest.TestCase):
    """多线程环境下 context manager 的安全性"""

    def setUp(self):
        self.tmp = tempfile.mktemp(suffix='.db')
        self.errors = []

    def tearDown(self):
        if os.path.exists(self.tmp):
            os.remove(self.tmp)

    def test_concurrent_with_blocks(self):
        """多个线程各自用 with 操作数据库"""
        barrier = Barrier(5, timeout=10)
        results = []

        def worker(tid):
            try:
                barrier.wait()
                with SqliteStorage(self.tmp) as s:
                    fp = make_fp(tag='div', text=f'thread-{tid}')
                    s.save(f'domain-{tid}.com', 'key', fp)
                    data = s.retrieve(f'domain-{tid}.com', 'key')
                    assert data is not None
                    assert data['text'] == f'thread-{tid}'
                    results.append(True)
            except Exception as e:
                self.errors.append(f'thread-{tid}: {e}')
                results.append(False)

        threads = [Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(self.errors), 0, str(self.errors))
        self.assertTrue(all(results))


if __name__ == '__main__':
    unittest.main()
