#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo EncodingDetector vs Scrapy 编码检测对比测试
==================================================
对比两种框架对同一内容的编码检测结果和质量。

关键发现：
- 对于有正常 meta 标签的页面：Crawlo = Scrapy（都基于 w3lib）
- 对于无 meta 无 header 的纯内容：Crawlo 胜出（chardet + CJK 安全阀 + 多编码轮询）
- 对于错误 meta 声明：两者都信任 meta，都产生乱码（待改进）
- 对于 4096 边界截断：Crawlo 能检测 gbk，Scrapy 回退到 utf-8
- 对于 Latin-1 西欧页面：Crawlo 正确检测，Scrapy 回退到 utf-8
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import re
from w3lib.encoding import html_to_unicode
from crawlo.utils.encoding_detector import EncodingDetector

# ==============================================================================
# 测试样本（模拟 OFWeek 类 GBK 页面 + 多种语言）
# ==============================================================================

# 典型 OFWeek GBK 页面（英文 DOCTYPE + GBK meta + 中文内容）
OFWEEK_LIKE = (
    '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" '
    '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n'
    '<html xmlns="http://www.w3.org/1999/xhtml">\n'
    '<head>\n'
    '<meta http-equiv="Content-Type" content="text/html; charset=GBK" />\n'
    '<title>AMD，谁是成长最快企业？</title>\n'
    '</head>\n'
    '<body>\n'
    '<div class="time fl">2026-05-11 10:00</div>\n'
    '<div class="source-name">数说商业</div>\n'
    '<div class="TRS_Editor">\n'
    '<p>半导体产业纵横：近年来，中国半导体产业发展迅猛。</p>\n'
    '<p>功率半导体市场持续增长，国产替代加速推进。</p>\n'
    '</div>\n'
    '</body>\n'
    '</html>'
).encode('gbk')

# 大量 ASCII 前缀的 GBK 页面（模拟之前前 200 字符无中文的 bug）
LARGE_PREFIX_GBK = (
    '<!DOCTYPE html>\n<html>\n<head>\n'
    '<!-- ' + 'X' * 4000 + ' -->\n'
    '<meta charset="GBK" />\n'
    '<title>中文标题在很后面</title>\n'
    '</head>\n<body>\n中文内容\n</body>\n</html>'
).encode('gbk')

# UTF-8 中文
UTF8_CHINESE = (
    '<html><head><meta charset="utf-8"/>'
    '<title>中文测试页面</title></head>'
    '<body><p>这是一个测试页面</p></body></html>'
).encode('utf-8')

# Shift-JIS 日文
SHIFT_JIS_PAGE = (
    '<html><head><meta charset="Shift_JIS"/>'
    '<title>日本語テストページ</title></head>'
    '<body><p>これはテストページです</p></body></html>'
).encode('shift_jis')

# EUC-KR 韩文
EUC_KR_PAGE = (
    '<html><head><meta charset="EUC-KR"/>'
    '<title>한글테스트페이지</title></head>'
    '<body><p>이것은테스트페이지입니다</p></body></html>'
).encode('euc-kr')

# 虚假声明：meta 说 UTF-8 但实际是 GBK
FALSE_META_UTF8_GBK = (
    '<html><head><meta charset="utf-8"/>'
    '<title>实际是GBK编码但声明为UTF-8</title></head>'
    '<body><p>中文内容</p></body></html>'
).encode('gbk')

# 虚假声明：meta 说 GBK 但实际是 UTF-8
FALSE_META_GBK_UTF8 = (
    '<html><head><meta charset="GBK"/>'
    '<title>实际是UTF-8编码但声明为GBK</title></body></html>'
).encode('utf-8')


def _count_mojibake(text: str, sample: int = 2000) -> int:
    """统计 Latin-1 补遗字符（U+0080-U+00FF），这是 GBK 被误判为 Latin-1 的特征"""
    matches = re.findall(r'[\x80-\xff]', text[:sample])
    return len(matches)


