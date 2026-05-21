#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
EncodingDetector 完整单例测试
============================
覆盖所有核心路径（BOM、Header、Meta、内容检测、chardet 交叉验证、CJK 安全阀）
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from crawlo.utils.encoding_detector import (
    EncodingDetector, detect_encoding, decode_body,
    _read_bom, _http_content_type_encoding, _html_body_declared_encoding, _resolve_encoding,
)

# ==============================================================================
# 测试用样本数据
# ==============================================================================

ASCII_ONLY = b"<html><body>Hello World</body></html>"

UTF8_CLEAN = "UTF-8 only text Caf\u00e9 r\u00e9sum\u00e9".encode('utf-8')

UTF8_HTML = "<html><head><meta charset=\"utf-8\"/><title>\u4e2d\u6587\u6807\u9898</title></head><body>\u4e2d\u6587\u5185\u5bb9</body></html>".encode('utf-8')

GBK_HTML = "<html><head><meta charset=\"GBK\"/><title>\u4e2d\u6587\u6807\u9898</title></head><body>\u4e2d\u6587\u5185\u5bb9</body></html>".encode('gbk')

GB2312_HTML = "<html><head><meta charset=\"gb2312\"/><title>\u4e2d\u6587\u6807\u9898</title></head><body>\u4e2d\u6587\u5185\u5bb9</body></html>".encode('gb2312')

# 大量 ASCII 前缀（>200 chars）后再出现中文 → 测试 CJK 安全阀搜索范围
LARGE_PREFIX_GBK = ("<html>" + "<!-- " + "X" * 5000 + " --><meta charset=\"GBK\"/><title>\u4e2d\u6587\u6807\u9898</title></html>").encode('gbk')

SHIFT_JIS_HTML = "<html><head><meta charset=\"Shift_JIS\"/><title>\u65e5\u672c\u8a9e\u30bf\u30a4\u30c8\u30eb</title></head><body>\u65e5\u672c\u8a9e\u672c\u6587</body></html>".encode('shift_jis')

EUC_KR_HTML = "<html><head><meta charset=\"EUC-KR\"/><title>\ud55c\uae00\uc81c\ubaa9</title></head><body>\ud55c\uae00\ub0b4\uc6a9</body></html>".encode('euc-kr')

LATIN1_BODY = "Caf\u00e9 r\u00e9sum\u00e9".encode('latin-1')

BOM_UTF8 = b'\xef\xbb\xbf<html><body>Hello</body></html>'
BOM_UTF16_LE = b'\xff\xfe' + "Hello".encode('utf-16-le')
BOM_UTF16_BE = b'\xfe\xff' + "Hello".encode('utf-16-be')
BOM_UTF32_LE = b'\xff\xfe\x00\x00' + "Hello".encode('utf-32-le')
BOM_UTF32_BE = b'\x00\x00\xfe\xff' + "Hello".encode('utf-32-be')

# 4K 边界截断测试：body 4100 字节，确保 4096 处截断不影响解码
_GBK_PAD = "A" * 4090 + "\u4e2d\u6587\u6807\u9898"
GBK_4096_BOUNDARY = _GBK_PAD.encode('gbk')[:4100]

# 没有声明编码的纯中文 UTF-8 内容
UTF8_NO_META = "\u7eaf\u4e2d\u6587\u5185\u5bb9\u65e0\u9700\u58f0\u660e".encode('utf-8')

# 纯英文 HTML（无中文）
ENGLISH_HTML = b"<html><head><title>English Page</title></head><body><p>Hello World</p></body></html>"


def _make_html_meta(content: str) -> bytes:
    """Helper: wrap content in <html><head>...</head><body>...</body></html>"""
    return ("<html><head>" + content + "</head><body><p>test</p></body></html>").encode('utf-8')


