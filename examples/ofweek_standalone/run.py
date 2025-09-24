#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
单机模式运行脚本
使用新的框架架构，完全自动化初始化
"""
import asyncio
import sys
import os


async def main():
    """主函数：使用新架构的简化版本"""
    try:
        # 确保在正确的目录下
        # os.chdir(os.path.dirname(os.path.abspath(__file__)))
        
        # # 添加调试信息
        # print(f"当前工作目录: {os.getcwd()}")
        # print(f"Python路径: {sys.path[:3]}...")
        # print(f"Python版本: {sys.version}")
        #
        # # 检查配置文件
        # cfg_path = os.path.join(os.getcwd(), "crawlo.cfg")
        # print(f"配置文件路径: {cfg_path}")
        # print(f"配置文件存在: {os.path.exists(cfg_path)}")
        
        # if os.path.exists(cfg_path):
        #     import configparser
        #     config = configparser.ConfigParser()
        #     config.read(cfg_path, encoding="utf-8")
        #     print(f"配置文件内容: {dict(config)}")
        #     if config.has_section("settings"):
        #         print(f"settings部分: {dict(config['settings'])}")
        #
        # # 检查settings.py
        # settings_path = os.path.join(os.getcwd(), "ofweek_standalone", "settings.py")
        # print(f"settings.py路径: {settings_path}")
        # print(f"settings.py存在: {os.path.exists(settings_path)}")
        
        # 使用新的框架入口
        from crawlo.framework import run_spider
        from ofweek_standalone.spiders.OfweekSpider import OfweekSpider
        
        # 运行爬虫 - 框架自动处理所有初始化
        # 项目配置会自动从crawlo.cfg和settings.py加载
        await run_spider(OfweekSpider)

    except Exception as e:
        print(f"❌ 运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())