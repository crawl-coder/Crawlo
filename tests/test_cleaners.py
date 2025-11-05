#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
数据清洗工具测试
"""
import unittest
from crawlo.tools import (
    TextCleaner,
    DataFormatter,
    remove_html_tags,
    decode_html_entities,
    clean_text,
    format_number,
    format_currency,
    format_phone_number
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
        self.assertEqual(decoded_text, "这是一个 测试&文本")
        
        # 测试综合清洗
        complex_text = "<p>这是一个&nbsp;<b>测试</b>&amp;文本</p>"
        cleaned = clean_text(complex_text)
        self.assertEqual(cleaned, "这是一个 测试&文本")

    def test_data_formatter(self):
        """测试数据格式化功能"""
        # 测试数字格式化
        formatted_num = format_number(1234.567, precision=2, thousand_separator=True)
        self.assertEqual(formatted_num, "1,234.57")
        
        # 测试货币格式化
        formatted_currency = format_currency(1234.567, "¥", 2)
        self.assertEqual(formatted_currency, "¥1,234.57")
        
        # 测试电话号码格式化
        formatted_phone = format_phone_number("13812345678", "+86", "international")
        self.assertEqual(formatted_phone, "+86 138 1234 5678")


if __name__ == '__main__':
    unittest.main()