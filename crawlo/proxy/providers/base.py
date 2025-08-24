#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
# @Time    :    2025-08-24 12:12
# @Author  :   crawl-coder
# @Desc    :   None
"""
from typing import List
from abc import ABC, abstractmethod


class BaseProxyProvider(ABC):
    """
    代理提供者抽象基类
    所有代理来源必须继承此类
    """

    @abstractmethod
    async def fetch_proxies(self) -> List[str]:
        """
        返回代理 URL 列表，格式如：
        ['http://ip:port', 'https://u:p@ip:port', 'socks5://...']
        """
        pass

    def __str__(self):
        return f"{self.__class__.__name__}()"