class TestBOMDetection(unittest.TestCase):
    """BOM 检测 - _detect_bom"""

    def test_utf8_bom(self):
        self.assertEqual(EncodingDetector._detect_bom(BOM_UTF8), 'utf-8')

    def test_utf16_le_bom(self):
        self.assertEqual(EncodingDetector._detect_bom(BOM_UTF16_LE), 'utf-16-le')

    def test_utf16_be_bom(self):
        self.assertEqual(EncodingDetector._detect_bom(BOM_UTF16_BE), 'utf-16-be')

    def test_utf32_le_bom(self):
        self.assertEqual(EncodingDetector._detect_bom(BOM_UTF32_LE), 'utf-32-le')

    def test_utf32_be_bom(self):
        self.assertEqual(EncodingDetector._detect_bom(BOM_UTF32_BE), 'utf-32-be')

    def test_no_bom(self):
        self.assertIsNone(EncodingDetector._detect_bom(ASCII_ONLY))

    def test_empty_body(self):
        self.assertIsNone(EncodingDetector._detect_bom(b''))


class TestHeaderDetection(unittest.TestCase):
    """Content-Type 头部检测 - _detect_from_headers"""

    def test_content_type_lowercase(self):
        headers = {'content-type': 'text/html; charset=gbk'}
        # w3lib 的 http_content_type_encoding 返回 'gbk', 但后续流转走 resolve → gb18030
        result = EncodingDetector._detect_from_headers(headers)
        self.assertIn(result, ('gbk', 'gb18030'))

    def test_content_type_titlecase(self):
        headers = {'Content-Type': 'text/html; charset=utf-8'}
        self.assertEqual(EncodingDetector._detect_from_headers(headers), 'utf-8')

    def test_content_type_iso8859(self):
        """iso-8859-1 可能被 w3lib 映射为 cp1252"""
        headers = {'content-type': b'text/html; charset=iso-8859-1'}
        result = EncodingDetector._detect_from_headers(headers)
        self.assertIn(result, ('iso-8859-1', 'cp1252'))

    def test_no_charset(self):
        self.assertIsNone(EncodingDetector._detect_from_headers({'content-type': 'text/html'}))

    def test_no_headers(self):
        self.assertIsNone(EncodingDetector._detect_from_headers({}))

    def test_uppercase_charset(self):
        headers = {'Content-Type': 'text/html; CHARSET=UTF-8'}
        self.assertEqual(EncodingDetector._detect_from_headers(headers), 'utf-8')


class TestMetaDetection(unittest.TestCase):
    """HTML Meta / XML 声明检测 - _detect_from_html_meta"""

    def test_html5_charset(self):
        body = _make_html_meta('<meta charset="utf-8">')
        self.assertEqual(EncodingDetector._detect_from_html_meta(body), 'utf-8')

    def test_html5_charset_gbk(self):
        body = _make_html_meta('<meta charset="GBK">')
        # resolve_encoding 将 gbk → gb18030 (w3lib DEFAULT_ENCODING_TRANSLATION)
        self.assertEqual(EncodingDetector._detect_from_html_meta(body), 'gb18030')

    def test_html4_http_equiv(self):
        body = b'<html><head><meta http-equiv="Content-Type" content="text/html; charset=GBK"></head><body></body></html>'
        # resolve_encoding('gbk') → gb18030
        self.assertEqual(EncodingDetector._detect_from_html_meta(body), 'gb18030')

    def test_xml_declaration(self):
        body = b'<?xml version="1.0" encoding="UTF-8"?><html><body>Hello</body></html>'
        self.assertEqual(EncodingDetector._detect_from_html_meta(body), 'utf-8')

    def test_no_meta(self):
        self.assertIsNone(EncodingDetector._detect_from_html_meta(ASCII_ONLY))

    def test_empty_body(self):
        self.assertIsNone(EncodingDetector._detect_from_html_meta(b''))


