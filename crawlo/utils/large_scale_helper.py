#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
大规模爬虫优化辅助工具
"""
import asyncio
import json
import time
from typing import Generator, List, Dict, Any

from crawlo.logging import get_logger


class LargeScaleHelper:
    """大规模爬虫辅助类"""
    
    def __init__(self, batch_size: int = 1000, checkpoint_interval: int = 5000):
        self.batch_size = batch_size
        self.checkpoint_interval = checkpoint_interval
        self.logger = get_logger(self.__class__.__name__)
        
    def batch_iterator(self, data_source, start_offset: int = 0) -> Generator[List[Any], None, None]:
        """
        批量迭代器，适用于大量数据的分批处理
        
        Args:
            data_source: 数据源（支持多种类型）
            start_offset: 起始偏移量
            
        Yields:
            每批数据的列表
        """
        if hasattr(data_source, '__iter__') and not isinstance(data_source, (str, bytes)):
            # 可迭代对象
            yield from self._iterate_batches(data_source, start_offset)
        elif hasattr(data_source, 'get_batch'):
            # 支持分批获取的数据源
            yield from self._get_batches_from_source(data_source, start_offset)
        elif callable(data_source):
            # 函数形式的数据源
            yield from self._get_batches_from_function(data_source, start_offset)
        else:
            raise ValueError(f"不支持的数据源类型: {type(data_source)}")
    
    def _iterate_batches(self, iterable, start_offset: int) -> Generator[List[Any], None, None]:
        """从可迭代对象分批获取数据"""
        iterator = iter(iterable)
        
        # 跳过已处理的数据
        for _ in range(start_offset):
            try:
                next(iterator)
            except StopIteration:
                return
        
        while True:
            batch = []
            for _ in range(self.batch_size):
                try:
                    batch.append(next(iterator))
                except StopIteration:
                    if batch:
                        yield batch
                    return
            
            if batch:
                yield batch
    
    def _get_batches_from_source(self, data_source, start_offset: int) -> Generator[List[Any], None, None]:
        """从支持分批获取的数据源获取数据"""
        offset = start_offset
        
        while True:
            try:
                batch = data_source.get_batch(offset, self.batch_size)
                if not batch:
                    break
                
                yield batch
                offset += len(batch)
                
                if len(batch) < self.batch_size:
                    break  # 已到达数据末尾
                    
            except Exception as e:
                self.logger.error(f"获取批次数据失败: {e}")
                break
    
    def _get_batches_from_function(self, func, start_offset: int) -> Generator[List[Any], None, None]:
        """从函数获取批次数据"""
        offset = start_offset
        
        while True:
            try:
                batch = func(offset, self.batch_size)
                if not batch:
                    break
                
                yield batch
                offset += len(batch)
                
                if len(batch) < self.batch_size:
                    break
                    
            except Exception as e:
                self.logger.error(f"函数获取数据失败: {e}")
                break


class ProgressManager:
    """进度管理器"""
    
    def __init__(self, progress_file: str = "spider_progress.json"):
        self.progress_file = progress_file
        self.logger = get_logger(self.__class__.__name__)
        
    def load_progress(self) -> Dict[str, Any]:
        """加载进度"""
        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                progress = json.load(f)
                self.logger.info(f"加载进度: {progress}")
                return progress
        except FileNotFoundError:
            self.logger.info("📄 未找到进度文件，从头开始")
            return self._get_default_progress()
        except Exception as e:
            self.logger.error(f"加载进度失败: {e}")
            return self._get_default_progress()
    
    def save_progress(self, **kwargs):
        """保存进度"""
        try:
            progress = {
                **kwargs,
                'timestamp': time.time(),
                'formatted_time': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress, f, indent=2, ensure_ascii=False)
                
            self.logger.debug(f"💾 已保存进度: {progress}")
            
        except Exception as e:
            self.logger.error(f"保存进度失败: {e}")
    
    def _get_default_progress(self) -> Dict[str, Any]:
        """获取默认进度"""
        return {
            'batch_num': 0,
            'processed_count': 0,
            'skipped_count': 0,
            'timestamp': time.time()
        }


class MemoryOptimizer:
    """内存优化器"""
    
    def __init__(self, max_memory_mb: int = 500):
        self.max_memory_mb = max_memory_mb
        self.logger = get_logger(self.__class__.__name__)
        
    def check_memory_usage(self) -> Dict[str, float]:
        """检查内存使用情况"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            memory_mb = memory_info.rss / 1024 / 1024
            memory_percent = process.memory_percent()
            
            return {
                'memory_mb': memory_mb,
                'memory_percent': memory_percent,
                'threshold_mb': self.max_memory_mb
            }
        except ImportError:
            self.logger.warning("psutil 未安装，无法监控内存")
            return {}
        except Exception as e:
            self.logger.error(f"检查内存失败: {e}")
            return {}
    
    def should_pause_for_memory(self) -> bool:
        """检查是否应该因内存不足而暂停"""
        memory_info = self.check_memory_usage()
        
        if not memory_info:
            return False
            
        memory_mb = memory_info.get('memory_mb', 0)
        
        if memory_mb > self.max_memory_mb:
            self.logger.warning(f"内存使用过高: {memory_mb:.1f}MB > {self.max_memory_mb}MB")
            return True
            
        return False
    
    def force_garbage_collection(self):
        """强制垃圾回收"""
        try:
            import gc
            collected = gc.collect()
            self.logger.debug(f"垃圾回收: 清理了 {collected} 个对象")
        except Exception as e:
            self.logger.error(f"垃圾回收失败: {e}")


