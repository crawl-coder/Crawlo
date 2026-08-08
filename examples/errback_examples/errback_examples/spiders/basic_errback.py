#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
基础 errback 用法示例
=====================

演示：
1. 直接绑定 errback 方法（无需工厂函数/闭包）
2. Failure 对象的使用：value / type / check() / getTraceback()
3. errback 中返回 Item（错误日志）和 Request（重试）
"""
from crawlo import Spider, Request, Item, Field


# ---- 自定义 Item ----
class ErrorLogItem(Item):
    url = Field(nullable=True)
    error_type = Field(nullable=True)
    error_msg = Field(nullable=True)
    retry_count = Field(nullable=True)


# ---- Spider ----
class BasicErrbackSpider(Spider):
    """
    展示 errback 的基础用法。

    请求失败时 errback 自动接收 Failure 对象，
    通过 failure.value 获取异常、failure.request 获取原始请求。
    """
    name = 'basic_errback'

    # 目标 URL（故意包含不存在的域名以触发错误）
    urls = [
        'https://httpbin.org/json',          # 正常响应
        'https://httpbin.org/status/500',    # HTTP 500 错误
        'https://this-domain-does-not-exist-12345.com/api',  # DNS 解析失败
    ]

    def start_requests(self):
        for url in self.urls:
            yield Request(
                url=url,
                callback=self.parse,
                errback=self.on_error,       # ✅ 直接绑定方法
                meta={'retry_count': 0},     # 通过 meta 传递上下文
            )

    # ========== 正常回调 ==========
    async def parse(self, response):
        self.logger.info(f"✅ 成功: {response.url} 状态码={response.status}")
        yield Item({'page_url': response.url})

    # ========== 错误回调 ==========
    async def on_error(self, failure):
        """
        errback — 接收 Failure 对象，包含完整的错误上下文。

        Args:
            failure: Failure 对象

        Failure 属性:
            failure.value       → 原始异常对象
            failure.type        → 异常类型 (如 ConnectionError)
            failure.request     → 原始 Request（含 url、meta、flags）
            failure.timestamp   → 错误时间戳

        Failure 方法:
            failure.check(*Types)      → isinstance(failure.value, Types)
            failure.getErrorMessage()  → str(failure.value)
            failure.getTraceback()     → 格式化堆栈
        """

        # 1. 基本的异常信息
        self.logger.error(f"❌ 请求失败: {failure.request.url}")
        self.logger.error(f"   错误类型: {failure.type.__name__}")
        self.logger.error(f"   错误信息: {failure.getErrorMessage()}")

        # 2. 按异常类型分类处理
        from httpx import ConnectError, HTTPStatusError, TimeoutException

        if failure.check(ConnectError):
            self.logger.warning("   → 连接错误（DNS / 代理 / 网络不通）")

        elif failure.check(HTTPStatusError):
            self.logger.warning("   → HTTP 状态码错误（4xx / 5xx）")

        elif failure.check(TimeoutException):
            self.logger.warning("   → 请求超时")

        else:
            self.logger.warning(f"   → 未分类错误")

        # 3. 记录错误日志（返回 Item 进入 Pipeline）
        yield ErrorLogItem(
            url=failure.request.url,
            error_type=failure.type.__name__,
            error_msg=failure.getErrorMessage(),
            retry_count=failure.request.meta.get('retry_count', 0),
        )

        # 4. 重试逻辑：最多重试 2 次
        retry_count = failure.request.meta.get('retry_count', 0)
        max_retries = 2

        if retry_count < max_retries:
            self.logger.info(f"   🔄 第 {retry_count + 1} 次重试...")
            yield Request(
                url=failure.request.url,
                callback=self.parse,
                errback=self.on_error,
                meta={'retry_count': retry_count + 1},
                dont_filter=True,
            )
        else:
            self.logger.error(f"   🛑 已达最大重试次数 {max_retries}，放弃")