class TestHasCJKChars(unittest.TestCase):
    """CJK 字符检测 - _has_cjk_chars"""

    def test_chinese(self):
        self.assertTrue(EncodingDetector._has_cjk_chars("\u4f60\u597d\u4e16\u754c"))

    def test_japanese(self):
        self.assertTrue(EncodingDetector._has_cjk_chars("\u65e5\u672c\u8a9e"))

    def test_korean(self):
        self.assertTrue(EncodingDetector._has_cjk_chars("\ud55c\uae00"))

    def test_no_cjk(self):
        self.assertFalse(EncodingDetector._has_cjk_chars("Hello World! 123"))

    def test_empty(self):
        self.assertFalse(EncodingDetector._has_cjk_chars(""))

    def test_mixed(self):
        self.assertTrue(EncodingDetector._has_cjk_chars("Hello \u4f60\u597d World"))


class TestContentDetection(unittest.TestCase):
    """内容检测 - _detect_from_content（核心路径）"""

    def test_utf8_plain(self):
        """纯 UTF-8 文本"""
        self.assertEqual(EncodingDetector._detect_from_content(UTF8_CLEAN), 'utf-8')

    def test_utf8_html(self):
        """UTF-8 HTML 含中文"""
        self.assertEqual(EncodingDetector._detect_from_content(UTF8_HTML), 'utf-8')

    def test_utf8_no_meta(self):
        """UTF-8 纯中文无声明"""
        self.assertEqual(EncodingDetector._detect_from_content(UTF8_NO_META), 'utf-8')

    def test_gbk_returns_gb18030(self):
        """GBK 内容 → 应返回 gb18030 (chardet + CJK 安全阀)"""
        self.assertEqual(EncodingDetector._detect_from_content(GBK_HTML), 'gb18030')

    def test_gb2312_returns_gb18030(self):
        """GB2312 内容 → 应返回 gb18030"""
        self.assertEqual(EncodingDetector._detect_from_content(GB2312_HTML), 'gb18030')

    def test_large_prefix_gbk(self):
        """前部大量 ASCII 标签后再出现中文 → 安全阀应能检测"""
        result = EncodingDetector._detect_from_content(LARGE_PREFIX_GBK)
        # 可能 gbk (东亚覆盖先命中) 或 gb18030 (chardet+安全阀)
        self.assertIn(result, ('gbk', 'gb18030'))

    def test_shift_jis(self):
        """Shift-JIS 日文内容"""
        result = EncodingDetector._detect_from_content(SHIFT_JIS_HTML)
        # CJK 安全阀可能将中/日/韩都归为 gb18030（CJK 统一汉字区重叠），
        # 也可能返回 cp932/shift_jis
        self.assertIn(result, ('shift_jis', 'cp932', 'gb18030', 'utf-8'))

    def test_euc_kr(self):
        """EUC-KR 韩文内容"""
        result = EncodingDetector._detect_from_content(EUC_KR_HTML)
        # CJK 安全阀可能将中/日/韩都归为 gb18030
        self.assertIn(result, ('euc_kr', 'cp949', 'gb18030', 'utf-8'))

    def test_ascii_only(self):
        """纯 ASCII → UTF-8 解码成功"""
        self.assertEqual(EncodingDetector._detect_from_content(ASCII_ONLY), 'utf-8')

    def test_latin1(self):
        """Latin-1 文本（无 CJK）→ chardet 检测到 latin-1"""
        result = EncodingDetector._detect_from_content(LATIN1_BODY)
        self.assertIn(result, ('latin-1', 'utf-8'))

    def test_empty_body(self):
        """空 body → utf-8（b''.decode('utf-8') 成功）"""
        self.assertEqual(EncodingDetector._detect_from_content(b''), 'utf-8')

    def test_english_html(self):
        """纯英文 HTML → utf-8"""
        self.assertEqual(EncodingDetector._detect_from_content(ENGLISH_HTML), 'utf-8')


