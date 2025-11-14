#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
SHA256 vs MD5 性能对比测试
=====================
测试在爬虫场景中两种哈希算法的性能差异
"""

import hashlib
import time
from collections import namedtuple


# 创建测试数据
TestItem = namedtuple('TestItem', ['title', 'url', 'content', 'price', 'tags'])

def create_test_items(count=10000):
    """创建测试数据项"""
    items = []
    for i in range(count):
        item = TestItem(
            title=f"Test Title {i}",
            url=f"https://example.com/page/{i}",
            content=f"This is test content number {i} with some additional text to make it longer",
            price=99.99 + i,
            tags=[f"tag{j}" for j in range(5)]
        )
        items.append(item)
    return items


def md5_fingerprint(data):
    """使用MD5生成指纹"""
    if hasattr(data, '_asdict'):
        data_dict = data._asdict()
    else:
        data_dict = {'__data__': str(data)}
    
    sorted_items = sorted(data_dict.items())
    fingerprint_string = '|'.join([f"{k}={v}" for k, v in sorted_items if v is not None])
    return hashlib.md5(fingerprint_string.encode('utf-8')).hexdigest()


def sha256_fingerprint(data):
    """使用SHA256生成指纹"""
    if hasattr(data, '_asdict'):
        data_dict = data._asdict()
    else:
        data_dict = {'__data__': str(data)}
    
    sorted_items = sorted(data_dict.items())
    fingerprint_string = '|'.join([f"{k}={v}" for k, v in sorted_items if v is not None])
    return hashlib.sha256(fingerprint_string.encode('utf-8')).hexdigest()


def performance_test():
    """性能测试"""
    print("开始哈希算法性能测试...")
    print("=" * 50)
    
    # 创建测试数据
    test_items = create_test_items(10000)
    
    # 测试MD5性能
    start_time = time.time()
    md5_results = []
    for item in test_items:
        fingerprint = md5_fingerprint(item)
        md5_results.append(fingerprint)
    md5_time = time.time() - start_time
    
    # 测试SHA256性能
    start_time = time.time()
    sha256_results = []
    for item in test_items:
        fingerprint = sha256_fingerprint(item)
        sha256_results.append(fingerprint)
    sha256_time = time.time() - start_time
    
    # 输出结果
    print(f"测试数据量: {len(test_items)} 条")
    print(f"MD5 耗时: {md5_time:.4f} 秒")
    print(f"SHA256 耗时: {sha256_time:.4f} 秒")
    print(f"性能差异: {((sha256_time - md5_time) / md5_time * 100):.2f}%")
    
    # 验证结果一致性
    print("\n验证指纹长度:")
    print(f"MD5 指纹长度: {len(md5_results[0])} 字符")
    print(f"SHA256 指纹长度: {len(sha256_results[0])} 字符")
    
    # 检查是否有重复指纹（理论上不应该有）
    md5_unique = len(set(md5_results))
    sha256_unique = len(set(sha256_results))
    print(f"\n唯一指纹数量:")
    print(f"MD5: {md5_unique}/{len(test_items)} ({md5_unique/len(test_items)*100:.2f}%)")
    print(f"SHA256: {sha256_unique}/{len(test_items)} ({sha256_unique/len(test_items)*100:.2f}%)")


if __name__ == '__main__':
    performance_test()