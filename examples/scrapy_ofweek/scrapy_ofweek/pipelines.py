# -*- coding: UTF-8 -*-
"""
scrapy_ofweek.pipelines
=======================
数据处理管道。
"""

import json
import os
from datetime import datetime


class JsonWriterPipeline:
    """JSON 文件写入管道"""
    
    def __init__(self):
        self.items = []
        self.start_time = None
        self.end_time = None
        
    def open_spider(self, spider):
        """爬虫启动时调用"""
        self.start_time = datetime.now()
        spider.logger.info(f'爬虫启动时间: {self.start_time.strftime("%Y-%m-%d %H:%M:%S")}')
        
        # 确保输出目录存在
        os.makedirs('output', exist_ok=True)
        
    def close_spider(self, spider):
        """爬虫关闭时调用"""
        self.end_time = datetime.now()
        cost_time = (self.end_time - self.start_time).total_seconds()
        
        # 写入 JSON 文件
        output_file = f'output/scrapy_ofweek_{self.start_time.strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.items, f, ensure_ascii=False, indent=2)
        
        # 输出统计信息
        spider.logger.info('=' * 60)
        spider.logger.info('Scrapy 测试统计:')
        spider.logger.info(f'  开始时间: {self.start_time.strftime("%Y-%m-%d %H:%M:%S")}')
        spider.logger.info(f'  结束时间: {self.end_time.strftime("%Y-%m-%d %H:%M:%S")}')
        spider.logger.info(f'  总耗时: {cost_time:.2f} 秒')
        spider.logger.info(f'  成功条数: {len(self.items)}')
        if cost_time > 0:
            spider.logger.info(f'  平均速度: {len(self.items)/cost_time:.2f} items/s')
        spider.logger.info(f'  输出文件: {output_file}')
        spider.logger.info('=' * 60)
        
    def process_item(self, item, spider):
        """处理每个 item"""
        self.items.append(dict(item))
        return item
