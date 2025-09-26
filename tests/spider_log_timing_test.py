#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
模拟爬虫场景测试日志文件生成时机
"""

import os
import sys
import time
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crawlo.logging import configure_logging as configure, get_logger


class MockSpider:
    """模拟爬虫类"""
    
    def __init__(self, name):
        self.name = name
        self.logger = get_logger(f'spider.{name}')
    
    async def start_requests(self):
        """开始请求"""
        self.logger.info(f"Spider {self.name} 开始请求")
        # 模拟一些网络请求
        for i in range(3):
            self.logger.info(f"Spider {self.name} 发送请求 {i+1}")
            await asyncio.sleep(0.1)
    
    async def parse(self, response):
        """解析响应"""
        self.logger.info(f"Spider {self.name} 解析响应")
        # 模拟解析过程
        await asyncio.sleep(0.05)
        self.logger.info(f"Spider {self.name} 提取数据")
        return {"data": f"item from {self.name}"}
    
    async def crawl(self):
        """执行爬取"""
        self.logger.info(f"Spider {self.name} 开始爬取")
        await self.start_requests()
        await self.parse("mock_response")
        self.logger.info(f"Spider {self.name} 爬取完成")


async def test_spider_logging_timing():
    """测试爬虫日志记录时机"""
    print("=== 测试爬虫日志记录时机 ===")
    
    # 设置日志文件路径
    log_file = "logs/spider_timing_test.log"
    
    # 删除可能存在的旧日志文件
    if os.path.exists(log_file):
        os.remove(log_file)
    
    # 配置日志系统
    print("1. 配置日志系统...")
    configure(
        level='INFO',
        file_path=log_file,
        console_enabled=True,
        file_enabled=True
    )
    
    print(f"   配置后日志文件是否存在: {os.path.exists(log_file)}")
    
    # 创建爬虫实例
    print("\n2. 创建爬虫实例...")
    spider = MockSpider("test_spider")
    print(f"   创建爬虫后日志文件是否存在: {os.path.exists(log_file)}")
    
    # 检查文件内容
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"   日志文件行数: {len(content.splitlines())}")
    
    # 执行爬取
    print("\n3. 执行爬取...")
    await spider.crawl()
    
    print(f"   爬取完成后日志文件是否存在: {os.path.exists(log_file)}")
    
    # 检查最终文件内容
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(f"\n最终日志文件内容:")
            print(f"  总行数: {len(lines)}")
            print(f"  文件大小: {os.path.getsize(log_file)} 字节")
            if lines:
                print(f"  第一行: {lines[0].strip()}")
                print(f"  最后一行: {lines[-1].strip()}")
    
    # 等待一段时间后再次检查
    print("\n4. 等待2秒后再次检查...")
    time.sleep(2)
    
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(f"  等待后总行数: {len(lines)}")


async def test_multiple_spiders():
    """测试多个爬虫的日志记录"""
    print("\n=== 测试多个爬虫的日志记录 ===")
    
    # 设置日志文件路径
    log_file = "logs/multi_spider_test.log"
    
    # 删除可能存在的旧日志文件
    if os.path.exists(log_file):
        os.remove(log_file)
    
    # 配置日志系统
    configure(
        level='INFO',
        file_path=log_file,
        console_enabled=True,
        file_enabled=True
    )
    
    # 创建多个爬虫实例
    spiders = [MockSpider(f"spider_{i}") for i in range(3)]
    
    print("1. 顺序执行多个爬虫...")
    for i, spider in enumerate(spiders):
        print(f"   执行爬虫 {i+1}...")
        await spider.crawl()
        
        # 检查当前日志文件状态
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"     当前日志行数: {len(lines)}")
    
    print(f"\n   所有爬虫执行完成后日志文件是否存在: {os.path.exists(log_file)}")
    
    # 检查最终文件内容
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(f"\n最终日志文件内容:")
            print(f"  总行数: {len(lines)}")
            print(f"  文件大小: {os.path.getsize(log_file)} 字节")
            if lines:
                print(f"  第一行: {lines[0].strip()}")
                print(f"  最后一行: {lines[-1].strip()}")


async def main():
    """主函数"""
    print("开始测试爬虫日志记录时机...")
    
    try:
        await test_spider_logging_timing()
        await test_multiple_spiders()
        
        print("\n=== 所有测试完成 ===")
        
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    asyncio.run(main())