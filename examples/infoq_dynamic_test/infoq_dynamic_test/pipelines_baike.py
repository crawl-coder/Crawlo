# -*- coding: UTF-8 -*-
"""
百度百科企业数据管道
"""
import json
import os
from datetime import datetime
from crawlo.pipelines import BasePipeline


class BaikeCompanyFilePipeline(BasePipeline):
    """百度百科企业数据文件管道 - 保存为JSON"""
    
    def __init__(self, crawler):
        super().__init__(crawler)
        
        # 输出文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_file = f'output/baike_companies_{timestamp}.json'
        
        # 确保目录存在
        os.makedirs('output', exist_ok=True)
        
        # 数据存储
        self.companies = []
    
    def open_spider(self, spider):
        """爬虫启动"""
        self.logger.info(f"📁 数据管道已启动，输出文件: {self.output_file}")
    
    def close_spider(self, spider):
        """爬虫关闭 - 保存数据"""
        if self.companies:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(self.companies, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ 已保存 {len(self.companies)} 家企业数据到 {self.output_file}")
        else:
            self.logger.warning("⚠️ 未采集到任何数据")
    
    def process_item(self, item, spider):
        """处理数据项"""
        # 转换为字典
        company_dict = dict(item)
        
        # 保存到列表
        self.companies.append(company_dict)
        
        # 实时日志
        status = company_dict.get('status', 'unknown')
        company_name = company_dict.get('company_name', 'Unknown')
        
        if status == 'success':
            self.logger.debug(f"  ✓ {company_name}")
        else:
            self.logger.debug(f"  ✗ {company_name}: {company_dict.get('error_message', 'Unknown error')}")
        
        return item
