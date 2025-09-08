#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
telecom_licenses_distributed 项目运行脚本
========================================
基于 Crawlo 框架的电信设备许可证爬虫启动器（分布式版）。

🎯 快速使用:
    python run.py telecom_device                    # 运行电信设备许可证爬虫
    python run.py telecom_device --redis-host 192.168.1.100  # 指定Redis服务器

🔧 高级选项:
    python run.py telecom_device --concurrency 16   # 自定义并发数
    python run.py telecom_device --delay 1.0        # 自定义请求延迟
    python run.py telecom_device --check-redis      # 检查Redis连接

分布式使用示例:
  # 在机器A上运行
  python run.py telecom_device
  
  # 在机器B上同时运行
  python run.py telecom_device --redis-host 192.168.1.100
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
    from telecom_licenses_distributed.spiders.telecom_device import TelecomDeviceSpider
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请确保在项目根目录中运行此脚本")
    sys.exit(1)


def create_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description='电信设备许可证爬虫启动器 - 分布式版',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # 爬虫名称（位置参数）
    parser.add_argument(
        'spider_name', 
        nargs='?',
        default='telecom_device',
        help='要运行的爬虫名称（默认：telecom_device）'
    )
    
    # Redis配置
    parser.add_argument(
        '--redis-host', 
        type=str,
        default='localhost',
        help='Redis服务器地址（默认：localhost）'
    )
    
    parser.add_argument(
        '--redis-port', 
        type=int,
        default=6379,
        help='Redis端口（默认：6379）'
    )
    
    parser.add_argument(
        '--redis-password', 
        type=str,
        help='Redis密码（如果需要）'
    )
    
    # 性能配置
    parser.add_argument(
        '--concurrency', 
        type=int,
        help='并发请求数（覆盖配置文件设置）'
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
        help='启用调试模式'
    )
    
    parser.add_argument(
        '--check-redis', 
        action='store_true',
        help='检查Redis连接后退出'
    )
    
    parser.add_argument(
        '--max-pages', 
        type=int,
        help='最大爬取页数（用于测试）'
    )
    
    return parser


async def check_redis_connection(host, port, password=None):
    """检查Redis连接"""
    try:
        import redis.asyncio as aioredis
        
        if password:
            url = f'redis://:{password}@{host}:{port}/0'
        else:
            url = f'redis://{host}:{port}/0'
        
        redis = aioredis.from_url(url)
        await redis.ping()
        await redis.aclose()
        
        print(f"✅ Redis连接成功: {host}:{port}")
        return True
        
    except Exception as e:
        print(f"❌ Redis连接失败: {host}:{port} - {e}")
        return False


def build_settings(args):
    """根据命令行参数构建设置"""
    settings = {}
    
    # Redis配置
    if args.redis_password:
        redis_url = f'redis://:{args.redis_password}@{args.redis_host}:{args.redis_port}/0'
    else:
        redis_url = f'redis://{args.redis_host}:{args.redis_port}/0'
    
    settings['REDIS_URL'] = redis_url
    settings['REDIS_HOST'] = args.redis_host
    settings['REDIS_PORT'] = args.redis_port
    if args.redis_password:
        settings['REDIS_PASSWORD'] = args.redis_password
    
    # 其他配置
    if args.debug:
        settings['LOG_LEVEL'] = 'DEBUG'
        settings['DUPEFILTER_DEBUG'] = True
        settings['FILTER_DEBUG'] = True
        print("🐛 启用调试模式")
    
    if args.concurrency:
        settings['CONCURRENCY'] = args.concurrency
        print(f"⚡ 设置并发数: {args.concurrency}")
    
    if args.delay:
        settings['DOWNLOAD_DELAY'] = args.delay
        print(f"⏱️  设置请求延迟: {args.delay}秒")
    
    return settings


async def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    print("🌐 启动电信设备许可证爬虫（分布式版）")
    print("📋 目标：大规模采集电信设备许可证数据")
    
    # 检查Redis连接
    redis_ok = await check_redis_connection(
        args.redis_host, 
        args.redis_port, 
        args.redis_password
    )
    
    if not redis_ok:
        print("\n💡 解决方案:")
        print("   1. 确保Redis服务已启动")
        print("   2. 检查Redis配置和网络连接")
        print("   3. 验证Redis密码（如果设置了）")
        if args.check_redis:
            return
        else:
            print("   4. 使用 --check-redis 选项仅测试连接")
            sys.exit(1)
    
    if args.check_redis:
        print("🎉 Redis连接检查完成")
        return
    
    # 构建设置
    custom_settings = build_settings(args)
    
    print(f"🔗 Redis服务器: {args.redis_host}:{args.redis_port}")
    print(f"🌐 多节点模式: 可在其他机器运行相同脚本")
    
    # 创建爬虫进程
    print(f"\n🚀 正在启动爬虫: {args.spider_name}")
    
    try:
        # 应用配置并启动
        from crawlo.settings.setting_manager import SettingManager
        settings_manager = SettingManager()
        
        # 更新设置
        for key, value in custom_settings.items():
            settings_manager.set(key, value)
        
        process = CrawlerProcess(settings=settings_manager)
        
        # 运行指定爬虫
        if args.spider_name == 'telecom_device':
            spider_cls = TelecomDeviceSpider
            # 如果指定了最大页数，修改spider设置
            if args.max_pages:
                spider_cls.end_page = args.max_pages
                print(f"🔢 限制最大页数: {args.max_pages}")
            
            await process.crawl(spider_cls)
        else:
            print(f"❌ 未知爬虫: {args.spider_name}")
            print("可用爬虫: telecom_device")
            return
        
        print("✅ 当前节点执行完成！")
        print("📊 查看输出文件获取当前节点的采集结果")
        print("🔄 其他节点可继续处理剩余任务")
        
    except ImportError as e:
        print(f"❌ 无法导入爬虫: {e}")
        print("   请检查爬虫文件是否存在")
    except Exception as e:
        print(f"❌ 当前节点执行出错: {e}")
        if args.debug:
            raise


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  当前节点被用户中断")
        print("🔄 其他节点可继续运行处理剩余任务")
    except Exception as e:
        print(f"❌ 运行错误: {e}")
        sys.exit(1)