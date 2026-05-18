# -*- coding: utf-8 -*-
"""
===================================
消息去重管理器
===================================

提供消息去重功能，防止重复发送相同内容的消息。
"""

import hashlib
import time
from typing import Dict, Set, Optional
from threading import Lock

from crawlo.logging import get_logger


class MessageDeduplicator:
    """
    消息去重管理器
    
    使用消息内容的哈希值来判断是否为重复消息，
    并提供时间窗口来控制重复消息的过滤。
    """
    
    def __init__(self, time_window: int = 300, max_size: int = 10000):  # 默认5分钟时间窗口，最大10000条记录
        """
        初始化去重管理器
        
        Args:
            time_window: 时间窗口（秒），在此时间内相同的
                        消息将被视为重复
            max_size: 最大记录数，防止内存无限增长
        """
        self.time_window = time_window
        self.max_size = max_size
        self._seen_messages: Dict[str, float] = {}  # 存储消息哈希和时间戳
        self._lock = Lock()  # 线程锁
        self.logger = get_logger(__name__)
    
    def _generate_message_hash(self, title: str, content: str, channel: str) -> str:
        """
        生成消息的唯一哈希值
        
        Args:
            title: 消息标题
            content: 消息内容
            channel: 消息渠道
            
        Returns:
            消息哈希值
        """
        # 将标题、内容和渠道组合起来生成哈希
        message_str = f"{title}||{content}||{channel}"
        return hashlib.sha256(message_str.encode('utf-8')).hexdigest()
    
    def is_duplicate(self, title: str, content: str, channel: str) -> bool:
        """
        检查消息是否为重复消息
        
        Args:
            title: 消息标题
            content: 消息内容
            channel: 消息渠道
            
        Returns:
            是否为重复消息
        """
        message_hash = self._generate_message_hash(title, content, channel)
        current_time = time.time()
        
        with self._lock:
            # 清理过期的消息记录
            self._cleanup_expired_messages(current_time)
            
            # 检查消息是否已存在且在时间窗口内
            if message_hash in self._seen_messages:
                last_seen = self._seen_messages[message_hash]
                if current_time - last_seen <= self.time_window:
                    return True
                else:
                    # 消息已过期，更新时间戳
                    self._seen_messages[message_hash] = current_time
                    return False
            else:
                # 新消息，检查容量限制
                if len(self._seen_messages) >= self.max_size:
                    # 达到容量限制，执行紧急清理（只保留最近的 80%）
                    self._emergency_cleanup()
                
                # 记录时间戳
                self._seen_messages[message_hash] = current_time
                return False
    
    def _cleanup_expired_messages(self, current_time: float) -> None:
        """
        清理过期的消息记录
        
        Args:
            current_time: 当前时间戳
        """
        expired_hashes = []
        for message_hash, timestamp in self._seen_messages.items():
            if current_time - timestamp > self.time_window:
                expired_hashes.append(message_hash)
        
        for message_hash in expired_hashes:
            del self._seen_messages[message_hash]
    
    def _emergency_cleanup(self) -> None:
        """
        紧急清理：当达到容量限制时，保留最近的 80% 记录
        按时间戳排序，删除最旧的 20%
        """
        if not self._seen_messages:
            return
        
        # 按时间戳排序
        sorted_items = sorted(self._seen_messages.items(), key=lambda x: x[1])
        
        # 删除最旧的 20%
        remove_count = int(len(sorted_items) * 0.2)
        for i in range(remove_count):
            del self._seen_messages[sorted_items[i][0]]
        
        self.logger.debug(
            f"[Deduplicator] 紧急清理：删除 {remove_count} 条最旧记录，"
            f"剩余 {len(self._seen_messages)} 条"
        )
    
    def add_message(self, title: str, content: str, channel: str) -> None:
        """
        手动添加消息到去重记录中
        
        Args:
            title: 消息标题
            content: 消息内容
            channel: 消息渠道
        """
        message_hash = self._generate_message_hash(title, content, channel)
        current_time = time.time()
        
        with self._lock:
            self._seen_messages[message_hash] = current_time
    
    def clear_history(self) -> None:
        """清空所有历史记录"""
        with self._lock:
            self._seen_messages.clear()


def get_deduplicator(time_window: int = 300) -> MessageDeduplicator:
    """
    获取全局去重器实例（存储于 ApplicationContext，DCL 线程安全）
    """
    from crawlo.core.application import get_global_context
    ctx = get_global_context()
    
    if ctx.deduplicator is None:
        with ctx.deduplicator_lock:
            if ctx.deduplicator is None:
                ctx.deduplicator = MessageDeduplicator(time_window)
    
    return ctx.deduplicator


def reset_deduplicator() -> None:
    """重置全局去重器（主要用于测试）"""
    from crawlo.core.application import get_global_context
    ctx = get_global_context()
    ctx.deduplicator = None