class TestCrawloVsScrapy(unittest.TestCase):
    """Crawlo EncodingDetector vs Scrapy 的 w3lib 基础检测对比"""

    def test_ofweek_gbk_encoding(self):
        """GBK 中文页面编码检测"""
        scrapy_enc, _ = html_to_unicode('text/html', OFWEEK_LIKE)
        crawlo_enc = EncodingDetector.detect(OFWEEK_LIKE)
        print(f"\n--- GBK 中文页面 ---")
        print(f"  Scrapy(w3lib): {scrapy_enc}")
        print(f"  Crawlo:        {crawlo_enc}")
        self.assertEqual(crawlo_enc, scrapy_enc)

    def test_ofweek_gbk_decode_quality(self):
        """GBK 中文页面解码质量（重点对比 Scrapy 和 Crawlo）"""
        scrapy_enc, scrapy_body = html_to_unicode('text/html', OFWEEK_LIKE)
        crawlo_enc = EncodingDetector.detect(OFWEEK_LIKE)
        crawlo_body = EncodingDetector.decode_body(OFWEEK_LIKE)

        self.assertEqual(crawlo_enc, scrapy_enc)
        self.assertEqual(crawlo_enc, 'gb18030')
        self.assertIn('数说商业', crawlo_body)
        self.assertIn('半导体产业纵横', crawlo_body)

        scrapy_moji = _count_mojibake(scrapy_body)
        crawlo_moji = _count_mojibake(crawlo_body)
        print(f"  Scrapy mojibake: {scrapy_moji}, Crawlo mojibake: {crawlo_moji}")
        self.assertEqual(scrapy_moji, 0)
        self.assertEqual(crawlo_moji, 0)

    def test_large_prefix_gbk(self):
        """大量 ASCII 前缀 + GBK 中文"""
        scrapy_enc, _ = html_to_unicode('text/html', LARGE_PREFIX_GBK)
        crawlo_enc = EncodingDetector.detect(LARGE_PREFIX_GBK)
        print(f"\n--- 大量前缀 GBK ---")
        print(f"  Scrapy: {scrapy_enc}")
        print(f"  Crawlo: {crawlo_enc}")
        self.assertEqual(crawlo_enc, 'gb18030')

    def test_gbk_content_only(self):
        """无 meta 无 header 纯 GBK bytes -> Crawlo 优势场景"""
        body = "中文内容无声明".encode('gbk')
        scrapy_enc, _ = html_to_unicode('', body)
        crawlo_enc = EncodingDetector.detect(body)
        print(f"\n--- 纯 GBK 内容（无声明）---")
        print(f"  Scrapy(w3lib): {scrapy_enc}")
        print(f"  Crawlo:        {crawlo_enc}")
        # w3lib 无 header 时回调可能不同；Crawlo 必须检测到 gb18030
        self.assertEqual(crawlo_enc, 'gb18030')

    def test_utf8_chinese(self):
        """UTF-8 中文页面"""
        scrapy_enc, _ = html_to_unicode('text/html', UTF8_CHINESE)
        crawlo_enc = EncodingDetector.detect(UTF8_CHINESE)
        print(f"\n--- UTF-8 中文 ---")
        print(f"  Scrapy: {scrapy_enc}, Crawlo: {crawlo_enc}")
        self.assertEqual(crawlo_enc, 'utf-8')

    def test_shift_jis(self):
        """Shift-JIS 日文页面"""
        scrapy_enc, _ = html_to_unicode('text/html', SHIFT_JIS_PAGE)
        crawlo_enc = EncodingDetector.detect(SHIFT_JIS_PAGE)
        print(f"\n--- Shift-JIS 日文 ---")
        print(f"  Scrapy: {scrapy_enc}, Crawlo: {crawlo_enc}")
        self.assertIn(crawlo_enc, ('shift_jis', 'cp932'))

    def test_shift_jis_decode(self):
        """Shift-JIS 日文解码"""
        _, scrapy_body = html_to_unicode('text/html', SHIFT_JIS_PAGE)
        crawlo_body = EncodingDetector.decode_body(SHIFT_JIS_PAGE)
        self.assertIn('日本語', scrapy_body)
        self.assertIn('日本語', crawlo_body)

    def test_euc_kr(self):
        """EUC-KR 韩文页面"""
        scrapy_enc, _ = html_to_unicode('text/html', EUC_KR_PAGE)
        crawlo_enc = EncodingDetector.detect(EUC_KR_PAGE)
        print(f"\n--- EUC-KR 韩文 ---")
        print(f"  Scrapy: {scrapy_enc}, Crawlo: {crawlo_enc}")
        self.assertIn(crawlo_enc, ('euc_kr', 'cp949'))

    def test_euc_kr_decode(self):
        """EUC-KR 韩文解码"""
        _, scrapy_body = html_to_unicode('text/html', EUC_KR_PAGE)
        crawlo_body = EncodingDetector.decode_body(EUC_KR_PAGE)
        self.assertIn('한글', scrapy_body)
        self.assertIn('한글', crawlo_body)

    def test_false_meta_utf8_gbk(self):
        """meta 声明 UTF-8 但实际是 GBK → 两者都信任 meta，都产出乱码"""
        scrapy_enc, scrapy_body = html_to_unicode('text/html', FALSE_META_UTF8_GBK)
        crawlo_enc = EncodingDetector.detect(FALSE_META_UTF8_GBK)
        crawlo_body = EncodingDetector.decode_body(FALSE_META_UTF8_GBK)

        print(f"\n--- 虚假声明: meta=UTF-8 实际=GBK ---")
        print(f"  Scrapy: {scrapy_enc}")
        print(f"  Crawlo: {crawlo_enc}")

        scrapy_moji = _count_mojibake(scrapy_body)
        crawlo_moji = _count_mojibake(crawlo_body)
        print(f"  Scrapy mojibake={scrapy_moji}, Crawlo mojibake={crawlo_moji}")

        # 两者都信任 meta 声明，都产生乱码
        self.assertEqual(crawlo_enc, scrapy_enc)
        self.assertEqual(crawlo_enc, 'utf-8')
        self.assertNotIn('实际是GBK编码但声明为UTF-8', crawlo_body)

    def test_false_meta_gbk_utf8(self):
        """meta 声明 GBK 但实际是 UTF-8 → 两者都信任 meta，都产出乱码"""
        scrapy_enc, scrapy_body = html_to_unicode('text/html', FALSE_META_GBK_UTF8)
        crawlo_enc = EncodingDetector.detect(FALSE_META_GBK_UTF8)
        crawlo_body = EncodingDetector.decode_body(FALSE_META_GBK_UTF8)

        print(f"\n--- 虚假声明: meta=GBK 实际=UTF-8 ---")
        print(f"  Scrapy: {scrapy_enc}")
        print(f"  Crawlo: {crawlo_enc}")

        scrapy_moji = _count_mojibake(scrapy_body)
        crawlo_moji = _count_mojibake(crawlo_body)
        print(f"  Scrapy mojibake={scrapy_moji}, Crawlo mojibake={crawlo_moji}")

        self.assertEqual(crawlo_enc, scrapy_enc)
        self.assertEqual(crawlo_enc, 'gb18030')

    def test_no_header_no_meta(self):
        """纯内容检测对比（无 header / 无 meta）"""
        bodies = {
            'GBK': "中文无声明测试".encode('gbk'),
            'UTF-8': "中文无声明测试".encode('utf-8'),
            'Shift-JIS': "日本語テスト".encode('shift_jis'),
            'Latin-1': "Café résumé".encode('latin-1'),
        }
        print(f"\n--- 纯内容检测对比（无 header / 无 meta）---")
        for name, body in bodies.items():
            scrapy_enc, scrapy_body = html_to_unicode('', body)
            crawlo_enc = EncodingDetector.detect(body)
            crawlo_body = EncodingDetector.decode_body(body)
            scrapy_moji = _count_mojibake(scrapy_body)
            crawlo_moji = _count_mojibake(crawlo_body)
            print(f"  {name:10s}:")
            print(f"    Scrapy: enc={scrapy_enc:12s} mojibake={scrapy_moji}")
            print(f"    Crawlo: enc={crawlo_enc:12s} mojibake={crawlo_moji}")


