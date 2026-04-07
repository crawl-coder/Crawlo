#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
InfoQ 动态下载器测试项目
========================
测试 DynamicRenderMiddleware 和 PlaywrightDownloader 的使用

测试目标：https://www.infoq.cn/zones/harmonyos/latest
"""
import os
import sys
import asyncio

from crawlo.crawler import CrawlerProcess


def main():
    """运行爬虫"""
    # 获取命令行参数
    test_mode = sys.argv[1] if len(sys.argv) > 1 else 'protocol'
    
    # 设置环境变量来控制测试模式
    os.environ['TEST_MODE'] = test_mode
    
    print(f"\n{'='*60}")
    print(f"InfoQ 动态下载器测试")
    print(f"测试模式: {test_mode}")
    print(f"{'='*60}\n")
    
    try:
        asyncio.run(CrawlerProcess().crawl('infoq_spider'))
    except Exception as e:
        print(f"运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
    
    """
    使用方法：
    
    # 测试1：协议下载器（默认）
    python run.py protocol
    
    # 测试2：动态下载器（域名配置）
    python run.py dynamic_domain
    
    # 测试3：动态下载器（请求标记）
    python run.py dynamic_meta
    """
