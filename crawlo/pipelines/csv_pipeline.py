# -*- coding: utf-8 -*-
import csv
import asyncio
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from crawlo.logging import get_logger
from crawlo.exceptions import ItemDiscard


class CsvPipeline:
    """CSV文件输出管道"""
    
    def __init__(self, crawler):
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__)
        
        # 配置文件路径
        self.file_path = self._get_file_path()
        self.file_handle = None
        self.csv_writer = None
        self.headers_written = False
        self.lock = asyncio.Lock()  # 异步锁保证线程安全
        
        # CSV配置
        self.delimiter = self.settings.get('CSV_DELIMITER', ',')
        self.quotechar = self.settings.get('CSV_QUOTECHAR', '"')
        self.include_headers = self.settings.get_bool('CSV_INCLUDE_HEADERS', True)
        
        # 注册关闭事件
        crawler.subscriber.subscribe(self.spider_closed, event='spider_closed')
        
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)
    
    def _get_file_path(self) -> Path:
        """获取输出文件路径"""
        file_path = (
            self.settings.get('CSV_FILE') or
            getattr(self.crawler.spider, 'csv_file', None) or
            f"output/{self.crawler.spider.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    
    async def _ensure_file_open(self):
        """确保文件已打开"""
        if self.file_handle is None:
            self.file_handle = open(self.file_path, 'w', newline='', encoding='utf-8')
            self.csv_writer = csv.writer(
                self.file_handle,
                delimiter=self.delimiter,
                quotechar=self.quotechar,
                quoting=csv.QUOTE_MINIMAL
            )
            self.logger.info(f"CSV文件已创建: {self.file_path}")
    
    async def _write_headers(self, item_dict: dict):
        """写入CSV表头"""
        if not self.headers_written and self.include_headers:
            headers = list(item_dict.keys())
            self.csv_writer.writerow(headers)
            self.headers_written = True
            self.logger.debug(f"CSV表头已写入: {headers}")
    
    async def process_item(self, item, spider) -> Optional[dict]:
        """处理item的核心方法"""
        try:
            async with self.lock:
                await self._ensure_file_open()
                
                # 转换为字典
                item_dict = dict(item)
                
                # 写入表头（仅第一次）
                await self._write_headers(item_dict)
                
                # 写入数据行
                values = [str(v) if v is not None else '' for v in item_dict.values()]
                self.csv_writer.writerow(values)
                self.file_handle.flush()  # 立即刷新到磁盘
                
                # 统计
                self.crawler.stats.inc_value('csv_pipeline/items_written')
                self.logger.debug(f"写入CSV行: {len(item_dict)} 字段")
                
            return item
            
        except Exception as e:
            self.crawler.stats.inc_value('csv_pipeline/items_failed')
            self.logger.error(f"CSV写入失败: {e}")
            raise ItemDiscard(f"CSV Pipeline处理失败: {e}")
    
    async def spider_closed(self):
        """关闭爬虫时清理资源"""
        if self.file_handle:
            self.file_handle.close()
            self.logger.info(f"CSV文件已关闭: {self.file_path}")


class CsvDictPipeline:
    """CSV字典写入器管道（使用DictWriter，支持字段映射）"""
    
    def __init__(self, crawler):
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__)
        
        self.file_path = self._get_file_path()
        self.file_handle = None
        self.csv_writer = None
        self.fieldnames = None
        self.headers_written = False
        self.lock = asyncio.Lock()
        
        # 配置选项
        self.delimiter = self.settings.get('CSV_DELIMITER', ',')
        self.quotechar = self.settings.get('CSV_QUOTECHAR', '"')
        self.include_headers = self.settings.get_bool('CSV_INCLUDE_HEADERS', True)
        self.extrasaction = self.settings.get('CSV_EXTRASACTION', 'ignore')  # ignore, raise
        
        crawler.subscriber.subscribe(self.spider_closed, event='spider_closed')
        
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)
    
    def _get_file_path(self) -> Path:
        """获取输出文件路径"""
        file_path = (
            self.settings.get('CSV_DICT_FILE') or
            getattr(self.crawler.spider, 'csv_dict_file', None) or
            f"output/{self.crawler.spider.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_dict.csv"
        )
        
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    
    def _get_fieldnames(self, item_dict: dict) -> List[str]:
        """获取字段名列表"""
        # 优先使用配置的字段名
        configured_fields = self.settings.get('CSV_FIELDNAMES')
        if configured_fields:
            return configured_fields if isinstance(configured_fields, list) else configured_fields.split(',')
        
        # 使用爬虫定义的字段名
        spider_fields = getattr(self.crawler.spider, 'csv_fieldnames', None)
        if spider_fields:
            return spider_fields if isinstance(spider_fields, list) else spider_fields.split(',')
        
        # 使用item的字段名
        return list(item_dict.keys())
    
    async def _ensure_file_open(self, item_dict: dict):
        """确保文件已打开"""
        if self.file_handle is None:
            self.fieldnames = self._get_fieldnames(item_dict)
            
            self.file_handle = open(self.file_path, 'w', newline='', encoding='utf-8')
            self.csv_writer = csv.DictWriter(
                self.file_handle,
                fieldnames=self.fieldnames,
                delimiter=self.delimiter,
                quotechar=self.quotechar,
                quoting=csv.QUOTE_MINIMAL,
                extrasaction=self.extrasaction
            )
            
            # 写入表头
            if self.include_headers:
                self.csv_writer.writeheader()
                self.headers_written = True
            
            self.logger.info(f"CSV字典文件已创建: {self.file_path}，字段: {self.fieldnames}")
    
    async def process_item(self, item, spider) -> Optional[dict]:
        """处理item方法"""
        try:
            async with self.lock:
                item_dict = dict(item)
                await self._ensure_file_open(item_dict)
                
                # 写入数据行
                self.csv_writer.writerow(item_dict)
                self.file_handle.flush()
                
                self.crawler.stats.inc_value('csv_dict_pipeline/items_written')
                self.logger.debug(f"写入CSV字典行，字段数: {len(item_dict)}")
                
            return item
            
        except Exception as e:
            self.crawler.stats.inc_value('csv_dict_pipeline/items_failed')
            self.logger.error(f"CSV字典写入失败: {e}")
            raise ItemDiscard(f"CSV Dict Pipeline处理失败: {e}")
    
    async def spider_closed(self):
        """资源清理"""
        if self.file_handle:
            self.file_handle.close()
            self.logger.info(f"CSV字典文件已关闭: {self.file_path}")


