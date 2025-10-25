#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Crawlo 事件系统
==============
定义框架中的所有事件类型，支持类型安全和IDE自动补全。
"""
from enum import Enum


class CrawlerEvent(str, Enum):
    """
    爬虫事件枚举
    
    所有事件都应该使用此枚举类型，以获得：
    - 类型安全：避免拼写错误
    - IDE支持：自动补全和提示
    - 文档化：集中管理所有事件
    
    使用示例：
        >>> from crawlo.event import CrawlerEvent
        >>> await subscriber.notify(CrawlerEvent.SPIDER_OPENED, spider)
    """
    
    # 爬虫生命周期事件
    SPIDER_OPENED = "spider_opened"      # 爬虫启动
    SPIDER_CLOSED = "spider_closed"      # 爬虫关闭
    SPIDER_ERROR = "spider_error"        # 爬虫错误
    
    # 请求相关事件
    REQUEST_SCHEDULED = "request_scheduled"  # 请求已调度
    IGNORE_REQUEST = "ignore_request"        # 请求被忽略
    
    # 响应相关事件
    RESPONSE_RECEIVED = "response_received"  # 响应已接收
    
    # Item相关事件
    ITEM_SUCCESSFUL = "item_successful"  # Item处理成功
    ITEM_DISCARD = "item_discard"        # Item被丢弃


# 导出所有公共API
__all__ = [
    'CrawlerEvent',
]
