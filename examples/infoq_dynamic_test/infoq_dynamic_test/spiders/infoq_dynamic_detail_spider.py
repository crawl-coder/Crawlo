# -*- coding: UTF-8 -*-
"""
InfoQ 动态详情页测试爬虫
==========================
测试场景：列表页使用协议下载器（快速），详情页使用动态下载器（渲染JS）

适用场景：
- 列表页是静态 HTML，可以直接解析
- 详情页包含动态内容（评论、相关推荐、懒加载图片等）需要浏览器渲染
"""
import os
from crawlo import Spider, Request
from ..items import InfoqArticle


class InfoqDynamicDetailSpider(Spider):
    """InfoQ 文章爬虫 - 详情页使用动态渲染"""
    
    name = 'infoq_dynamic_detail_spider'
    
    # 目标 URL
    START_URL = 'https://www.infoq.cn/zones/harmonyos/latest'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_mode = os.environ.get('TEST_MODE', 'protocol')
        
    def start_requests(self):
        """生成起始请求 - 使用协议下载器（快速）"""
        self.logger.info("[列表页] 使用协议下载器（静态HTML）")
        yield Request(
            url=self.START_URL,
            callback=self.parse_list
            # 不设置 use_dynamic_loader，使用默认的协议下载器
        )
    
    def parse_list(self, response):
        """解析列表页 - 协议下载器返回"""
        
        # 输出基本信息
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"[列表页] URL: {response.url}")
        self.logger.info(f"[列表页] 状态码: {response.status}")
        self.logger.info(f"[列表页] 内容长度: {len(response.text)} 字符")
        self.logger.info(f"[列表页] 下载器类型: 协议下载器（快速）")
        self.logger.info(f"{'='*60}\n")
        
        # 提取页面标题
        title = response.xpath('//title/text()').get()
        self.logger.info(f"页面标题: {title}")
        
        # 提取文章列表
        article_items = response.xpath('//div[@article-item]')
        self.logger.info(f"找到文章容器: {len(article_items)} 个")
        
        # 提取文章信息
        article_count = 0
        for idx, item in enumerate(article_items, 1):
            # 文章链接
            url = item.xpath('.//h4[@class="title"]/a/@href').get()
            # 文章标题
            article_title = item.xpath('.//h4[@class="title"]/a/text()').get()
            # 作者
            author = item.xpath('.//a[@com-author-name]/text()').get()
            # 日期
            date = item.xpath('.//span[@class="date"]/text()').get()
            # 摘要
            summary = item.xpath('.//p[@class="summary"]/span/text()').get()
            
            # 调试日志
            if idx <= 3:
                self.logger.debug(f"文章 {idx}: url={url}, title={article_title}")
            
            if url:
                full_url = response.urljoin(url)
                article_count += 1
                
                # 生成列表页 Item
                article = InfoqArticle(
                    url=full_url,
                    title=article_title.strip() if article_title else '',
                    author=author.strip() if author else '',
                    date=date.strip() if date else '',
                    summary=summary.strip() if summary else '',
                    source='infoq.cn',
                    type='list_item'
                )
                
                yield article
                
                # 跟进详情页 - 使用动态下载器（限制前2个用于测试）
                if article_count <= 2:
                    self.logger.info(f"[详情页] 准备使用动态下载器加载: {article_title}")
                    yield Request(
                        url=full_url,
                        callback=self.parse_detail,
                        meta={
                            'article_title': article_title,
                            'use_dynamic_loader': True,  # 关键：启用动态下载器
                            # 可选：添加页面操作（如果需要滚动或点击）
                            # 'dynamic_actions': [
                            #     {
                            #         'type': 'scroll_to_bottom',
                            #         'params': {
                            #             'scroll_delay': 500,
                            #             'max_no_content': 2
                            #         }
                            #     }
                            # ]
                        }
                    )
        
        # 输出统计
        self.logger.info(f"[列表页] 提取到 {article_count} 篇文章")
        self.logger.info(f"[列表页] 跟进 {min(article_count, 2)} 个详情页（使用动态渲染）")
        
        # 确保至少返回一个 Item
        if article_count == 0:
            yield InfoqArticle(
                url=response.url,
                title=title or 'Unknown',
                source='infoq.cn',
                note='No articles found in list page'
            )
        
        # 注意：这里不翻页，只爬取第一页作为示例
    
    def parse_detail(self, response):
        """解析详情页 - 动态下载器返回"""
        article_title = response.meta.get('article_title', '')
        
        # 输出基本信息
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"[详情页] URL: {response.url}")
        self.logger.info(f"[详情页] 文章标题: {article_title}")
        self.logger.info(f"[详情页] 内容长度: {len(response.text)} 字符")
        self.logger.info(f"[详情页] 下载器类型: 动态下载器（浏览器渲染）")
        self.logger.info(f"{'='*60}\n")
        
        # 提取正文内容
        content_html = response.xpath('//div[@class="ProseMirror"]').get()
        content_text = response.xpath('//div[@class="ProseMirror"]//text()').getall()
        content_text = ''.join([t.strip() for t in content_text if t.strip()])
        
        # 提取动态内容（这些内容只有动态下载器才能获取到）
        # 例如：评论数、相关推荐、作者信息等
        comment_count = response.xpath('//span[contains(@class, "comment-count")]/text()').get()
        related_articles = response.xpath('//div[contains(@class, "related")]//a/text()').getall()
        
        self.logger.info(f"[详情页] 正文长度: {len(content_text)} 字符")
        self.logger.info(f"[详情页] 评论数: {comment_count or '未找到'}")
        self.logger.info(f"[详情页] 相关文章数: {len(related_articles)}")
        
        # 如果有动态操作，输出执行情况
        dynamic_actions = response.request.meta.get('dynamic_actions', [])
        if dynamic_actions:
            self.logger.info(f"[详情页] 执行了 {len(dynamic_actions)} 个动态操作")
        
        # 生成详情页 Item
        yield InfoqArticle(
            url=response.url,
            title=article_title,
            content=content_text,
            content_html=content_html,
            source='infoq.cn',
            type='detail',
            note=f'Loaded with dynamic downloader, content length: {len(content_text)}'
        )
