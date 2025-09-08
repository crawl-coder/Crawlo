#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
telecom_licenses_standalone 项目运行脚本
======================================
基于 Crawlo 框架的电信设备许可证爬虫启动器。

🎯 快速使用:
    python run.py telecom_device                  # 运行电信设备许可证爬虫
    python run.py telecom_device --debug          # 调试模式运行

🔧 高级选项:
    python run.py telecom_device --concurrency 8  # 自定义并发数
    python run.py telecom_device --delay 2.0      # 自定义请求延迟
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path

# 添加项目路径到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from crawlo.crawler import CrawlerProcess
    from telecom_licenses_standalone.spiders.telecom_device import TelecomDeviceSpider
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请确保在项目根目录中运行此脚本")
    sys.exit(1)


def create_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description='电信设备许可证爬虫启动器 - 单机版',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # 爬虫名称（位置参数）
    parser.add_argument(
        'spider_name', 
        nargs='?',
        default='telecom_device',
        help='要运行的爬虫名称（默认：telecom_device）'
    )
    
    # 性能调优选项
    parser.add_argument(
        '--concurrency', 
        type=int,
        help='并发请求数（覆盖默认设置）'
    )
    
    parser.add_argument(
        '--delay', 
        type=float,
        help='请求延迟时间（秒）'
    )
    
    # 功能选项
    parser.add_argument(
        '--debug', 
        action='store_true',
        help='启用调试模式 - 详细日志输出'
    )
    
    parser.add_argument(
        '--max-pages', 
        type=int,
        help='最大爬取页数（用于测试）'
    )
    
    return parser


def build_settings(args):
    """根据命令行参数构建设置"""
    settings = {}
    
    # 应用命令行参数覆盖
    if args.concurrency:
        settings['CONCURRENCY'] = args.concurrency
        print(f"⚡ 设置并发数: {args.concurrency}")
    
    if args.delay:
        settings['DOWNLOAD_DELAY'] = args.delay
        print(f"⏱️  设置请求延迟: {args.delay}秒")
    
    if args.debug:
        settings['LOG_LEVEL'] = 'DEBUG'
        print("🐛 启用调试模式")
    
    return settings


async def main():
    """主函数：解析参数，构建配置，启动爬虫"""
    
    # 解析命令行参数
    parser = create_parser()
    args = parser.parse_args()
    
    print("🚀 启动电信设备许可证爬虫（单机版）")
    print("📋 目标：采集电信设备无线电发射设备型号核准许可证")
    
    # 构建设置
    custom_settings = build_settings(args)
    
    # 创建爬虫进程
    print(f"\n🚀 正在启动爬虫: {args.spider_name}")
    
    try:
        # 应用配置并启动
        process = CrawlerProcess()
        
        # 运行指定爬虫
        if args.spider_name == 'telecom_device':
            spider_cls = TelecomDeviceSpider
            # 如果指定了最大页数，修改spider设置
            if args.max_pages:
                spider_cls.end_page = args.max_pages
                print(f"🔢 限制最大页数: {args.max_pages}")
            
            await process.crawl(spider_cls, **custom_settings)
        else:
            print(f"❌ 未知爬虫: {args.spider_name}")
            print("可用爬虫: telecom_device")
            return
        
        print("\n✅ 爬虫执行完成")
        
    except ImportError as e:
        print(f"❌ 无法导入爬虫: {e}")
        print("   请检查爬虫文件是否存在")
    except Exception as e:
        print(f"❌ 运行错误: {e}")
        if args.debug:
            raise


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  用户中断爬虫执行")
    except Exception as e:
        print(f"❌ 运行错误: {e}")
        sys.exit(1)