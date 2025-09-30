#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Response.follow 方法简单测试
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 直接测试 urljoin 方法
from urllib.parse import urljoin


def test_urljoin():
    """测试 urljoin 方法"""
    base_url = "https://example.com/test"
    
    # 测试绝对URL
    absolute_url = urljoin(base_url, "https://other.com/page")
    print(f"绝对URL: {absolute_url}")
    assert absolute_url == "https://other.com/page"
    
    # 测试相对URL
    relative_url = urljoin(base_url, "/relative/path")
    print(f"相对URL: {relative_url}")
    assert relative_url == "https://example.com/relative/path"
    
    # 测试复杂相对URL
    complex_url = urljoin(base_url, "../other/path")
    print(f"复杂相对URL: {complex_url}")
    assert complex_url == "https://example.com/other/path"
    
    print("所有测试通过！")


if __name__ == '__main__':
    test_urljoin()