class TestAutoDetectCallback(unittest.TestCase):
    """w3lib 回调 - _auto_detect_callback"""

    def test_ascii(self):
        text = b"<html><body>Hello</body></html>"
        result = EncodingDetector._auto_detect_callback(text)
        # w3lib resolve_encoding 可能映射 ascii → cp1252
        self.assertIn(result, ('ascii', 'cp1252'))

    def test_utf8(self):
        text = "\u4e2d\u6587\u5185\u5bb9".encode('utf-8')
        result = EncodingDetector._auto_detect_callback(text)
        self.assertEqual(result, 'utf-8')

    def test_gbk_cjk_safety_valve(self):
        """GBK 内容 → chardet 可能返回 cp1252 → CJK 安全阀纠正为 gb18030"""
        self.assertEqual(EncodingDetector._auto_detect_callback(GBK_HTML), 'gb18030')

    def test_latin1_no_cjk(self):
        """Latin-1 无 CJK → 应返回 latin-1 相关编码"""
        result = EncodingDetector._auto_detect_callback(LATIN1_BODY)
        self.assertIn(result, ('latin-1', 'cp1252', 'utf-8'))


class TestDecodeBody(unittest.TestCase):
    """解码 - decode_body"""

    def test_with_encoding(self):
        """指定正确编码解码"""
        result = EncodingDetector.decode_body(GBK_HTML, encoding='gb18030')
        self.assertIn('\u4e2d\u6587', result)
        self.assertNotIn('\ufffd', result)

    def test_without_encoding_auto(self):
        """不指定编码，自动检测后解码"""
        result = EncodingDetector.decode_body(GBK_HTML)
        self.assertIn('\u4e2d\u6587', result)

    def test_wrong_encoding(self):
        """错误编码使用 replace 模式，不会崩溃"""
        result = EncodingDetector.decode_body(GBK_HTML, encoding='ascii')
        self.assertIsInstance(result, str)

    def test_invalid_encoding_name(self):
        """无效编码名 → 回退到 utf-8 replace"""
        result = EncodingDetector.decode_body(b'Hello', encoding='nonexistent-enc')
        self.assertIsInstance(result, str)

    def test_empty_body(self):
        self.assertEqual(EncodingDetector.decode_body(b''), "")

    def test_large_prefix_decode(self):
        """大量前缀场景解码正确"""
        result = EncodingDetector.decode_body(LARGE_PREFIX_GBK)
        self.assertIn('\u4e2d\u6587', result)

    def test_utf8_decode(self):
        result = EncodingDetector.decode_body(UTF8_HTML)
        self.assertIn('\u4e2d\u6587', result)

    def test_shift_jis_decode(self):
        result = EncodingDetector.decode_body(SHIFT_JIS_HTML)
        self.assertIn('\u65e5\u672c\u8a9e', result)

    def test_euc_kr_decode(self):
        result = EncodingDetector.decode_body(EUC_KR_HTML)
        self.assertIn('\ud55c\uae00', result)

    def test_english_decode(self):
        result = EncodingDetector.decode_body(ENGLISH_HTML)
        self.assertIn('English', result)

    def test_gbk_with_detect(self):
        """decode_body 不传 encoding，走 detect 路径"""
        result = EncodingDetector.decode_body(GBK_HTML)
        self.assertIn('\u4e2d\u6587', result)

    def test_chinese_decode_clean(self):
        """中文解码后不应含替换字符"""
        result = EncodingDetector.decode_body(GBK_HTML)
        self.assertNotIn('\ufffd', result)


