# -*- coding: utf-8 -*-
import json
import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime
from crawlo.logging import get_logger
from crawlo.exceptions import ItemDiscard


class JsonPipeline:
    """JSON文件输出管道"""
    
    def __init__(self, crawler):
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__)
        
        # 配置文件路径
        self.file_path = self._get_file_path()
        self.file_handle = None
        self.lock = asyncio.Lock()  # 异步锁保证线程安全
        
        # 注册关闭事件
        crawler.subscriber.subscribe(self.spider_closed, event='spider_closed')
        
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)
    
    def _get_file_path(self) -> Path:
        """获取输出文件路径"""
        # 优先级：设置 > 爬虫属性 > 默认路径
        file_path = (
            self.settings.get('JSON_FILE') or
            getattr(self.crawler.spider, 'json_file', None) or
            f"output/{self.crawler.spider.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    
    async def _ensure_file_open(self):
        """确保文件已打开"""
        if self.file_handle is None:
            self.file_handle = open(self.file_path, 'w', encoding='utf-8')
            self.logger.info(f"JSON文件已创建: {self.file_path}")
    
    async def process_item(self, item, spider) -> Optional[dict]:
        """处理item的核心方法"""
        try:
            async with self.lock:
                await self._ensure_file_open()
                
                # 转换为字典并序列化
                item_dict = dict(item)
                json_line = json.dumps(item_dict, ensure_ascii=False, indent=None)
                
                # 写入文件（每行一个JSON对象）
                self.file_handle.write(json_line + '\n')
                self.file_handle.flush()  # 立即刷新到磁盘
                
                # 统计
                self.crawler.stats.inc_value('json_pipeline/items_written')
                self.logger.debug(f"写入JSON项: {len(item_dict)} 字段")
                
            return item
            
        except Exception as e:
            self.crawler.stats.inc_value('json_pipeline/items_failed')
            self.logger.error(f"JSON写入失败: {e}")
            raise ItemDiscard(f"JSON Pipeline处理失败: {e}")
    
    async def spider_closed(self):
        """关闭爬虫时清理资源"""
        if self.file_handle:
            self.file_handle.close()
            self.logger.info(f"JSON文件已关闭: {self.file_path}")


class JsonLinesPipeline:
    """JSON Lines格式输出管道（每行一个JSON对象）"""
    
    def __init__(self, crawler):
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__)
        
        self.file_path = self._get_file_path()
        self.file_handle = None
        self.items_count = 0
        self.lock = asyncio.Lock()
        
        crawler.subscriber.subscribe(self.spider_closed, event='spider_closed')
        
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)
    
    def _get_file_path(self) -> Path:
        """获取输出文件路径"""
        file_path = (
            self.settings.get('JSONLINES_FILE') or
            getattr(self.crawler.spider, 'jsonlines_file', None) or
            f"output/{self.crawler.spider.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        )
        
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    
    async def _ensure_file_open(self):
        """确保文件已打开"""
        if self.file_handle is None:
            self.file_handle = open(self.file_path, 'w', encoding='utf-8')
            self.logger.info(f"JSONL文件已创建: {self.file_path}")
    
    async def process_item(self, item, spider) -> Optional[dict]:
        """处理item方法"""
        try:
            async with self.lock:
                await self._ensure_file_open()
                
                item_dict = dict(item)
                
                # 添加元数据
                if self.settings.get_bool('JSON_ADD_METADATA', False):
                    item_dict['_crawl_time'] = datetime.now().isoformat()
                    item_dict['_spider_name'] = spider.name
                
                # 写入JSONL格式
                json_line = json.dumps(item_dict, ensure_ascii=False, separators=(',', ':'))
                self.file_handle.write(json_line + '\n')
                self.file_handle.flush()
                
                self.items_count += 1
                
                # 定期日志输出
                if self.items_count % 100 == 0:
                    self.logger.info(f"已写入 {self.items_count} 个JSON对象")
                
                self.crawler.stats.inc_value('jsonlines_pipeline/items_written')
                
            return item
            
        except Exception as e:
            self.crawler.stats.inc_value('jsonlines_pipeline/items_failed')
            self.logger.error(f"JSONL写入失败: {e}")
            raise ItemDiscard(f"JSON Lines Pipeline处理失败: {e}")
    
    async def spider_closed(self):
        """资源清理"""
        if self.file_handle:
            self.file_handle.close()
            self.logger.info(f"JSONL文件已关闭，共写入 {self.items_count} 个项目: {self.file_path}")


class JsonArrayPipeline:
    """JSON数组格式输出管道（所有item组成一个JSON数组）"""
    
    def __init__(self, crawler):
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__)
        
        self.file_path = self._get_file_path()
        self.items = []  # 内存中暂存所有items
        self.lock = asyncio.Lock()
        
        crawler.subscriber.subscribe(self.spider_closed, event='spider_closed')
        
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)
    
    def _get_file_path(self) -> Path:
        """获取输出文件路径"""
        file_path = (
            self.settings.get('JSON_ARRAY_FILE') or
            getattr(self.crawler.spider, 'json_array_file', None) or
            f"output/{self.crawler.spider.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_array.json"
        )
        
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    
    async def process_item(self, item, spider) -> Optional[dict]:
        """处理item方法"""
        try:
            async with self.lock:
                item_dict = dict(item)
                self.items.append(item_dict)
                
                self.crawler.stats.inc_value('json_array_pipeline/items_collected')
                self.logger.debug(f"收集item，当前总数: {len(self.items)}")
                
            return item
            
        except Exception as e:
            self.crawler.stats.inc_value('json_array_pipeline/items_failed')
            self.logger.error(f"JSON Array收集失败: {e}")
            raise ItemDiscard(f"JSON Array Pipeline处理失败: {e}")
    
    async def spider_closed(self):
        """关闭时写入所有items到JSON数组文件"""
        try:
            if self.items:
                with open(self.file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.items, f, ensure_ascii=False, indent=2)
                
                self.logger.info(f"JSON数组文件已保存，包含 {len(self.items)} 个项目: {self.file_path}")
                self.crawler.stats.set_value('json_array_pipeline/total_items', len(self.items))
            else:
                self.logger.warning("没有items需要保存")
                
        except Exception as e:
            self.logger.error(f"保存JSON数组文件失败: {e}")