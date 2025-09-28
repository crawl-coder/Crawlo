#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
advanced_tools_example 项目运行脚本
============================
基于 Crawlo 框架的高级工具示例运行器。
"""
import sys
import asyncio
import argparse

from crawlo.crawler import CrawlerProcess


def run_spider(spider_name):
    """运行指定的爬虫"""
    print(f"🚀 启动爬虫: {spider_name}")
    
    # 创建爬虫进程（自动加载默认配置）
    try:
        # 确保 spider 模块被正确导入
        spider_modules = ['advanced_tools_example.spiders']
        process = CrawlerProcess(spider_modules=spider_modules)
        print("✅ 爬虫进程初始化成功")
        
        # 运行指定的爬虫
        asyncio.run(process.crawl(spider_name))
        
        print("✅ 爬虫运行完成")
        
    except Exception as e:
        print(f"❌ 运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """主函数：根据命令行参数运行相应的示例"""
    parser = argparse.ArgumentParser(description='Crawlo高级工具示例运行器')
    parser.add_argument('example', nargs='?', default='help',
                       choices=['factory', 'batch', 'controlled', 'large_scale_config', 'large_scale_helper', 'help'],
                       help='要运行的示例类型')
    
    args = parser.parse_args()
    
    if args.example == 'help' or not args.example:
        print("""
Crawlo高级工具示例使用说明
=====================

可用示例:
  factory              - 工厂模式相关模块示例
  batch                - 批处理工具示例
  controlled           - 受控爬虫混入类示例
  large_scale_config   - 大规模配置工具示例
  large_scale_helper   - 大规模爬虫辅助工具示例

运行示例:
  python run.py factory          # 运行工厂模式示例
  python run.py batch            # 运行批处理工具示例
  python run.py controlled       # 运行受控爬虫混入类示例
  python run.py large_scale_config  # 运行大规模配置工具示例
  python run.py large_scale_helper  # 运行大规模爬虫辅助工具示例
        """)
        return
    
    # 根据参数运行相应的示例
    spider_mapping = {
        'factory': 'factory_example',
        'batch': 'batch_example',
        'controlled': 'controlled_example',
        'large_scale_config': 'large_scale_config_example',
        'large_scale_helper': 'large_scale_helper_example'
    }
    
    if args.example in spider_mapping:
        run_spider(spider_mapping[args.example])
    else:
        print(f"未知示例类型: {args.example}")
        sys.exit(1)


if __name__ == '__main__':
    main()