class TestDetectMethod(unittest.TestCase):
    """detect() 主入口"""

    def test_declared_encoding_priority(self):
        """显式声明的编码优先级最高"""
        self.assertEqual(
            EncodingDetector.detect(GBK_HTML, declared_encoding='utf-8'),
            'utf-8'
        )

    def test_w3lib_path_gbk(self):
        """w3lib 可用时，GBK 页面检测到 gb18030"""
        result = EncodingDetector.detect(GBK_HTML, headers={'Content-Type': 'text/html'})
        self.assertEqual(result, 'gb18030')

    def test_w3lib_path_utf8(self):
        """UTF-8 页面检测到 utf-8"""
        result = EncodingDetector.detect(UTF8_HTML, headers={'Content-Type': 'text/html'})
        self.assertEqual(result, 'utf-8')

    def test_fallback_path(self):
        """use_w3lib=False 走内置 fallback"""
        result = EncodingDetector.detect(GBK_HTML, use_w3lib=False)
        self.assertEqual(result, 'gb18030')

    def test_empty_body(self):
        """空 body → w3lib 默认编码"""
        result = EncodingDetector.detect(b'')
        self.assertIsInstance(result, str)

    def test_utf8_detect(self):
        self.assertEqual(EncodingDetector.detect(UTF8_HTML), 'utf-8')

    def test_gbk_via_meta(self):
        """含 GBK meta 标签→w3lib 应检测到"""
        self.assertEqual(EncodingDetector.detect(GBK_HTML), 'gb18030')

    def test_with_bom(self):
        """BOM 优先于 meta"""
        self.assertEqual(EncodingDetector.detect(BOM_UTF8), 'utf-8')


class TestDetectWithW3lib(unittest.TestCase):
    """_detect_with_w3lib 路径"""

    def test_bom_w3lib(self):
        self.assertEqual(EncodingDetector._detect_with_w3lib(BOM_UTF8), 'utf-8')

    def test_meta_gbk(self):
        result = EncodingDetector._detect_with_w3lib(GBK_HTML, {'Content-Type': 'text/html'})
        self.assertEqual(result, 'gb18030')

    def test_content_type_header(self):
        result = EncodingDetector._detect_with_w3lib(
            b"<html></html>",
            {'Content-Type': 'text/html; charset=iso-8859-1'}
        )
        # w3lib 映射 iso-8859-1 → cp1252
        self.assertIn(result, ('iso-8859-1', 'cp1252'))

    def test_content_type_lowercase(self):
        result = EncodingDetector._detect_with_w3lib(
            b"<html></html>",
            {'content-type': 'text/html; charset=gbk'}
        )
        # w3lib 映射 gbk → gb18030
        self.assertEqual(result, 'gb18030')

    def test_empty_body(self):
        """空 body → w3lib 默认编码"""
        result = EncodingDetector._detect_with_w3lib(b'', {})
        self.assertIsInstance(result, str)

    def test_gbk_meta_english_content(self):
        """meta 声明 GBK 但内容纯英文 → 信任 meta 返回 gb18030"""
        body = b"<html><head><meta charset=\"GBK\"/></head><body>English Only Text</body></html>"
        result = EncodingDetector._detect_with_w3lib(body)
        # w3lib 从 meta 得到 gbk→gb18030, _has_cjk_chars 检查发现无 CJK → fallback
        # fallback 的 meta 检测仍返回 gb18030
        self.assertEqual(result, 'gb18030')


class TestDetectFallback(unittest.TestCase):
    """内置 fallback - _detect_fallback"""

    def test_bom(self):
        self.assertEqual(EncodingDetector._detect_fallback(BOM_UTF8), 'utf-8')

    def test_header(self):
        result = EncodingDetector._detect_fallback(
            b"<html></html>",
            {'content-type': 'text/html; charset=iso-8859-1'}
        )
        self.assertIn(result, ('iso-8859-1', 'cp1252'))

    def test_meta_fallback(self):
        body = b'<html><head><meta charset="GBK"/></head><body>Hello</body></html>'
        result = EncodingDetector._detect_fallback(body)
        # w3lib resolve_encoding('gbk') → gb18030
        self.assertIn(result, ('gbk', 'gb18030', 'utf-8'))

    def test_no_info(self):
        self.assertEqual(EncodingDetector._detect_fallback(b'', {}), 'utf-8')

    def test_gbk_content(self):
        self.assertEqual(EncodingDetector._detect_fallback(GBK_HTML), 'gb18030')

    def test_utf8_content(self):
        self.assertEqual(EncodingDetector._detect_fallback(UTF8_HTML), 'utf-8')


