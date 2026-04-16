#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试所有下载器的 Response 创建
"""

import ast
from pathlib import Path

def check_downloader(file_path):
    """检查下载器文件"""
    print(f"\n检查 {file_path.name}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找所有 Response( 的位置
    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        if 'Response(' in line or 'Response (' in line:
            # 检查前后几行
            start = max(0, i-5)
            end = min(len(lines), i+3)
            context = '\n'.join(lines[start:end])
            
            if 'status=' in context:
                print(f"  ✅ 行 {i}: 使用 status=")
            elif 'status_code=' in context:
                print(f"  ❌ 行 {i}: 使用 status_code= (错误!)")
                print(f"     {line.strip()}")

def main():
    downloader_dir = Path(__file__).parent / 'crawlo' / 'downloader'
    
    print("=" * 70)
    print("检查所有下载器文件")
    print("=" * 70)
    
    for py_file in sorted(downloader_dir.glob('*.py')):
        if py_file.name == '__init__.py' or py_file.name == 'constants.py':
            continue
        check_downloader(py_file)

if __name__ == "__main__":
    main()
