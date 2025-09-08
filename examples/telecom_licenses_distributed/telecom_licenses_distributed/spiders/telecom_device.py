# -*- coding: utf-8 -*-
"""
电信设备许可证采集爬虫（分布式版）
==============================

功能：
- 分布式模式运行
- 电信设备许可证数据采集
- 从工信部网站采集真实数据
- Redis分布式队列和去重

运行方式：
    crawlo run telecom_device
"""

import sys
import json
import re
import hashlib
from pathlib import Path
from datetime import datetime
from crawlo.spider import Spider
from crawlo import Request
from crawlo.utils.log import get_logger

from ..items import TelecomLicenseItem

logger = get_logger(__name__)

# 请求头配置
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Content-Type': 'application/json;charset=UTF-8',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://ythzxfw.miit.gov.cn/oldyth/user-center/tbAppSearch/index',
}

# Cookies配置（如果需要）
COOKIES = {}


class TelecomDeviceSpider(Spider):
    """分布式电信设备许可证爬虫"""
    
    name = 'telecom_device'
    allowed_domains = ['ythzxfw.miit.gov.cn']
    
    # API 的基础 URL
    base_api_url = 'https://ythzxfw.miit.gov.cn/oldyth/user-center/tbAppSearch/selectResult'
    
    # 配置：起始页码和结束页码
    start_page = 1
    end_page = 26405  # 可以根据实际情况调整
    
    # 分布式爬虫配置
    custom_settings = {
        'DOWNLOAD_DELAY': 1.0,           # 分布式环境可以适当降低延迟
        'CONCURRENCY': 16,               # 分布式模式支持更高并发
        'MAX_RETRY_TIMES': 5,            # 分布式环境增加重试次数
        'DUPEFILTER_CLASS': 'crawlo.dupefilters.RedisDupeFilter',  # Redis去重
        'SCHEDULER': 'crawlo.scheduler.redis_scheduler.RedisScheduler',  # Redis调度器
    }
    
    data = {
        "categoryId": "144",
        "currentPage": 1,
        "pageSize": 5,
        "searchContent": ""
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
        """从第一页开始，逐页发起请求"""
        logger.info(f"🌐 分布式节点 {self.node_id} 开始生成请求")
        
        yield Request(
            url=self.base_api_url,
            method='POST',
            headers=HEADERS,
            cookies=COOKIES,
            body=json.dumps(self.data),
            callback=self.parse,
            meta={'page': 1, 'node_id': self.node_id},
            dont_filter=True
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
            
            if not json_data.get('success'):
                logger.error(f"[节点 {node_id}] 第 {page} 页请求失败: {json_data.get('msg', 'Unknown error')}")
                return
            
            # 提取总页数和总记录数（可选，用于验证）
            total_records = json_data.get("params", {}).get("tbAppArticle", {}).get("total", 0)
            logger.info(f"[节点 {node_id}] 第 {page} 页，总记录数: {total_records}")
            
            article_list = json_data.get("params", {}).get("tbAppArticle", {}).get("list", [])
            
            if not article_list:
                logger.warning(f"[节点 {node_id}] 第 {page} 页未找到数据")
                return
            
            logger.info(f"[节点 {node_id}] 第 {page} 页成功解析到 {len(article_list)} 条记录")
            
            # 将每条记录作为独立的 item yield 出去
            for item_data in article_list:
                # 清洗数据：移除 HTML 标签
                cleaned_item = self.clean_item(item_data)
                item = TelecomLicenseItem()
                
                # 基础字段
                item['license_number'] = cleaned_item.get('articleField01')
                item['device_name'] = cleaned_item.get('articleField02')
                item['device_model'] = cleaned_item.get('articleField03')
                item['applicant'] = cleaned_item.get('articleField04')
                item['manufacturer'] = cleaned_item.get('articleField05')
                item['issue_date'] = cleaned_item.get('articleField06')
                item['expiry_date'] = cleaned_item.get('articleField07')
                item['certificate_type'] = cleaned_item.get('articleField08')
                item['remarks'] = cleaned_item.get('articleField09')
                item['certificate_status'] = cleaned_item.get('articleField10')
                item['origin'] = cleaned_item.get('articleField11')
                item['article_id'] = cleaned_item.get('articleId')
                item['article_edit_date'] = cleaned_item.get('articleEdate')
                item['create_time'] = cleaned_item.get('createTime')
                
                # 分布式扩展字段
                item['crawl_time'] = datetime.now().isoformat()
                item['crawl_node'] = node_id
                item['data_version'] = '1.0'
                item['id'] = self._generate_unique_id(item)
                item['fingerprint'] = self._generate_fingerprint(item)
                
                yield item
            
            # --- 自动翻页逻辑 ---
            # 检查是否还有下一页
            if page < self.end_page:
                next_page = page + 1
                self.data['currentPage'] = next_page
                logger.debug(f"[节点 {node_id}] 准备爬取下一页: {next_page}")
                yield Request(
                    url=self.base_api_url,
                    method='POST',
                    headers=HEADERS,
                    cookies=COOKIES,
                    body=json.dumps(self.data),
                    callback=self.parse,
                    meta={'page': next_page, 'node_id': node_id},
                    dont_filter=True
                )
        
        except Exception as e:
            logger.error(f"[节点 {node_id}] 解析第 {page} 页响应失败: {e}", exc_info=True)
    
    def _generate_unique_id(self, item):
        """生成唯一ID"""
        license_number = item.get('license_number', '')
        article_id = item.get('article_id', '')
        unique_string = f"{license_number}_{article_id}"
        return hashlib.md5(unique_string.encode()).hexdigest()
    
    def _generate_fingerprint(self, item):
        """生成数据指纹用于分布式去重"""
        key_fields = [
            item.get('license_number', ''),
            item.get('device_name', ''),
            item.get('device_model', ''),
            item.get('manufacturer', ''),
            item.get('article_id', '')
        ]
        fingerprint_string = '|'.join(key_fields)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()
    
    @staticmethod
    def clean_item(item: dict) -> dict:
        """
        清洗单条记录，移除 HTML 标签等
        :param item: 原始字典
        :return: 清洗后的字典
        """
        html_tag_re = re.compile(r'<[^>]+>')
        cleaned = {}
        for k, v in item.items():
            if isinstance(v, str):
                # 移除 HTML 标签并去除首尾空白
                cleaned[k] = html_tag_re.sub('', v).strip()
            else:
                cleaned[k] = v
        return cleaned