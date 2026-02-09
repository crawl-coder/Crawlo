#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Crawlo 通知系统集成示例
===================================

演示如何在爬虫项目中集成通知系统，实现状态监控和告警功能。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlo.bot.handlers import (
    send_crawler_status,
    send_crawler_alert,
    send_crawler_progress
)
from crawlo.bot.models import ChannelType
from crawlo import Crawler, Request, Item
from crawlo.bot.channels.dingtalk import get_dingtalk_channel
from crawlo.bot.channels.feishu import get_feishu_channel
from crawlo.bot.channels.wecom import get_wecom_channel
from crawlo.bot.channels.email import get_email_channel
import asyncio
import time


def setup_notification_channels():
    """
    配置通知渠道
    注意：在实际使用中，需要替换成真实的 Webhook URL 和 SMTP 信息
    """
    print("🔧 配置通知渠道...")
    
    # 配置钉钉机器人（示例）
    # dingtalk_channel = get_dingtalk_channel()
    # dingtalk_channel.set_config(
    #     webhook_url="https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN",
    #     secret="YOUR_SECRET"  # 可选
    # )
    
    # 配置飞书机器人（示例）
    # feishu_channel = get_feishu_channel()
    # feishu_channel.set_config(
    #     webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_TOKEN"
    # )
    
    # 配置企业微信机器人（示例）
    # wecom_channel = get_wecom_channel()
    # wecom_channel.set_config(
    #     webhook_url="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
    # )
    
    # 配置邮件服务器（示例）
    # email_channel = get_email_channel()
    # email_channel.set_config(
    #     smtp_host="smtp.example.com",
    #     smtp_port=587,
    #     smtp_user="user@example.com",
    #     smtp_password="password",
    #     sender_email="sender@example.com"
    # )
    
    print("✅ 通知渠道配置完成")
    print("💡 提示：在实际部署时，请配置真实的 Webhook URL 和 SMTP 信息")


class NewsSpider(Crawler):
    """
    新闻爬虫示例，集成通知系统
    """
    name = 'news_spider'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 记录开始时间
        self.start_time = time.time()
        self.total_items = 0
        self.error_count = 0
        
        # 发送爬虫启动通知
        send_crawler_status(
            title=f"【{self.name}】爬虫启动",
            content=f"新闻爬虫任务已启动，开始抓取数据...",
            channel=ChannelType.DINGTALK
        )
    
    async def start_requests(self):
        urls = [
            'http://example-news-site.com/news/1',
            'http://example-news-site.com/news/2',
            'http://example-news-site.com/news/3',
        ]
        for url in urls:
            yield Request(url=url, callback=self.parse)
    
    async def parse(self, response):
        try:
            # 模拟解析逻辑
            title = response.css('title::text').get()
            content = response.css('div.content::text').get()
            
            item = {
                'title': title,
                'content': content,
                'url': response.url
            }
            
            self.total_items += 1
            
            # 每处理一定数量的项目发送进度通知
            if self.total_items % 10 == 0:
                elapsed_time = time.time() - self.start_time
                send_crawler_progress(
                    title=f"【{self.name}】进度更新",
                    content=f"已处理 {self.total_items} 条新闻，耗时 {elapsed_time:.2f}s",
                    channel=ChannelType.DINGTALK
                )
            
            yield item
            
            # 模拟发现更多链接
            next_page = response.css('a.next::attr(href)').get()
            if next_page:
                yield Request(url=response.urljoin(next_page), callback=self.parse)
                
        except Exception as e:
            self.error_count += 1
            # 错误率达到一定程度时发送告警
            if self.error_count >= 3:
                send_crawler_alert(
                    title=f"【{self.name}】爬虫异常告警",
                    content=f"错误数达到 {self.error_count}，请及时检查",
                    channel=ChannelType.DINGTALK
                )
    
    def closed(self, reason):
        """
        爬虫关闭时的清理工作
        """
        elapsed_time = time.time() - self.start_time
        send_crawler_status(
            title=f"【{self.name}】爬虫结束",
            content=f"爬虫任务已完成，共处理 {self.total_items} 条数据，耗时 {elapsed_time:.2f}s，错误数 {self.error_count}",
            channel=ChannelType.DINGTALK
        )


def run_news_spider_with_notifications():
    """
    运行集成了通知系统的爬虫
    """
    print("🚀 开始运行集成了通知系统的爬虫示例")
    print("=" * 60)
    
    # 配置通知渠道
    setup_notification_channels()
    
    print("\n📋 预期的通知流程：")
    print("  1. 爬虫启动 -> 发送状态通知")
    print("  2. 处理数据 -> 每10条发送进度通知")
    print("  3. 出现错误 -> 达到阈值发送告警通知")
    print("  4. 爬虫结束 -> 发送完成状态通知")
    
    print("\n📊 通知系统在爬虫中的应用场景：")
    print("  • 启停监控：实时了解爬虫运行状态")
    print("  • 异常告警：及时发现和处理问题")
    print("  • 进度跟踪：掌握数据采集进展")
    print("  • 性能监控：评估爬虫效率和稳定性")
    
    print("\n🎯 通知系统的优势：")
    print("  • 统一接口：简化不同渠道的集成")
    print("  • 类型丰富：支持状态、告警、进度等多种通知")
    print("  • 优先级控制：根据重要性调整通知级别")
    print("  • 易于扩展：可快速接入新通知渠道")
    
    print("\n🌐 支持的通知渠道：")
    print("  • 钉钉：适合企业内部团队沟通")
    print("  • 飞书：现代办公协作平台")
    print("  • 企业微信：企业通讯工具")
    print("  • 邮件：传统可靠的通知方式")
    
    print("\n✨ 爬虫通知系统集成完成！")


if __name__ == "__main__":
    run_news_spider_with_notifications()