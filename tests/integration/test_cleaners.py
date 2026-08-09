#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
数据清洗工具测试
"""
import unittest
from crawlo.utils.text.cleaner import (
    remove_html_tags,
    decode_html_entities,
    clean_text,
    extract_numbers,
    extract_phones,
    extract_emails
)


class TestCleaners(unittest.TestCase):
    """数据清洗工具测试类"""

    def test_text_cleaner(self):
        """测试文本清洗功能"""
        # 测试移除HTML标签
        html_text = "<p>这是一个<b>测试</b>文本</p>"
        clean_text_result = remove_html_tags(html_text)
        self.assertEqual(clean_text_result, "这是一个测试文本")
        
        # 测试解码HTML实体
        entity_text = "这是一个&nbsp;测试&amp;文本"
        decoded_text = decode_html_entities(entity_text)
        # &nbsp; 解码为不换行空格（\xa0）
        self.assertEqual(decoded_text, "这是一个\xa0测试&文本")
        
        # 测试综合清洗
        complex_text = "<p>这是一个&nbsp;<b>测试</b>&amp;文本</p>"
        cleaned = clean_text(complex_text)
        self.assertEqual(cleaned, "这是一个 测试&文本")

    def test_extract_tools(self):
        """测试提取工具（替代已删除的 DataFormatter）"""
        # 测试数字提取
        numbers = extract_numbers("价格 12.5 元，共 34 件")
        self.assertEqual(numbers, ["12.5", "34"])
        
        # 测试电话号码提取
        phones = extract_phones("联系 13812345678 或 010-12345678")
        self.assertEqual(phones, ["13812345678", "010-12345678"])
        
        # 测试邮箱提取
        emails = extract_emails("邮箱 a@b.com 和 c@d.cn")
        self.assertEqual(emails, ["a@b.com", "c@d.cn"])


if __name__ == '__main__':
    unittest.main()
