#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
async start_requests 用法示例
==============================
演示 Crawlo 对 async def start_requests 的完整支持。

支持三种签名：
  1. def start_requests(self)         → 同步生成器（原有，向下兼容）
  2. async def start_requests(self)   → 异步生成器（yield）
  3. async def start_requests(self)   → 协程（return 列表）

典型场景：
  - 从数据库/API 异步获取种子 URL 列表
  - 启动时加载远程配置
  - 调用外部服务获取任务队列
"""
import asyncio
from crawlo import Spider, Request


class AsyncStartSpider(Spider):
    """
    展示 async start_requests 的典型用法：
    - 异步获取种子数据
    - 再 yield 请求
    """
    name = 'async_start'

    async def start_requests(self):
        """异步获取种子 URL —— 例如从数据库读取"""
        self.logger.info("正在异步获取种子数据...")

        # 模拟异步操作：从数据库 / Redis / API 获取 URL 列表
        seed_urls = await self._fetch_seed_urls()
        self.logger.info(f"获取到 {len(seed_urls)} 个种子 URL")

        for url in seed_urls:
            yield Request(
                url=url,
                callback=self.parse,
                # 也可以绑定 errback
                # errback=self.on_error,
                meta={'source': 'seed_db'},
            )

    async def _fetch_seed_urls(self):
        """模拟从数据库异步获取 URL"""
        # 实际项目中这里可能是：
        #   result = await db.fetch("SELECT url FROM seed_tasks WHERE status='pending'")
        #   return [row['url'] for row in result]
        await asyncio.sleep(0.01)  # 模拟 I/O
        return [
            'https://httpbin.org/json',
            'https://httpbin.org/ip',
            'https://httpbin.org/uuid',
        ]

    async def parse(self, response):
        self.logger.info(f"处理: {response.url} 状态码={response.status}")


# ============================================================
# 备选方案：直接 return 列表（更简洁，无需 yield）
# ============================================================
class ReturnListSpider(Spider):
    """
    如果不需要逐个 yield，可以直接 return 请求列表。
    框架自动处理。
    """
    name = 'return_list'

    async def start_requests(self):
        urls = await self._load_urls_from_config()
        # 直接 return 列表 —— 框架会内部包装为迭代器
        return [Request(url=u, callback=self.parse) for u in urls]

    async def _load_urls_from_config(self):
        # 模拟从远程配置加载
        return ['https://httpbin.org/json', 'https://httpbin.org/ip']

    async def parse(self, response):
        self.logger.info(f"处理: {response.url}")
