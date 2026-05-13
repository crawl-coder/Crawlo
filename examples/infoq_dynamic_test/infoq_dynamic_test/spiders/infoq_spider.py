# -*- coding: UTF-8 -*-
"""
InfoQ 动态下载器测试爬虫
==========================
测试 CloakBrowserDownloader 的使用

测试目标：https://www.infoq.cn/zones/harmonyos/latest
"""
import os
from crawlo import Spider, Request
from ..items import InfoqArticle




class InfoqSpider(Spider):
    """InfoQ HarmonyOS 文章爬虫 - 使用 CloakBrowserDownloader"""
    
    name = 'infoq_spider'
    
    # 目标 URL
    START_URL = 'https://www.infoq.cn/zones/harmonyos/latest'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_mode = os.environ.get('TEST_MODE', 'dynamic_meta')
        
    def start_requests(self):
        """生成起始请求"""
        
        # 使用 CloakBrowser 动态下载器
        self.logger.info(f"[CloakBrowser] 启用动态下载器")
        yield Request(
            url=self.START_URL,
            callback=self.parse,
            meta={
                'use_dynamic_loader': True,
                # CloakBrowser 特有配置（cloakbrowser_ 前缀）
                'cloakbrowser_auto_scroll': True,
                'cloakbrowser_scroll_delay': 500,
                'cloakbrowser_block_resources': ["image", "font", "media"],
            }
        )
    
    def parse(self, response):
        """解析列表页"""
        
        # 输出基本信息
        current_page = response.meta.get('page', 1)
        self.logger.info(f"\n{'#'*60}")
        self.logger.info(f"# 测试模式: {self.test_mode}")
        self.logger.info(f"# 当前页码: {current_page}")
        self.logger.info(f"# URL: {response.url}")
        self.logger.info(f"# 状态码: {response.status}")
        self.logger.info(f"# 内容长度: {len(response.text)} 字符")
        self.logger.info(f"# 使用动态下载器: {response.request.meta.get('use_dynamic_loader', False)}")
        self.logger.info(f"{'#'*60}\n")
        
        # 提取页面标题
        title = response.xpath('//title/text()').get()
        self.logger.info(f"页面标题: {title}")
        
        # 提取文章列表 - 使用正确的选择器
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
                
                # 生成文章项
                article = InfoqArticle(
                    url=full_url,
                    title=article_title.strip() if article_title else '',
                    author=author.strip() if author else '',
                    date=date.strip() if date else '',
                    summary=summary.strip() if summary else '',
                    source='infoq.cn',
                    type='article'
                )
                
                yield article
                
                # 跟进详情页（限制前3个）
                if article_count <= 3:
                    yield Request(
                        url=full_url,
                        callback=self.parse_detail,
                        meta={
                            'article_title': article_title,
                            'use_dynamic_loader': True,
                        }
                    )
        
        # 输出统计
        self.logger.info(f"提取到 {article_count} 篇文章")
        
        # 确保至少返回一个 Item
        if article_count == 0:
            yield InfoqArticle(
                url=response.url,
                title=title or 'Unknown',
                source='infoq.cn',
                note='No articles found'
            )
        
        # 尝试点击"更多"按钮加载下一页
        self.logger.info("尝试点击'更多'按钮加载下一页...")
        yield Request(
            url=response.url,
            callback=self.parse,
            dont_filter=True,  # 允许重复URL
            meta={
                # 确保使用动态下载器
                'use_dynamic_loader': True,
                # 使用 cloakbrowser_ 前缀的配置
                'cloakbrowser_auto_scroll': True,
                'cloakbrowser_block_resources': ["image", "font", "media"],
                # 使用通用的 dynamic_actions（CloakBrowser 支持）
                'dynamic_actions': [
                    # 智能滚动到底部
                    {
                        'type': 'scroll_to_bottom',
                        'params': {
                            'scroll_delay': 500,
                            'max_no_content': 2
                        }
                    },
                    # 等待按钮渲染
                    {
                        'type': 'wait',
                        'params': {
                            'timeout': 1000
                        }
                    },
                    # 点击"加载更多"按钮
                    {
                        'type': 'click_and_wait',
                        'params': {
                            'selector': '//div[contains(@class, "more-button") and contains(text(), "加载更多")]',
                            'wait_timeout': 3000,
                            'wait_for': 'networkidle'
                        }
                    }
                ]
            }
        )
    
    def parse_detail(self, response):
        """解析详情页"""
        article_title = response.meta.get('article_title', '')
        
        # 提取正文内容
        content_html = response.xpath('//div[@class="ProseMirror"]').get()
        content_text = response.xpath('//div[@class="ProseMirror"]//text()').getall()
        content_text = ''.join([t.strip() for t in content_text if t.strip()])
        
        self.logger.info(f"详情页: {response.url}")
        self.logger.info(f"文章标题: {article_title}")
        self.logger.info(f"正文长度: {len(content_text)} 字符")
        
        # 生成详情页项
        yield InfoqArticle(
            url=response.url,
            title=article_title,
            content=content_text,
            content_html=content_html,
            source='infoq.cn',
            type='detail'
        )