class TestEdgeCases(unittest.TestCase):
    """边界场景"""

    def test_4k_boundary_gbk_decode(self):
        """body[:4096] 正好截断 GBK 字符尾部 → decode 正确"""
        result = EncodingDetector.decode_body(GBK_4096_BOUNDARY)
        self.assertIsInstance(result, str)

    def test_large_body_no_cjk(self):
        """大量内容但无 CJK → UTF-8/chardet 检测"""
        large_body = b"<html>" + b"<p>Hello World</p>" * 200 + b"</html>"
        result = EncodingDetector.detect(large_body)
        self.assertIsInstance(result, str)

    def test_mixed_cjk_latin(self):
        """混合中文和英文"""
        body = "Hello \u4f60\u597d World \u4e16\u754c".encode('utf-8')
        self.assertEqual(EncodingDetector._detect_from_content(body), 'utf-8')

    def test_body_with_only_high_bytes_no_cjk(self):
        """只有高字节但非 CJK（如拉丁补遗）→ 不应崩溃"""
        body = bytes(range(0x80, 0x100))
        result = EncodingDetector._detect_from_content(body)
        self.assertIsNotNone(result)

    def test_very_short_body(self):
        """极短的 body"""
        for b in [b'a', b'\xd6\xd0', b'\xc4\xe3\xba\xc3']:
            result = EncodingDetector.detect(b)
            self.assertIsInstance(result, str)

    def test_body_with_no_valid_encoding(self):
        """随机二进制 → 不应崩溃"""
        import random
        random.seed(42)
        body = bytes(random.randint(0, 255) for _ in range(100))
        result = EncodingDetector._detect_from_content(body)
        # 应返回某种编码或 None
        self.assertIsNotNone(result)

    def test_4096_exact_boundary(self):
        """body 恰好 4096 字节"""
        body = b"X" * 4096
        self.assertIsInstance(EncodingDetector.detect(body), str)

    def test_chinese_content_with_english_doctype(self):
        """模拟 OFWeek 页面：较长的英文 DOCTYPE + 中文标题 → GB18030"""
        body = ("<!DOCTYPE html PUBLIC \"-//W3C//DTD XHTML 1.0 Transitional//EN\" "
                "\"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd\">\n"
                "<html><head><meta charset=\"GBK\"/><title>\u4e2d\u6587\u6807\u9898</title></head>"
                "<body>\u4e2d\u6587\u5185\u5bb9</body></html>").encode('gbk')
        result = EncodingDetector.detect(body)
        self.assertEqual(result, 'gb18030')
        decoded = EncodingDetector.decode_body(body)
        self.assertIn('\u4e2d\u6587', decoded)

    def test_shift_jis_not_gb18030(self):
        """日文内容通过 detect() 不应被误判为 gb18030（detect 走 w3lib 路径，可区分）"""
        result = EncodingDetector.detect(SHIFT_JIS_HTML)
        # detect() 走 w3lib，能正确检测到 shift_jis/cp932
        self.assertIn(result, ('shift_jis', 'cp932', 'utf-8'))

    def test_euc_kr_not_gb18030(self):
        """韩文内容通过 detect() 不应被误判为 gb18030"""
        result = EncodingDetector.detect(EUC_KR_HTML)
        self.assertIn(result, ('euc_kr', 'cp949', 'utf-8'))

    def test_gbk_repeated_decode(self):
        """多次解码相同 GBK 内容结果一致"""
        r1 = EncodingDetector.decode_body(GBK_HTML)
        r2 = EncodingDetector.decode_body(GBK_HTML)
        self.assertEqual(r1, r2)

    def test_decode_roundtrip_gbk(self):
        """编解码往返：UTF8 str → GBK bytes → decode 可逆"""
        original = "\u4e2d\u6587\u6807\u9898"
        encoded = original.encode('gbk')
        decoded = EncodingDetector.decode_body(encoded)
        self.assertEqual(decoded, original)


