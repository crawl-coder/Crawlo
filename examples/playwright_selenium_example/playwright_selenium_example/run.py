# -*- coding: UTF-8 -*-
"""
运行示例爬虫
"""
import asyncio
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlo.crawler import CrawlerProcess
from crawlo.settings.setting_manager import SettingManager
from settings import *


def run_with_playwright():
    """使用 Playwright 下载器运行爬虫"""
    print("使用 Playwright 下载器运行爬虫...")
    
    # 创建设置管理器
    settings = SettingManager()
    
    # 更新下载器配置
    settings.set('DOWNLOADER', 'crawlo.downloader.playwright_downloader.PlaywrightDownloader')
    settings.set('PLAYWRIGHT_BROWSER_TYPE', 'chromium')
    settings.set('PLAYWRIGHT_HEADLESS', True)
    settings.set('LOG_LEVEL', 'INFO')
    
    # 创建并运行爬虫进程
    process = CrawlerProcess(
        settings=settings,
        spider_modules=['playwright_selenium_example.spiders']  # 自动发现爬虫模块
    )
    
    # 使用 asyncio.run 来运行异步函数
    asyncio.run(process.crawl('example_spider'))


def run_with_selenium():
    """使用 Selenium 下载器运行爬虫"""
    print("使用 Selenium 下载器运行爬虫...")
    
    # 创建设置管理器
    settings = SettingManager()
    
    # 更新下载器配置
    settings.set('DOWNLOADER', 'crawlo.downloader.selenium_downloader.SeleniumDownloader')
    settings.set('SELENIUM_BROWSER_TYPE', 'chrome')
    settings.set('SELENIUM_HEADLESS', True)
    settings.set('LOG_LEVEL', 'INFO')
    
    # 创建并运行爬虫进程
    process = CrawlerProcess(
        settings=settings,
        spider_modules=['playwright_selenium_example.spiders']  # 自动发现爬虫模块
    )
    
    # 使用 asyncio.run 来运行异步函数
    asyncio.run(process.crawl('example_spider'))


if __name__ == '__main__':
    print("选择要测试的下载器:")
    print("1. Playwright 下载器")
    print("2. Selenium 下载器")
    
    choice = input("请输入选择 (1 或 2): ")
    
    if choice == '1':
        run_with_playwright()
    elif choice == '2':
        run_with_selenium()
    else:
        print("无效选择，使用默认的 AioHttp 下载器")
        process = CrawlerProcess(spider_modules=['playwright_selenium_example.spiders'])
        asyncio.run(process.crawl('example_spider'))