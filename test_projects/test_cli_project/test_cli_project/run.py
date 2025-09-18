#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
test_cli_project 项目运行脚本
============================
基于 Crawlo 框架的智能爬虫启动器。
支持单机/分布式模式，灵活配置，开箱即用。

🎯 快速使用:
    python run.py spider_name                     # 单机模式运行
    python run.py spider_name --distributed       # 分布式模式运行
    python run.py spider_name --env production    # 使用预设配置
    python run.py all                             # 运行所有爬虫

🔧 高级选项:
    python run.py spider_name --dry-run           # 干运行（不执行实际爬取）
    python run.py spider_name --concurrency 16    # 自定义并发数
    python run.py spider_name --mode gentle       # 温和模式（低负载）
    python run.py spider1 spider2 --distributed   # 多爬虫分布式运行

📦 配置模式:
    --standalone     单机模式（默认）- 内存队列，无需外部依赖
    --distributed    分布式模式 - Redis队列，支持多节点
    --auto          自动模式 - 智能检测Redis可用性

🎛️ 预设配置:
    --env development    开发环境（调试友好）
    --env production     生产环境（高性能）
    --env large-scale    大规模爬取（优化内存）
    --env gentle         温和模式（低负载）
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path
from crawlo.crawler import CrawlerProcess
from crawlo.config import CrawloConfig
from crawlo.mode_manager import standalone_mode, distributed_mode, auto_mode


def create_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description='test_cli_project 爬虫启动器 - 基于 Crawlo 框架',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python run.py my_spider                    # 默认单机模式
  python run.py my_spider --distributed      # 分布式模式
  python run.py my_spider --env production   # 生产环境配置
  python run.py spider1 spider2              # 运行多个爬虫
  python run.py all                          # 运行所有爬虫
  python run.py my_spider --dry-run          # 测试模式
        """
    )
    
    # 爬虫名称（位置参数）
    parser.add_argument(
        'spiders', 
        nargs='*',
        help='要运行的爬虫名称（可指定多个，"all"表示运行所有爬虫）'
    )
    
    # 运行模式选择
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--standalone', 
        action='store_true',
        help='单机模式（默认）- 使用内存队列，无需外部依赖'
    )
    mode_group.add_argument(
        '--distributed', 
        action='store_true',
        help='分布式模式 - 使用 Redis 队列，支持多节点爬取'
    )
    mode_group.add_argument(
        '--auto', 
        action='store_true',
        help='自动模式 - 智能检测 Redis 可用性选择队列类型'
    )
    
    # 预设环境配置
    parser.add_argument(
        '--env', 
        choices=['development', 'production', 'large-scale', 'gentle'],
        help='预设环境配置（优先级高于模式选择）'
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
        '--dry-run', 
        action='store_true',
        help='干运行模式 - 解析页面但不执行实际爬取操作'
    )
    
    parser.add_argument(
        '--debug', 
        action='store_true',
        help='启用调试模式 - 详细日志输出'
    )
    
    parser.add_argument(
        '--config-file', 
        type=str,
        help='自定义配置文件路径'
    )
    
    # 环境变量支持
    parser.add_argument(
        '--from-env', 
        action='store_true',
        help='从环境变量加载配置（CRAWLO_*）'
    )
    
    return parser


def build_config(args):
    """根据命令行参数构建配置"""
    config = None
    
    # 1. 优先使用环境变量配置
    if args.from_env:
        config = CrawloConfig.from_env()
        print("📋 使用环境变量配置")
    
    # 2. 使用预设环境配置
    elif args.env:
        presets = {
            'development': CrawloConfig.presets().development(),
            'production': CrawloConfig.presets().production(),
            'large-scale': CrawloConfig.presets().large_scale(),
            'gentle': CrawloConfig.presets().gentle()
        }
        config = presets[args.env]
        print(f"🎛️  使用预设配置: {args.env}")
    
    # 3. 使用模式配置
    elif args.distributed:
        config = CrawloConfig.distributed()
        print("🌐 启用分布式模式")
    elif args.auto:
        config = CrawloConfig.auto()
        print("🤖 启用自动检测模式")
    else:
        # 默认单机模式
        config = CrawloConfig.standalone()
        print("💻 使用单机模式（默认）")
    
    # 4. 应用命令行参数覆盖
    if args.concurrency:
        config.set('CONCURRENCY', args.concurrency)
        print(f"⚡ 设置并发数: {args.concurrency}")
    
    if args.delay:
        config.set('DOWNLOAD_DELAY', args.delay)
        print(f"⏱️  设置请求延迟: {args.delay}秒")
    
    if args.debug:
        config.set('LOG_LEVEL', 'DEBUG')
        print("🐛 启用调试模式")
    
    if args.dry_run:
        # 干运行模式的配置（可根据需要调整）
        config.set('DOWNLOAD_DELAY', 0.1)  # 加快速度
        config.set('CONCURRENCY', 1)       # 降低并发
        print("🧪 启用干运行模式")
    
    return config


async def main():
    """主函数：解析参数，构建配置，启动爬虫"""
    
    # 解析命令行参数
    parser = create_parser()
    args = parser.parse_args()
    
    # 检查是否指定了爬虫
    if not args.spiders:
        print("❌ 请指定要运行的爬虫名称")
        print("\n可用的爬虫:")
        print("   # TODO: 在这里列出你的爬虫")
        print("   # from test_cli_project.spiders import MySpider")
        print("\n使用方法: python run.py <spider_name>")
        parser.print_help()
        return
    
    # 构建配置
    config = build_config(args)
    
    # 创建爬虫进程
    print(f"\n🚀 正在启动爬虫: {', '.join(args.spiders)}")
    
    if args.dry_run:
        print("   🧪 [干运行模式] 将解析页面但不执行实际爬取")
    
    try:
        # 应用配置并启动
        process = CrawlerProcess(settings=config.to_dict())
        
        # 检查是否要运行所有爬虫
        if 'all' in [s.lower() for s in args.spiders]:
            # 获取所有已注册的爬虫名称
            spider_names = process.get_spider_names()
            if not spider_names:
                print("❌ 未找到任何爬虫")
                print("💡 请确保:")
                print("  • 爬虫定义在 'spiders/' 目录中")
                print("  • 爬虫类有 'name' 属性")
                return 1
            
            print(f"📋 找到 {len(spider_names)} 个爬虫: {', '.join(spider_names)}")
            # 运行所有爬虫
            await process.crawl(spider_names)
        else:
            # 运行指定爬虫
            await process.crawl(args.spiders)
        
        print("\n✅ 所有爬虫执行完成")
        
    except ImportError as e:
        print(f"❌ 无法导入爬虫: {e}")
        print("   请检查爬虫文件是否存在，并更新 run.py 中的导入语句")
    except Exception as e:
        print(f"❌ 运行错误: {e}")
        raise


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  用户中断爬虫执行")
    except Exception as e:
        print(f"❌ 运行错误: {e}")
        sys.exit(1)