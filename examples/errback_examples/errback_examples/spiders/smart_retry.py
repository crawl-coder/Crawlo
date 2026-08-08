#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
智能重试 + Failure.request 示例
================================

演示：
1. 通过 failure.request 精确重建请求（保留原始 URL、meta、flags、cb_kwargs）
2. 备用域名降级策略（主域名失败 → 自动切换备用域名）
3. 利用 flags 标记追踪请求状态
4. 组合使用 errback + cb_kwargs 传递业务参数
"""
from crawlo import Spider, Request, Item, Field


class SmartRetrySpider(Spider):
    """
    展示 errback 的高级用法：智能重试 + 降级策略。

    核心思路：
    - 失败时通过 failure.request 获取原始请求的所有属性
    - 根据 flags 标记决定重试策略
    - 使用备用域名实现降级
    """
    name = 'smart_retry'

    # 主域名和备用域名
    PRIMARY_DOMAIN = 'https://this-primary-domain-will-fail-99999.com'
    FALLBACK_DOMAIN = 'https://httpbin.org'

    # 模拟任务列表
    tasks = [
        {'id': 1, 'endpoint': '/json', 'priority': 'high'},
        {'id': 2, 'endpoint': '/ip', 'priority': 'normal'},
        {'id': 3, 'endpoint': '/uuid', 'priority': 'low'},
    ]

    def start_requests(self):
        for task in self.tasks:
            yield Request(
                url=f'{self.PRIMARY_DOMAIN}{task["endpoint"]}',
                callback=self.parse,
                errback=self.on_error,
                cb_kwargs={'task_id': task['id']},      # 通过 cb_kwargs 传递业务参数
                meta={
                    'endpoint': task['endpoint'],
                    'priority': task['priority'],
                },
                flags=['primary'],                        # 标记请求来源
            )

    # ========== 正常回调 ==========
    async def parse(self, response, task_id=None):
        """成功处理响应"""
        self.logger.info(
            f"✅ 任务 {task_id}: 已获取 {response.url} "
            f"(flags={response.flags})"
        )

    # ========== 错误回调 ==========
    async def on_error(self, failure):
        """
        智能错误处理：根据原始请求信息执行降级/重试。

        由于 errback 现在接收 Failure 对象，可以直接通过
        failure.request 获取原始 Request 的全部属性。
        """
        req = failure.request

        # 1. 提取原始上下文
        endpoint = req.meta.get('endpoint', '')
        priority = req.meta.get('priority', 'normal')
        flags = getattr(req, 'flags', [])
        cb_kwargs = getattr(req, 'cb_kwargs', {}).copy()

        self.logger.error(f"❌ 主域名请求失败: {req.url}")
        self.logger.error(f"   任务 {cb_kwargs.get('task_id')}: {failure.type.__name__}")

        # 2. 已使用备用域名的请求不再重试
        if 'fallback' in flags:
            self.logger.error(f"   🛑 备用域名也失败，彻底放弃")
            return

        # 3. 主域名失败 → 自动切换到备用域名
        fallback_url = f'{self.FALLBACK_DOMAIN}{endpoint}'
        self.logger.info(f"   🔄 降级到备用域名: {fallback_url}")

        # 4. 重建请求 — 精确继承原始属性
        yield Request(
            url=fallback_url,
            callback=self.parse,
            errback=self.on_error,                # 继续绑定 errback
            cb_kwargs=cb_kwargs,                  # ✅ 继承原始 cb_kwargs
            meta={
                **req.meta,                       # ✅ 继承原始 meta
                'due_to_error': True,
            },
            flags=flags + ['fallback'],           # ✅ 追加标记
        )

    # ========== 可选：错误统计 on_spider_closed ==========
    async def on_spider_closed(self, spider, reason):
        """爬虫结束时汇总"""
        self.logger.info("=" * 50)
        self.logger.info(f"爬虫结束: {reason}")
        self.logger.info("=" * 50)
