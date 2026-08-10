# -*- coding: UTF-8 -*-
"""
整站抓取 Spider：列表页 → 分页 → 详情页 → Item。

要点（教程逐节讲解）：
1. 列表页解析产品链接 + 下一页链接（响应式选择器）；
2. 请求去重由框架自带 dupefilter 处理；
3. 详情页数据 + 列表页摘要合并成 CatalogItem；
4. 选择器带 adaptive=True，网站改版时自愈（见 docs/guides/adaptive-selector.md）。
"""

import os

from crawlo.http import Request
from crawlo.items import Item
from crawlo.spider import Spider

from real_world_catalog.items import CatalogItem


class CatalogSpider(Spider):
    name = "catalog"

    # 演示/生产目标：生产环境用真实站点，本地演示用 demo_server.py 起的 mock 站。
    # 注意：start_urls 在 __init__ / start_requests 中运行时构建，
    # 避免类定义期固化（环境变量在导入后设置时失效）。
    start_urls: list = []

    custom_settings = {
        "MAX_PAGES": int(os.environ.get("CATALOG_MAX_PAGES", "5")),
        "ROBOTSTXT_OBEY": False,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_url = os.environ.get("CATALOG_BASE_URL", "http://127.0.0.1:9000")
        self.base_url = base_url
        self.start_urls = [f"{base_url}/catalog?page=1"]

    def parse(self, response):
        """列表页：提取产品链接 + 下一页链接。"""
        max_pages = 5
        if self.crawler and self.crawler.settings:
            max_pages = self.crawler.settings.get("MAX_PAGES", 5)

        # 1) 产品详情链接
        for href in response.css("a.product-link::attr(href)").getall():
            yield Request(
                url=response.urljoin(href),
                callback=self.parse_detail,
                meta={"listing_summary": self._extract_listing_summary(response)},
            )

        # 2) 下一页（分页）——用 adaptive 选择器演示改版自愈
        next_href = response.css(
            "a.pagination-link.next::attr(href)",
            adaptive=True,
            identifier="catalog_next_page",
        ).get()
        if next_href and response.meta.get("page", 1) < max_pages:
            yield Request(
                url=response.urljoin(next_href),
                callback=self.parse,
                meta={"page": response.meta.get("page", 1) + 1},
                dont_filter=False,
            )

    def parse_detail(self, response):
        """详情页：合并列表页摘要 + 详情字段 → CatalogItem。"""
        summary = response.meta.get("listing_summary") or {}
        item = CatalogItem(
            url=response.url,
            title=response.css("h1.product-title::text").get("").strip() or summary.get("title", ""),
            price=response.css(".product-price::text").get("").strip() or summary.get("price", ""),
            category=summary.get("category", ""),
            description=response.css(".product-description::text").get("").strip(),
            sku=response.css(".product-sku::text").get("").strip(),
            in_stock=response.css(".stock-status.in-stock").get() is not None,
        )
        return item

    def _extract_listing_summary(self, response):
        """列表页卡片上已展示的摘要字段（减少详情页请求压力时可复用）。"""
        return {
            "title": response.css(".product-title::text").get("").strip(),
            "price": response.css(".product-price::text").get("").strip(),
            "category": response.css(".product-category::text").get("").strip(),
        }