class TestModuleFunctions(unittest.TestCase):
    """模块级便捷函数"""

    def test_detect_encoding(self):
        self.assertEqual(detect_encoding(GBK_HTML), 'gb18030')

    def test_detect_encoding_declared(self):
        self.assertEqual(detect_encoding(GBK_HTML, declared_encoding='utf-8'), 'utf-8')

    def test_detect_encoding_utf8(self):
        self.assertEqual(detect_encoding(UTF8_HTML), 'utf-8')

    def test_decode_body_module(self):
        result = decode_body(GBK_HTML)
        self.assertIn('\u4e2d\u6587', result)

    def test_decode_body_with_encoding(self):
        result = decode_body(GBK_HTML, encoding='gb18030')
        self.assertIn('\u4e2d\u6587', result)

    def test_decode_body_empty(self):
        self.assertEqual(decode_body(b''), "")


class TestFallbackFunctions(unittest.TestCase):
    """内置 fallback 函数（w3lib 不可用时独立使用）"""

    def test_read_bom_utf8(self):
        result, bom_len = _read_bom(b'\xef\xbb\xbfhello')
        self.assertEqual(result, 'utf-8')
        self.assertEqual(bom_len, 3)

    def test_read_bom_utf16le(self):
        result, bom_len = _read_bom(b'\xff\xfe\x00\x41')  # utf-16-le, U+4100
        self.assertEqual(result, 'utf-16-le')
        self.assertEqual(bom_len, 2)

    def test_read_bom_utf16be(self):
        result, bom_len = _read_bom(b'\xfe\xff\x00\x41')
        self.assertEqual(result, 'utf-16-be')
        self.assertEqual(bom_len, 2)

    def test_read_bom_none(self):
        result, bom_len = _read_bom(b'hello')
        self.assertIsNone(result)
        self.assertEqual(bom_len, 0)

    def test_http_content_type_encoding(self):
        self.assertEqual(_http_content_type_encoding('text/html; charset=gbk'), 'gbk')

    def test_http_content_type_encoding_no_charset(self):
        self.assertIsNone(_http_content_type_encoding('text/html'))

    def test_http_content_type_encoding_empty(self):
        self.assertIsNone(_http_content_type_encoding(''))

    def test_html_body_declared_encoding_html5(self):
        body = b'<html><head><meta charset="utf-8"></head></html>'
        self.assertEqual(_html_body_declared_encoding(body), 'utf-8')

    def test_html_body_declared_encoding_html4(self):
        body = b'<html><head><meta http-equiv="Content-Type" content="text/html; charset=gbk"></head></html>'
        self.assertEqual(_html_body_declared_encoding(body), 'gbk')

    def test_html_body_declared_encoding_xml(self):
        body = b'<?xml version="1.0" encoding="UTF-8"?><root></root>'
        self.assertEqual(_html_body_declared_encoding(body), 'utf-8')

    def test_html_body_declared_encoding_none(self):
        self.assertIsNone(_html_body_declared_encoding(b'<html></html>'))

    def test_html_body_declared_encoding_empty(self):
        self.assertIsNone(_html_body_declared_encoding(b''))

    def test_resolve_encoding_utf8(self):
        self.assertEqual(_resolve_encoding('utf8'), 'utf-8')

    def test_resolve_encoding_utf16(self):
        self.assertEqual(_resolve_encoding('utf16'), 'utf-16')

    def test_resolve_encoding_latin1(self):
        self.assertEqual(_resolve_encoding('latin1'), 'latin-1')

    def test_resolve_encoding_iso8859(self):
        self.assertEqual(_resolve_encoding('iso-8859-1'), 'latin-1')

    def test_resolve_encoding_windows1252(self):
        self.assertEqual(_resolve_encoding('windows-1252'), 'cp1252')

    def test_resolve_encoding_gbk(self):
        self.assertEqual(_resolve_encoding('GBK'), 'gbk')

    def test_resolve_encoding_gb18030(self):
        self.assertEqual(_resolve_encoding('gb18030'), 'gb18030')

    def test_resolve_encoding_shift_jis(self):
        self.assertEqual(_resolve_encoding('shift-jis'), 'shift_jis')

    def test_resolve_encoding_euc_jp(self):
        self.assertEqual(_resolve_encoding('euc-jp'), 'euc_jp')

    def test_resolve_encoding_euc_kr(self):
        self.assertEqual(_resolve_encoding('euc-kr'), 'euc_kr')

    def test_resolve_encoding_none(self):
        self.assertEqual(_resolve_encoding(''), 'utf-8')

    def test_resolve_encoding_unknown(self):
        self.assertEqual(_resolve_encoding('unknown-enc'), 'unknown-enc')


