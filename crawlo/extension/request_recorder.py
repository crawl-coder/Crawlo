#!/usr/bin/python
# -*- coding:UTF-8 -*-
import os
import json
from typing import Any
from datetime import datetime

from crawlo.event import CrawlerEvent
from crawlo.logging import get_logger


class RequestRecorderExtension:
    """
    请求记录扩展
    记录所有发送的请求信息到文件，便于调试和分析
    """

    def __init__(self, crawler: Any):
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__)
        
        # 获取配置参数
        self.enabled = self.settings.get_bool('REQUEST_RECORDER_ENABLED', False)
        self.output_dir = self.settings.get('REQUEST_RECORDER_OUTPUT_DIR', 'requests_log')
        self.max_file_size = self.settings.get_int('REQUEST_RECORDER_MAX_FILE_SIZE', 10 * 1024 * 1024)  # 默认10MB
        
        # 创建输出目录
        if self.enabled:
            os.makedirs(self.output_dir, exist_ok=True)
            
        self.current_file = None
        self.current_file_size = 0

    @classmethod
    def create_instance(cls, crawler: Any) -> 'RequestRecorderExtension':
        # 只有当配置启用时才创建实例
        if not crawler.settings.get_bool('REQUEST_RECORDER_ENABLED', False):
            from crawlo.exceptions import NotConfigured
            raise NotConfigured("RequestRecorderExtension: REQUEST_RECORDER_ENABLED is False")
        
        o = cls(crawler)
        if o.enabled:
            crawler.subscriber.subscribe(o.request_scheduled, event=CrawlerEvent.REQUEST_SCHEDULED)
            crawler.subscriber.subscribe(o.response_received, event=CrawlerEvent.RESPONSE_RECEIVED)
            crawler.subscriber.subscribe(o.spider_closed, event=CrawlerEvent.SPIDER_CLOSED)
        return o

    async def request_scheduled(self, request: Any, spider: Any) -> None:
        """记录调度的请求"""
        if not self.enabled:
            return
            
        try:
            request_info = {
                'timestamp': datetime.now().isoformat(),
                'type': 'request',
                'url': request.url,
                'method': request.method,
                'headers': dict(request.headers),
                'meta': getattr(request, 'meta', {}),
            }
            
            await self._write_record(request_info)
        except Exception as e:
            self.logger.error(f"Error recording request: {e}")

    async def response_received(self, response: Any, spider: Any) -> None:
        """记录接收到的响应"""
        if not self.enabled:
            return
            
        try:
            response_info = {
                'timestamp': datetime.now().isoformat(),
                'type': 'response',
                'url': response.url,
                'status_code': response.status_code,
                'headers': dict(response.headers),
            }
            
            await self._write_record(response_info)
        except Exception as e:
            self.logger.error(f"Error recording response: {e}")

    async def spider_closed(self, spider: Any) -> None:
        """爬虫关闭时清理资源"""
        if self.current_file:
            self.current_file.close()
            self.current_file = None
        self.logger.info("Request recorder closed.")

    async def _write_record(self, record: dict) -> None:
        """写入记录到文件"""
        # 检查是否需要创建新文件
        if not self.current_file or self.current_file_size > self.max_file_size:
            if self.current_file:
                self.current_file.close()
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(self.output_dir, f'requests_{timestamp}.jsonl')
            self.current_file = open(filename, 'a', encoding='utf-8')
            self.current_file_size = 0
        
        # 写入记录
        line = json.dumps(record, ensure_ascii=False) + '\n'
        self.current_file.write(line)
        self.current_file.flush()
        self.current_file_size += len(line.encode('utf-8'))