#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
异步日志处理器
用于提高日志写入性能
"""

import asyncio
import logging
import threading
import queue
from typing import Optional
from concurrent_log_handler import ConcurrentRotatingFileHandler


class AsyncLogHandler(logging.Handler):
    """
    异步日志处理器
    将日志记录放入队列中，由后台线程异步处理
    """
    
    def __init__(self, handler: logging.Handler, queue_size: int = 10000):
        """
        初始化异步日志处理器
        
        Args:
            handler: 实际的日志处理器
            queue_size: 队列大小
        """
        super().__init__()
        self._handler = handler
        self._queue = queue.Queue(maxsize=queue_size)
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._started = False
        
    def start(self):
        """启动异步处理线程"""
        if self._started:
            return
            
        self._started = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        
    def stop(self):
        """停止异步处理线程"""
        if not self._started:
            return
            
        self._started = False
        self._stop_event.set()
        
        # 发送一个哨兵消息来唤醒工作线程
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
            
        # 等待线程结束
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
            
        # 关闭底层处理器
        if self._handler:
            self._handler.close()
            
    def _worker(self):
        """工作线程函数"""
        while not self._stop_event.is_set():
            try:
                # 从队列中获取日志记录
                record = self._queue.get(timeout=1.0)
                
                # 哨兵消息，表示停止
                if record is None:
                    break
                    
                # 处理日志记录
                try:
                    self._handler.emit(record)
                except Exception:
                    pass  # 忽略处理错误
                    
                self._queue.task_done()
                
            except queue.Empty:
                continue
            except Exception:
                if not self._stop_event.is_set():
                    continue
                else:
                    break
                    
    def emit(self, record):
        """
        发出日志记录
        
        Args:
            record: 日志记录
        """
        if not self._started:
            self.start()
            
        # 将日志记录放入队列
        try:
            self._queue.put_nowait(record)
        except queue.Full:
            # 队列满时丢弃日志记录
            pass
            
    def flush(self):
        """刷新日志处理器"""
        if self._handler:
            self._handler.flush()
            
    def close(self):
        """关闭日志处理器"""
        self.stop()
        super().close()


class AsyncConcurrentRotatingFileHandler(AsyncLogHandler):
    """
    异步并发轮转文件处理器
    结合了异步处理和并发轮转文件的功能
    """
    
    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0, 
                 encoding=None, delay=False, queue_size: int = 10000):
        """
        初始化异步并发轮转文件处理器
        
        Args:
            filename: 日志文件名
            mode: 文件打开模式
            maxBytes: 最大文件大小
            backupCount: 备份文件数量
            encoding: 文件编码
            delay: 是否延迟打开文件
            queue_size: 队列大小
        """
        handler = ConcurrentRotatingFileHandler(
            filename=filename,
            mode=mode,
            maxBytes=maxBytes,
            backupCount=backupCount,
            encoding=encoding,
            delay=delay
        )
        super().__init__(handler, queue_size)
        
    @property
    def baseFilename(self):
        """获取基础文件名"""
        return self._handler.baseFilename if self._handler else None
        
    @property
    def maxBytes(self):
        """获取最大字节数"""
        return self._handler.maxBytes if self._handler else 0
        
    @property
    def backupCount(self):
        """获取备份计数"""
        return self._handler.backupCount if self._handler else 0


def wrap_handler_async(handler: logging.Handler, queue_size: int = 10000) -> AsyncLogHandler:
    """
    将现有的日志处理器包装为异步处理器
    
    Args:
        handler: 要包装的日志处理器
        queue_size: 队列大小
        
    Returns:
        异步日志处理器
    """
    return AsyncLogHandler(handler, queue_size)