class TestDeclaredEncoding(unittest.TestCase):
    """declared_encoding 优先级"""

    def test_declared_takes_priority(self):
        """declared_encoding 应屏蔽 body/header 检测"""
        result = EncodingDetector.detect(
            GBK_HTML,
            headers={'Content-Type': 'text/html; charset=utf-8'},
            declared_encoding='ascii'
        )
        self.assertEqual(result, 'ascii')

    def test_declared_utf8(self):
        self.assertEqual(
            EncodingDetector.detect(GBK_HTML, declared_encoding='utf-8'),
            'utf-8'
        )

    def test_declared_gbk(self):
        self.assertEqual(
            EncodingDetector.detect(UTF8_HTML, declared_encoding='gbk'),
            'gbk'
        )


class TestResponseIntegration(unittest.TestCase):
    """与 Response 协同的集成测试"""

    def test_response_text_gbk(self):
        """GBK body → Response.text 正确解码"""
        from crawlo.network.response import Response
        resp = Response(url='https://ee.ofweek.com/test.html', body=GBK_HTML)
        self.assertIn('\u4e2d\u6587', resp.text)

    def test_response_text_utf8(self):
        from crawlo.network.response import Response
        resp = Response(url='https://example.com', body=UTF8_HTML)
        self.assertIn('\u4e2d\u6587', resp.text)
        self.assertEqual(resp.encoding, 'utf-8')

    def test_response_with_request_encoding(self):
        """Request 指定编码 → Response.encoding 应使用该编码"""
        from crawlo.network.response import Response

        class MockRequest:
            encoding = 'gbk'

        resp = Response(
            url='https://example.com',
            body=b"<html>Hello</html>",
            request=MockRequest(),
        )
        self.assertEqual(resp.encoding, 'gbk')

    def test_response_encode_body_with_gbk(self):
        from crawlo.network.response import Response
        resp = Response(url='https://example.com', body=GBK_HTML)
        self.assertIn('\u4e2d\u6587', resp.text)
        self.assertEqual(resp.encoding, 'gb18030')

    def test_response_text_cached(self):
        from crawlo.network.response import Response
        resp = Response(url='https://example.com', body=UTF8_HTML)
        t1 = resp.text
        t2 = resp.text
        self.assertEqual(t1, t2)

    def test_response_empty(self):
        from crawlo.network.response import Response
        resp = Response(url='https://example.com', body=b'')
        self.assertEqual(resp.text, "")

    def test_response_xpath_gbk(self):
        """GBK 页面 XPath 查询正常"""
        from crawlo.network.response import Response
        body = "<html><body><div class=\"content\">中文内容</div></body></html>".encode('utf-8')
        resp = Response(url='https://example.com', body=body)
        result = resp.xpath('//div[@class="content"]/text()').get()
        self.assertEqual(result, '中文内容')


if __name__ == '__main__':
    unittest.main(verbosity=2)
