# -*- coding: utf-8 -*-
"""
===================================
集成通知功能的 ofweek 爬虫示例
===================================

展示如何在实际爬虫中集成 Crawlo 通知系统
"""

from crawlo.spider import Spider
from crawlo import Request, Response
from ..items import OfWeekStandaloneItem
from crawlo.bot.handlers import send_crawler_status, send_crawler_alert, send_crawler_progress
from crawlo.bot.models import ChannelType
import asyncio


class OfWeekSpiderWithNotifications(Spider):
    """集成通知功能的 ofweek 爬虫"""
    
    name = 'of_week_with_notifications'
    allowed_domains = ['ee.ofweek.com']
    start_urls = ['https://ee.ofweek.com/']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats = {
            'total_requests': 0,
            'successful_items': 0,
            'failed_requests': 0,
            'start_time': None
        }
    
    async def start_requests(self):
        """生成初始请求 - 带启动通知"""
        # 发送爬虫启动通知
        await send_crawler_status(
            title="【启动】ofweek爬虫开始运行",
            content=f"爬虫任务 '{self.name}' 已启动，开始抓取 ofweek 新闻数据...",
            channel=ChannelType.DINGTALK
        )
        
        self.stats['start_time'] = self.get_current_time()
        self.logger.info("爬虫启动通知已发送")
        
        # 原有的起始请求逻辑
        max_pages = 10
        start_urls = []
        for page in range(1, max_pages + 1):
            url = f'https://ee.ofweek.com/CATList-2800-8100-ee-{page}.html'
            start_urls.append(url)
        
        self.logger.info(f"生成了 {len(start_urls)} 个起始URL")
        
        for url in start_urls:
            self.stats['total_requests'] += 1
            yield Request(url, callback=self.parse, dont_filter=True)
    
    async def parse(self, response: Response):
        """解析响应 - 带进度和异常通知"""
        try:
            # 检查响应状态
            if response.status_code != 200:
                self.stats['failed_requests'] += 1
                error_msg = f"页面返回非200状态码: {response.status_code}"
                self.logger.warning(f"{error_msg}, URL: {response.url}")
                
                # 发送告警通知
                await send_crawler_alert(
                    title="【告警】页面访问失败",
                    content=f"URL: {response.url}\n状态码: {response.status_code}\n已记录并继续处理其他请求",
                    channel=ChannelType.DINGTALK
                )
                return
            
            # 检查页面内容是否为空
            if not response.text or len(response.text.strip()) == 0:
                self.stats['failed_requests'] += 1
                self.logger.warning(f"页面内容为空: {response.url}")
                return
            
            # 数据提取
            rows = response.xpath('//div[@class="main_left"]/div[@class="list_model"]/div[@class="model_right model_right2"]')
            self.logger.info(f"在页面 {response.url} 中找到 {len(rows)} 个条目")
            
            # 发送进度通知（每处理5个页面发送一次）
            if self.stats['total_requests'] % 5 == 0:
                await send_crawler_progress(
                    title="【进度】数据抓取进度",
                    content=f"已处理 {self.stats['total_requests']} 个页面，成功提取 {len(rows)} 条数据",
                    channel=ChannelType.DINGTALK
                )
            
            for row in rows:
                try:
                    # 提取URL和标题
                    url = row.xpath('./h3/a/@href').extract_first()
                    title = row.xpath('./h3/a/text()').extract_first()
                    
                    # 容错处理
                    if not url or not title:
                        continue
                    
                    # 确保 URL 是绝对路径
                    absolute_url = response.urljoin(url)
                    
                    # 验证URL格式
                    if not absolute_url.startswith(('http://', 'https://')):
                        continue
                    
                    yield Request(
                        url=absolute_url,
                        meta={
                            "title": title.strip(),
                            "parent_url": response.url
                        },
                        callback=self.parse_detail
                    )
                    
                except Exception as e:
                    self.logger.error(f"处理条目时出错: {e}")
                    continue
                    
        except Exception as e:
            self.stats['failed_requests'] += 1
            error_msg = f"解析页面时出错: {str(e)}"
            self.logger.error(error_msg)
            
            # 发送严重错误告警
            await send_crawler_alert(
                title="【严重告警】页面解析异常",
                content=f"URL: {response.url}\n错误信息: {error_msg}\n请检查页面结构是否发生变化",
                channel=ChannelType.DINGTALK
            )
    
    async def parse_detail(self, response):
        """解析详情页面 - 带数据统计通知"""
        try:
            self.logger.info(f'正在解析详情页: {response.url}')
            
            # 检查响应状态
            if response.status_code != 200:
                self.stats['failed_requests'] += 1
                self.logger.warning(f"详情页返回非200状态码: {response.status_code}")
                return
            
            title = response.meta.get('title', '')
            
            # 提取内容
            content_elements = response.xpath('//div[@class="TRS_Editor"]|//*[@id="articleC"]')
            if content_elements:
                content = content_elements.xpath('.//text()').extract()
                content = '\n'.join([text.strip() for text in content if text.strip()])
            else:
                content = ''
            
            # 提取发布时间和来源
            publish_time = response.xpath('//div[@class="time fl"]/text()').extract_first()
            source = response.xpath('//div[@class="source-name"]/text()').extract_first()
            
            # 创建数据项
            item = OfWeekStandaloneItem()
            item['title'] = title.strip() if title else ''
            item['publish_time'] = publish_time.strip() if publish_time else ''
            item['url'] = response.url
            item['source'] = source.strip() if source else ''
            item['content'] = content
            
            self.stats['successful_items'] += 1
            
            # 每成功处理100条数据发送一次进度通知
            if self.stats['successful_items'] % 100 == 0:
                await send_crawler_progress(
                    title="【数据统计】抓取进度更新",
                    content=f"累计成功抓取 {self.stats['successful_items']} 条数据\n失败请求: {self.stats['failed_requests']} 次",
                    channel=ChannelType.DINGTALK
                )
            
            yield item
            
        except Exception as e:
            self.stats['failed_requests'] += 1
            self.logger.error(f"解析详情页 {response.url} 时出错: {e}")
    
    async def closed(self, reason):
        """爬虫关闭时的回调 - 发送总结通知"""
        # 计算运行时长
        run_duration = self.get_run_duration()
        
        # 发送任务完成总结通知
        await send_crawler_status(
            title="【完成】ofweek爬虫任务总结",
            content=f"""爬虫任务 '{self.name}' 已完成！
📊 运行统计：
   • 总请求数: {self.stats['total_requests']}
   • 成功抓取: {self.stats['successful_items']} 条数据
   • 失败请求: {self.stats['failed_requests']} 次
   • 运行时长: {run_duration}
✅ 数据已存储到 MySQL 数据库
📍 项目: ofweek_standalone""",
            channel=ChannelType.DINGTALK
        )
        
        self.logger.info("爬虫完成总结通知已发送")
    
    def get_current_time(self):
        """获取当前时间"""
        from datetime import datetime
        return datetime.now()
    
    def get_run_duration(self):
        """计算运行时长"""
        if not self.stats['start_time']:
            return "未知"
        
        from datetime import datetime
        duration = datetime.now() - self.stats['start_time']
        hours, remainder = divmod(duration.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}小时{minutes}分钟{seconds}秒"


# 使用示例
def run_spider_with_notifications():
    """运行带通知的爬虫示例"""
    print("🚀 启动集成通知功能的 ofweek 爬虫...")
    
    # 这里应该是实际的爬虫运行代码
    # 由于这是示例，我们只演示通知功能
    
    async def demo():
        # 模拟爬虫运行过程中的通知
        await send_crawler_status(
            title="【示例】爬虫通知功能演示",
            content="这是演示如何在爬虫中使用通知功能的示例",
            channel=ChannelType.DINGTALK
        )
    
    asyncio.run(demo())
    print("✅ 演示完成！")


if __name__ == "__main__":
    run_spider_with_notifications()