class TestRealWorldOFWeek(unittest.TestCase):
    """真实 OFWeek 页面对比测试"""

    def _compare_url(self, label: str, url: str):
        import httpx
        import asyncio

        async def compare():
            async with httpx.AsyncClient(follow_redirects=True, verify=False) as client:
                resp = await client.get(url, timeout=30)
                body = resp.content
                scrapy_enc, scrapy_body = html_to_unicode(
                    resp.headers.get('content-type', 'text/html'), body
                )
                crawlo_enc = EncodingDetector.detect(body, headers=dict(resp.headers))
                crawlo_body = EncodingDetector.decode_body(body, encoding=crawlo_enc)

                scrapy_moji = _count_mojibake(scrapy_body)
                crawlo_moji = _count_mojibake(crawlo_body)
                print(f"\n  [{label}] {url}")
                print(f"    Scrapy: enc={scrapy_enc:12s} mojibake={scrapy_moji}")
                print(f"    Crawlo: enc={crawlo_enc:12s} mojibake={crawlo_moji}")

                scrapy_ok = '数说商业' in scrapy_body or '半导体' in scrapy_body or 'OFweek' in scrapy_body
                crawlo_ok = '数说商业' in crawlo_body or '半导体' in crawlo_body or 'OFweek' in crawlo_body
                return scrapy_ok, crawlo_ok

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(compare())
        loop.close()
        return result

    def test_ofweek_urls(self):
        """6 个 OFWeek 页面真实对比"""
        urls = [
            ("30687010", "https://ee.ofweek.com/2026-05/ART-8420-2801-30687010.html"),
            ("30687321", "https://ee.ofweek.com/2026-05/ART-8420-2800-30687321.html"),
            ("30687002", "https://ee.ofweek.com/2026-05/ART-12002-2815-30687002.html"),
            ("30686714", "https://ee.ofweek.com/2026-05/ART-8110-2812-30686714.html"),
            ("30687039", "https://ee.ofweek.com/2026-05/ART-8420-2816-30687039.html"),
            ("30687360", "https://ee.ofweek.com/2026-05/ART-8210-2800-30687360.html"),
        ]
        print(f"\n{'='*70}")
        print("  真实 OFWeek 页面对比")
        print(f"{'='*70}")

        scrapy_ok = crawlo_ok = 0
        for label, url in urls:
            sh, ch = self._compare_url(label, url)
            if sh: scrapy_ok += 1
            if ch: crawlo_ok += 1

        print(f"\n{'='*70}")
        print(f"  汇总: Scrapy 正确={scrapy_ok}/6, Crawlo 正确={crawlo_ok}/6")
        print(f"{'='*70}")
        self.assertEqual(crawlo_ok, 6)
        self.assertEqual(scrapy_ok, 6)


class TestEdgeCaseComparison(unittest.TestCase):
    """边界场景对比"""

    def test_empty_body(self):
        """空 body 不应崩溃"""
        scrapy_enc, _ = html_to_unicode('', b'')
        crawlo_enc = EncodingDetector.detect(b'')
        print(f"\n--- 空 body --- Scrapy: {scrapy_enc}, Crawlo: {crawlo_enc}")

    def test_4k_boundary(self):
        """4096 边界截断 GBK 字符"""
        body = ("A" * 4090 + "中文标题").encode('gbk')[:4100]
        scrapy_enc, _ = html_to_unicode('', body)
        crawlo_enc = EncodingDetector.detect(body)
        print(f"\n--- 4096 边界截断 --- Scrapy: {scrapy_enc}, Crawlo: {crawlo_enc}")
        # Crawlo 能检测出 gbk，Scrapy 回退到 utf-8
        self.assertEqual(crawlo_enc, 'gbk')


if __name__ == '__main__':
    unittest.main(verbosity=2)