class CsvBatchPipeline:
    """CSV批量写入管道（内存缓存，批量写入，提高性能）"""
    
    def __init__(self, crawler):
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__)
        
        self.file_path = self._get_file_path()
        self.file_handle = None
        self.csv_writer = None
        self.batch_buffer = []
        self.headers_written = False
        self.lock = asyncio.Lock()
        
        # 批量配置
        self.batch_size = self.settings.get_int('CSV_BATCH_SIZE', 100)
        self.delimiter = self.settings.get('CSV_DELIMITER', ',')
        self.quotechar = self.settings.get('CSV_QUOTECHAR', '"')
        self.include_headers = self.settings.get_bool('CSV_INCLUDE_HEADERS', True)
        
        crawler.subscriber.subscribe(self.spider_closed, event='spider_closed')
        
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)
    
    def _get_file_path(self) -> Path:
        """获取输出文件路径"""
        file_path = (
            self.settings.get('CSV_BATCH_FILE') or
            getattr(self.crawler.spider, 'csv_batch_file', None) or
            f"output/{self.crawler.spider.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_batch.csv"
        )
        
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    
    async def _ensure_file_open(self):
        """确保文件已打开"""
        if self.file_handle is None:
            self.file_handle = open(self.file_path, 'w', newline='', encoding='utf-8')
            self.csv_writer = csv.writer(
                self.file_handle,
                delimiter=self.delimiter,
                quotechar=self.quotechar,
                quoting=csv.QUOTE_MINIMAL
            )
            self.logger.info(f"CSV批量文件已创建: {self.file_path}")
    
    async def _flush_batch(self):
        """刷新批量缓存到文件"""
        if not self.batch_buffer:
            return
        
        await self._ensure_file_open()
        
        for row in self.batch_buffer:
            self.csv_writer.writerow(row)
        
        self.file_handle.flush()
        items_count = len(self.batch_buffer)
        self.batch_buffer.clear()
        
        self.crawler.stats.inc_value('csv_batch_pipeline/batches_written')
        self.crawler.stats.inc_value('csv_batch_pipeline/items_written', count=items_count)
        self.logger.info(f"批量写入 {items_count} 行到CSV文件")
    
    async def process_item(self, item, spider) -> Optional[dict]:
        """处理item方法"""
        try:
            async with self.lock:
                item_dict = dict(item)
                
                # 写入表头（仅第一次）
                if not self.headers_written and self.include_headers:
                    headers = list(item_dict.keys())
                    self.batch_buffer.append(headers)
                    self.headers_written = True
                
                # 添加数据到缓存
                values = [str(v) if v is not None else '' for v in item_dict.values()]
                self.batch_buffer.append(values)
                
                # 检查是否需要刷新批量缓存
                if len(self.batch_buffer) >= self.batch_size:
                    await self._flush_batch()
                
            return item
            
        except Exception as e:
            self.crawler.stats.inc_value('csv_batch_pipeline/items_failed')
            self.logger.error(f"CSV批量处理失败: {e}")
            raise ItemDiscard(f"CSV Batch Pipeline处理失败: {e}")
    
    async def spider_closed(self):
        """关闭时刷新剩余缓存"""
        try:
            # 刷新剩余的批量数据
            async with self.lock:
                await self._flush_batch()
            
            if self.file_handle:
                self.file_handle.close()
                self.logger.info(f"CSV批量文件已关闭: {self.file_path}")
                
        except Exception as e:
            self.logger.error(f"关闭CSV批量管道时出错: {e}")