#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
指纹算法性能对比测试
测试 MD5 vs SHA256 在请求指纹生成中的性能差异
"""

import hashlib
import time
from w3lib.url import canonicalize_url


def benchmark_hash(hash_name, iterations=100000):
    """基准测试指定哈希算法"""
    
    # 测试数据
    method = 'GET'
    url = 'https://example.com/page?id=123&name=test'
    body = b''
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html'}
    meta = {'retry_times': 0, 'proxy': 'http://proxy:8080'}
    
    start_time = time.time()
    
    for i in range(iterations):
        hash_func = hashlib.new(hash_name)
        hash_func.update(method.encode('utf-8'))
        hash_func.update(canonicalize_url(url).encode('utf-8'))
        hash_func.update(body or b'')
        
        if headers:
            sorted_headers = sorted(headers.items())
            for name, value in sorted_headers:
                hash_func.update(f"{name}:{value}".encode('utf-8'))
        
        if meta:
            key_meta_fields = {}
            for key in ['retry_times', 'is_retry', 'download_slot', 'proxy', 'download_timeout']:
                if key in meta:
                    key_meta_fields[key] = meta[key]
            
            if key_meta_fields:
                sorted_meta_items = sorted(key_meta_fields.items())
                for key, value in sorted_meta_items:
                    hash_func.update(f"meta_{key}:{str(value)}".encode('utf-8'))
        
        fingerprint = hash_func.hexdigest()
    
    elapsed = time.time() - start_time
    speed = iterations / elapsed
    
    return elapsed, speed, fingerprint


def main():
    print('=' * 60)
    print('指纹算法性能对比测试')
    print('=' * 60)
    
    iterations = 100000
    print(f'\n测试次数: {iterations:,}\n')
    
    # 测试 MD5
    print('测试 MD5...')
    md5_time, md5_speed, md5_fp = benchmark_hash('md5', iterations)
    print(f'  耗时: {md5_time:.3f} 秒')
    print(f'  速度: {md5_speed:,.0f} 次/秒')
    print(f'  指纹长度: {len(md5_fp)} 字符')
    print(f'  示例: {md5_fp}')
    
    # 测试 SHA256
    print('\n测试 SHA256...')
    sha256_time, sha256_speed, sha256_fp = benchmark_hash('sha256', iterations)
    print(f'  耗时: {sha256_time:.3f} 秒')
    print(f'  速度: {sha256_speed:,.0f} 次/秒')
    print(f'  指纹长度: {len(sha256_fp)} 字符')
    print(f'  示例: {sha256_fp}')
    
    # 性能对比
    print('\n' + '=' * 60)
    print('性能对比')
    print('=' * 60)
    speedup = sha256_time / md5_time
    print(f'MD5 比 SHA256 快: {speedup:.2f}x')
    print(f'耗时减少: {((sha256_time - md5_time) / sha256_time * 100):.1f}%')
    
    print('\n' + '=' * 60)
    print('结论')
    print('=' * 60)
    print('✅ 请求指纹使用 MD5：性能提升显著，适合高频调用场景')
    print('✅ 数据指纹保持 SHA256：数据准确性更重要，性能影响小')
    print('\n🎉 测试完成！')


if __name__ == '__main__':
    main()