class DataSourceAdapter:
    """数据源适配器"""
    
    @staticmethod
    def from_redis_queue(queue, batch_size: int = 1000):
        """从Redis队列创建批量数据源"""
        def get_batch(offset: int, limit: int) -> List[Dict]:
            try:
                # 如果队列支持范围查询
                if hasattr(queue, 'get_range'):
                    return queue.get_range(offset, offset + limit - 1)
                
                # 如果队列支持批量获取
                if hasattr(queue, 'get_batch'):
                    return queue.get_batch(offset, limit)
                
                # 模拟批量获取
                results = []
                for _ in range(limit):
                    item = queue.get_nowait() if hasattr(queue, 'get_nowait') else None
                    if item:
                        results.append(item)
                    else:
                        break
                
                return results
                
            except Exception as e:
                print(f"获取批次失败: {e}")
                return []
        
        return get_batch
    
    @staticmethod
    def from_database(db_helper, query: str, batch_size: int = 1000):
        """从数据库创建批量数据源"""
        def get_batch(offset: int, limit: int) -> List[Dict]:
            try:
                # 添加分页查询
                paginated_query = f"{query} LIMIT {limit} OFFSET {offset}"
                return db_helper.execute_query(paginated_query)
            except Exception as e:
                print(f"数据库查询失败: {e}")
                return []
        
        return get_batch
    
    @staticmethod
    def from_file(file_path: str, batch_size: int = 1000):
        """从文件创建批量数据源"""
        def get_batch(offset: int, limit: int) -> List[str]:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    # 跳过已处理的行
                    for _ in range(offset):
                        f.readline()
                    
                    # 读取当前批次
                    batch = []
                    for _ in range(limit):
                        line = f.readline()
                        if not line:
                            break
                        batch.append(line.strip())
                    
                    return batch
            except Exception as e:
                print(f"读取文件失败: {e}")
                return []
        
        return get_batch


class LargeScaleSpiderMixin:
    """大规模爬虫混入类"""
    
    def __init__(self):
        super().__init__()
        self.large_scale_helper = LargeScaleHelper(
            batch_size=getattr(self, 'batch_size', 1000),
            checkpoint_interval=getattr(self, 'checkpoint_interval', 5000)
        )
        self.progress_manager = ProgressManager(
            progress_file=getattr(self, 'progress_file', f"{self.name}_progress.json")
        )
        self.memory_optimizer = MemoryOptimizer(
            max_memory_mb=getattr(self, 'max_memory_mb', 500)
        )
        
    def create_streaming_start_requests(self, data_source):
        """创建流式start_requests生成器"""
        progress = self.progress_manager.load_progress()
        start_offset = progress.get('processed_count', 0)
        
        processed_count = start_offset
        skipped_count = progress.get('skipped_count', 0)
        
        for batch in self.large_scale_helper.batch_iterator(data_source, start_offset):
            
            # 内存检查
            if self.memory_optimizer.should_pause_for_memory():
                self.memory_optimizer.force_garbage_collection()
                # 可以添加延迟或其他处理
                asyncio.sleep(1)
            
            for item in batch:
                processed_count += 1
                
                # 检查进度保存
                if processed_count % self.large_scale_helper.checkpoint_interval == 0:
                    self.progress_manager.save_progress(
                        processed_count=processed_count,
                        skipped_count=skipped_count
                    )
                
                # 生成请求
                request = self.create_request_from_item(item)
                if request:
                    yield request
                else:
                    skipped_count += 1
        
        # 最终保存进度
        self.progress_manager.save_progress(
            processed_count=processed_count,
            skipped_count=skipped_count,
            completed=True
        )
        
        self.logger.info(f"处理完成！总计: {processed_count}, 跳过: {skipped_count}")
    
    def create_request_from_item(self, item):
        """从数据项创建请求（需要子类实现）"""
        raise NotImplementedError("子类必须实现 create_request_from_item 方法")