# -*- coding: UTF-8 -*-
"""
阶段2：单机模式增强示例
- 增加持久化去重机制（如文件存储）
- 优化内存使用，处理大数据量
- 保持单机运行特性
"""

import sys
import os
import asyncio

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.config import CrawloConfig
from crawlo.crawler import CrawlerProcess
from ofweek_project.spiders.OfweekSpider import OfweekSpider

# 自定义文件持久化过滤器
class FileFilter:
    """
    基于文件的持久化去重过滤器
    将已访问的URL保存到文件中，程序重启后不会重复抓取
    """
    def __init__(self, filename='visited_urls.txt'):
        self.filename = filename
        self.visited = set()
        self._load_visited()
    
    def _load_visited(self):
        """从文件加载已访问的URL"""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    self.visited = set(line.strip() for line in f)
                print(f"已加载 {len(self.visited)} 个已访问URL")
            except Exception as e:
                print(f"加载已访问URL文件失败: {e}")
    
    def _save_visited(self, url):
        """将URL保存到文件"""
        try:
            with open(self.filename, 'a', encoding='utf-8') as f:
                f.write(f"{url}\n")
        except Exception as e:
            print(f"保存URL到文件失败: {e}")
    
    async def contains(self, url):
        """检查URL是否已访问"""
        return url in self.visited
    
    async def add(self, url):
        """添加URL到已访问集合和文件中"""
        if url not in self.visited:
            self.visited.add(url)
            self._save_visited(url)

async def main():
    print("=== 阶段2：单机模式增强 ===")
    print("特点：")
    print("- 增加持久化去重机制（如文件存储）")
    print("- 优化内存使用，处理大数据量")
    print("- 保持单机运行特性")
    print()
    
    # 使用 standalone 模式配置作为基础
    config = CrawloConfig.standalone(
        concurrency=6,           # 适中的并发数
        download_delay=1.5,      # 适中的下载延迟
        project_name='ofweek_project'
    )
    
    # 获取配置字典并添加自定义过滤器配置
    config_dict = config.to_dict()
    
    # 注意：在这个阶段，我们演示的是概念，实际实现需要框架支持自定义过滤器
    # 这里只是展示思路，实际使用时需要框架支持
    
    # 打印配置信息
    print("配置详情：")
    print(f"- 并发数: {config_dict.get('CONCURRENCY', 6)}")
    print(f"- 下载延迟: {config_dict.get('DOWNLOAD_DELAY', 1.5)} 秒")
    print(f"- 过滤器: {config_dict.get('FILTER_CLASS', 'MemoryFilter')} (概念演示)")
    print()
    
    print("阶段2说明：")
    print("在这个阶段，我们通过自定义的 FileFilter 实现持久化去重：")
    print("1. 程序启动时从文件加载已访问的URL")
    print("2. 爬取过程中将新URL保存到文件")
    print("3. 程序重启后不会重复抓取已保存的URL")
    print()
    
    # 演示 FileFilter 的使用
    print("演示 FileFilter 的使用：")
    filter_instance = FileFilter('demo_visited_urls.txt')
    
    # 模拟添加一些URL
    test_urls = [
        'https://ee.ofweek.com/article1.html',
        'https://ee.ofweek.com/article2.html',
        'https://ee.ofweek.com/article3.html'
    ]
    
    for url in test_urls:
        if not await filter_instance.contains(url):
            await filter_instance.add(url)
            print(f"添加新URL: {url}")
        else:
            print(f"URL已存在: {url}")
    
    print()
    print("注意：在实际框架中，需要集成自定义过滤器到爬虫引擎中")
    print("这通常需要修改框架的核心组件或通过插件机制实现")
    print()
    
    # 创建爬虫进程并应用配置
    process = CrawlerProcess(settings=config_dict)
    
    # 运行爬虫
    print("开始运行增强型单机爬虫...")
    await process.crawl(OfweekSpider)
    
    print("增强型单机爬虫运行完成")

if __name__ == '__main__':
    asyncio.run(main())