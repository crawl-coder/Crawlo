# -*- coding: utf-8 -*-
"""
API数据采集爬虫（列表页模式）
==========================

功能：
- 分布式模式运行
- API数据采集（列表页直接获取完整数据）
- Redis分布式队列和去重

运行方式：
    crawlo run api_data
"""

import sys
import json
import re
import hashlib
from datetime import datetime
from crawlo.spider import Spider
from crawlo import Request
from crawlo.utils.log import get_logger

from ..items import ApiDataItem

logger = get_logger(__name__)


class ApiDataSpider(Spider):
    """API数据采集爬虫（列表页模式）"""
    
    name = 'api_data'
    allowed_domains = ['api.example.com']
    
    # API 的基础 URL
    base_api_url = 'https://api.example.com/data'
    
    # 配置：起始页码和结束页码
    start_page = 1
    end_page = 1000  # 可以根据实际情况调整
    
    # 爬虫配置
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,           # 列表页模式可以适当降低延迟
        'CONCURRENCY': 32,               # 支持更高并发
        'MAX_RETRY_TIMES': 5,            # 增加重试次数
        'DUPEFILTER_CLASS': 'crawlo.dupefilters.RedisDupeFilter',  # Redis去重
        'SCHEDULER': 'crawlo.scheduler.redis_scheduler.RedisScheduler',  # Redis调度器
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.node_id = self._generate_node_id()
        
    def _generate_node_id(self):
        """生成节点ID"""
        import socket
        import os
        hostname = socket.gethostname()
        pid = os.getpid()
        timestamp = int(datetime.now().timestamp())
        return f"{hostname}-{pid}-{timestamp}"
    
    def start_requests(self):
        """生成所有页面的请求，让多个节点可以并行处理"""
        logger.info(f"🌐 分布式节点 {self.node_id} 开始生成请求")
        
        # 生成所有页面的请求
        for page in range(self.start_page, self.end_page + 1):
            yield Request(
                url=f'{self.base_api_url}?page={page}&limit=50',
                callback=self.parse,
                meta={'page': page, 'node_id': self.node_id},
                # 在分布式环境中，启用去重机制避免重复请求
                dont_filter=False
            )
    
    def parse(self, response):
        """
        解析 API 响应
        :param response: Crawlo Response 对象
        """
        page = response.meta['page']
        node_id = response.meta.get('node_id', 'unknown')
        logger.info(f"[节点 {node_id}] 正在解析第 {page} 页，状态码: {response.status_code}")
        
        try:
            json_data = response.json()
            
            # 检查API响应是否成功
            if not json_data.get('success', True):
                logger.error(f"[节点 {node_id}] 第 {page} 页请求失败: {json_data.get('message', 'Unknown error')}")
                return
            
            # 提取数据列表
            data_list = json_data.get("data", [])
            
            if not data_list:
                logger.warning(f"[节点 {node_id}] 第 {page} 页未找到数据")
                return
            
            logger.info(f"[节点 {node_id}] 第 {page} 页成功解析到 {len(data_list)} 条记录")
            
            # 将每条记录作为独立的 item yield 出去
            for item_data in data_list:
                item = ApiDataItem()
                
                # 基础字段
                item['id'] = item_data.get('id')
                item['name'] = item_data.get('name')
                item['description'] = item_data.get('description')
                item['category'] = item_data.get('category')
                item['price'] = item_data.get('price')
                item['status'] = item_data.get('status')
                item['created_at'] = item_data.get('created_at')
                item['updated_at'] = item_data.get('updated_at')
                
                # 分布式扩展字段
                item['crawl_time'] = datetime.now().isoformat()
                item['crawl_node'] = node_id
                item['data_version'] = '1.0'
                
                yield item
                
        except Exception as e:
            logger.error(f"[节点 {node_id}] 解析第 {page} 页响应失败: {e}", exc_info=True)