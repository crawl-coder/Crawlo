#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
百度百科爬虫 - 100家企业测试脚本
=================================

功能：
1. 测试100家知名企业的百度百科页面采集
2. 只验证企业名称（提取页面标题）
3. 统计成功率、失败率
4. 输出详细日志

用法：
    python run_baike_100_test.py
"""
import os
import sys
import asyncio

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from crawlo.crawler import CrawlerProcess


def main():
    """运行爬虫"""
    # 获取命令行参数
    company_count = sys.argv[1] if len(sys.argv) > 1 else '100'
    
    # 设置环境变量来控制测试企业数量
    os.environ['BAIKE_COMPANY_COUNT'] = company_count
    
    print(f"\n{'='*70}")
    print(f"百度百科爬虫 - {company_count}家企业测试")
    print(f"{'='*70}\n")
    
    try:
        asyncio.run(CrawlerProcess().crawl('baike_company'))
    except Exception as e:
        print(f"运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
    
    """
    使用方法：
    
    # 测试100家企业（默认）
    python run_baike_100_test.py
    
    # 测试50家企业
    python run_baike_100_test.py 50
    
    # 测试10家企业（快速测试）
    python run_baike_100_test.py 10
    """
