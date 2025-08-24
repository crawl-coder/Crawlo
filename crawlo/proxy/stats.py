#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
# @Time    :    2025-08-24 12:11
# @Author  :   crawl-coder
# @Desc    :   None
"""
from typing import Dict


class ProxyStats:
    def __init__(self):
        self.data: Dict[str, Dict[str, int]] = {}

    def record(self, proxy_url: str, event: str):
        if proxy_url not in self.data:
            self.data[proxy_url] = {'success': 0, 'failure': 0, 'total': 0}
        self.data[proxy_url][event] += 1
        self.data[proxy_url]['total'] += 1

    def get(self, proxy_url: str):
        return self.data.get(proxy_url, {'success': 0, 'failure': 0, 'total': 0})

    def all(self):
        return {k: v.copy() for k, v in self.data.items()}