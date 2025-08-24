#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
# @Time    :    2025-08-24 12:13
# @Author  :   crawl-coder
# @Desc    :   None
"""
from typing import List
from .base import BaseProxyProvider


class FileProxyProvider(BaseProxyProvider):
    """从本地文件读取代理（每行一个）"""
    def __init__(self, filepath: str):
        self.filepath = filepath

    async def fetch_proxies(self) -> List[str]:
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        except Exception as e:
            print(f"[FileProxyProvider] 读取失败 {self.filepath}: {e}")
            return []