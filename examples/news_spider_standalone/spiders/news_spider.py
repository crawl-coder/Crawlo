"""
新闻爬虫示例
演示如何使用Crawlo框架爬取新闻网站
"""

import re
from urllib.parse import urljoin
from crawlo.spider import Spider
from crawlo.network.request import Request
from crawlo.items import Item, Field


class NewsItem(Item):
    """新闻数据项"""
    title = Field()          # 标题
    url = Field()            # 链接
    content = Field()        # 内容
    author = Field()         # 作者
    publish_time = Field()   # 发布时间
    category = Field()       # 分类
    tags = Field()           # 标签


class NewsSpider(Spider):
    """新闻爬虫"""
    
    name = "news_spider"
    allowed_domains = ["example-news.com"]
    start_urls = [
        "https://example-news.com",
        "https://example-news.com/tech",
        "https://example-news.com/business",
        "https://example-news.com/sports"
    ]
    
    # 自定义配置
    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS': 5,
        'USER_AGENT': 'Crawlo NewsBot 1.0'
    }
    
    async def parse(self, response):
        """解析首页和分类页面"""
        self.logger.info(f"正在解析: {response.url}")
        
        # 提取新闻链接
        news_links = response.css('a.news-link::attr(href)').getall()
        if not news_links:
            # 备用选择器
            news_links = response.css('a[href*="/news/"]::attr(href)').getall()
        
        # 处理相对链接
        for link in news_links:
            full_url = urljoin(response.url, link)
            yield Request(
                url=full_url,
                callback=self.parse_news,
                meta={'category': self._extract_category(response.url)}
            )
        
        # 提取分页链接
        next_page = response.css('a.next-page::attr(href)').get()
        if next_page:
            yield Request(
                url=urljoin(response.url, next_page),
                callback=self.parse
            )
    
    async def parse_news(self, response):
        """解析新闻详情页"""
        self.logger.info(f"正在解析新闻: {response.url}")
        
        # 提取新闻数据
        item = NewsItem()
        
        item['url'] = response.url
        item['title'] = self._extract_title(response)
        item['content'] = self._extract_content(response)
        item['author'] = self._extract_author(response)
        item['publish_time'] = self._extract_publish_time(response)
        item['category'] = response.meta.get('category', 'general')
        item['tags'] = self._extract_tags(response)
        
        # 数据验证
        if item['title'] and item['content']:
            yield item
        else:
            self.logger.warning(f"新闻数据不完整: {response.url}")
    
    def _extract_title(self, response):
        """提取标题"""
        selectors = [
            'h1.news-title::text',
            'h1.article-title::text',
            'title::text',
            'h1::text'
        ]
        
        for selector in selectors:
            title = response.css(selector).get()
            if title:
                return title.strip()
        return None
    
    def _extract_content(self, response):
        """提取内容"""
        selectors = [
            '.news-content',
            '.article-content',
            '.content',
            'article'
        ]
        
        for selector in selectors:
            content_elements = response.css(f'{selector} p::text').getall()
            if content_elements:
                return '\n'.join(p.strip() for p in content_elements if p.strip())
        return None
    
    def _extract_author(self, response):
        """提取作者"""
        selectors = [
            '.author::text',
            '.by-author::text',
            '[rel="author"]::text'
        ]
        
        for selector in selectors:
            author = response.css(selector).get()
            if author:
                return author.strip()
        return "未知作者"
    
    def _extract_publish_time(self, response):
        """提取发布时间"""
        selectors = [
            'time::attr(datetime)',
            '.publish-time::text',
            '.date::text',
            '[class*="time"]::text'
        ]
        
        for selector in selectors:
            time_str = response.css(selector).get()
            if time_str:
                return self._clean_time_string(time_str.strip())
        return None
    
    def _extract_tags(self, response):
        """提取标签"""
        tags = response.css('.tags a::text, .tag::text').getall()
        return [tag.strip() for tag in tags if tag.strip()]
    
    def _extract_category(self, url):
        """从URL提取分类"""
        if '/tech' in url:
            return '科技'
        elif '/business' in url:
            return '商业'
        elif '/sports' in url:
            return '体育'
        else:
            return '综合'
    
    def _clean_time_string(self, time_str):
        """清理时间字符串"""
        # 移除多余的空白字符
        time_str = re.sub(r'\s+', ' ', time_str)
        # 移除常见的前缀
        time_str = re.sub(r'^(发布时间|时间)[：:]?\s*', '', time_str)
        return time_str