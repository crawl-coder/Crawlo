# -*- coding: utf-8 -*-
"""
===================================
ofweek_standalone 项目钉钉通知使用示例
===================================

演示如何在实际爬虫项目中使用 Crawlo 通知系统发送钉钉通知
"""

import asyncio
# 修正：从 crawlo.bot 统一导入
from crawlo.bot import (
    send_crawler_status, 
    send_crawler_alert, 
    send_crawler_progress,
    ChannelType
)


class NotificationDemo:
    """通知功能演示类"""
    
    def __init__(self):
        """初始化通知演示"""
        pass
    
    async def demo_basic_notifications(self):
        """演示基础通知功能"""
        print("🚀 开始演示基础通知功能...")
        
        # 1. 发送状态通知
        print("\n--- 发送状态通知 ---")
        status_response = await send_crawler_status(
            title="【状态】ofweek爬虫运行中",
            content="ofweek_standalone 爬虫已启动，正在抓取数据...",
            channel=ChannelType.DINGTALK
        )
        print(f"状态通知发送结果: success={status_response.success}, message='{status_response.message}'")
        
        # 2. 发送进度通知
        print("\n--- 发送进度通知 ---")
        progress_response = await send_crawler_progress(
            title="【进度】数据抓取进度",
            content="已完成 50% 的数据抓取任务，预计还需要 30 分钟完成",
            channel=ChannelType.DINGTALK
        )
        print(f"进度通知发送结果: success={progress_response.success}, message='{progress_response.message}'")
        
        # 3. 发送告警通知
        print("\n--- 发送告警通知 ---")
        alert_response = await send_crawler_alert(
            title="【告警】爬虫异常",
            content="检测到网络连接不稳定，部分请求失败，已自动重试",
            channel=ChannelType.DINGTALK
        )
        print(f"告警通知发送结果: success={alert_response.success}, message='{alert_response.message}'")
    
    async def demo_advanced_notifications(self):
        """演示高级通知功能"""
        print("\n🚀 开始演示高级通知功能...")
        
        # 1. 发送详细的任务报告
        print("\n--- 发送任务报告 ---")
        report_response = await send_crawler_status(
            title="【日报】ofweek爬虫每日报告",
            content="""今日爬虫运行情况总结：
📊 抓取数据量：1,250 条
✅ 成功请求：856 次
⚠️ 失败请求：45 次（已重试）
⏱️ 运行时长：2小时35分钟
📈 数据存储：MySQL 数据库""",
            channel=ChannelType.DINGTALK
        )
        print(f"任务报告发送结果: success={report_response.success}")
        
        # 2. 发送异常告警
        print("\n--- 发送异常告警 ---")
        error_response = await send_crawler_alert(
            title="【紧急】数据库连接失败",
            content="""数据库连接出现异常：
🔴 错误类型：ConnectionError
🔴 影响范围：数据存储暂停
🔴 建议措施：检查MySQL服务状态
🔴 当前状态：已切换到本地文件存储""",
            channel=ChannelType.DINGTALK
        )
        print(f"异常告警发送结果: success={error_response.success}")
    
    async def demo_real_world_usage(self):
        """演示真实世界使用场景"""
        print("\n🚀 开始演示真实使用场景...")
        
        # 模拟爬虫启动通知
        print("\n--- 爬虫启动通知 ---")
        await send_crawler_status(
            title="【启动】ofweek爬虫开始运行",
            content="爬虫任务已启动，开始抓取 ofweek 新闻数据...",
            channel=ChannelType.DINGTALK
        )
        
        # 模拟进度更新（可以放在爬虫的关键节点）
        print("\n--- 进度更新通知 ---")
        await send_crawler_progress(
            title="【进度】爬虫执行进度",
            content="已完成第一阶段抓取：新闻列表页数据获取完毕",
            channel=ChannelType.DINGTALK
        )
        
        # 模拟完成通知
        print("\n--- 任务完成通知 ---")
        await send_crawler_status(
            title="【完成】ofweek爬虫任务完成",
            content="今日爬虫任务已完成！共抓取数据 1,250 条，存储到 MySQL 数据库。",
            channel=ChannelType.DINGTALK
        )


# 在爬虫中的实际使用示例
class OfWeekSpiderWithNotifications:
    """带通知功能的 ofweek 爬虫示例"""
    
    def __init__(self):
        self.name = 'of_week_with_notifications'
    
    async def start_requests_with_notification(self):
        """带通知的起始请求"""
        # 发送启动通知
        await send_crawler_status(
            title="【启动】ofweek爬虫开始运行",
            content="爬虫任务已启动，开始抓取 ofweek 新闻数据...",
            channel=ChannelType.DINGTALK
        )
        
        # 原有的爬虫逻辑...
        max_pages = 10
        for page in range(1, max_pages + 1):
            url = f'https://ee.ofweek.com/CATList-2800-8100-ee-{page}.html'
            # yield Request(url, callback=self.parse)
    
    async def parse_with_progress_notification(self, response):
        """带进度通知的解析方法"""
        # 原有的解析逻辑...
        rows = response.xpath('//div[@class="main_left"]/div[@class="list_model"]/div[@class="model_right model_right2"]')
        
        # 发送进度通知（每处理100条发送一次）
        if len(rows) > 0 and len(rows) % 100 == 0:
            await send_crawler_progress(
                title="【进度】数据处理进度",
                content=f"已处理 {len(rows)} 条数据，继续抓取中...",
                channel=ChannelType.DINGTALK
            )
        
        # 继续原有的解析逻辑...
    
    async def handle_error_with_alert(self, error_info):
        """带告警的错误处理"""
        # 发送错误告警
        await send_crawler_alert(
            title="【告警】爬虫执行异常",
            content=f"发生错误：{error_info}\n已记录日志并尝试恢复...",
            channel=ChannelType.DINGTALK
        )
        
        # 原有的错误处理逻辑...


def main():
    """主函数 - 运行演示"""
    print("🎯 Crawlo 通知系统演示")
    print("=" * 50)
    
    demo = NotificationDemo()
    
    # 运行演示
    asyncio.run(demo.demo_basic_notifications())
    asyncio.run(demo.demo_advanced_notifications())
    asyncio.run(demo.demo_real_world_usage())
    
    print("\n" + "=" * 50)
    print("✅ 演示完成！")
    print("\n💡 在实际项目中的使用建议：")
    print("1. 在爬虫启动时发送状态通知")
    print("2. 在关键节点发送进度通知")
    print("3. 在出现异常时发送告警通知")
    print("4. 在任务完成时发送总结通知")


if __name__ == "__main__":
    main()