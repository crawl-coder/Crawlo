"""
分布式新闻爬虫示例
演示Crawlo框架的分布式特性和高级功能
"""

import asyncio
import hashlib
from datetime import datetime
from urllib.parse import urljoin
from crawlo.spider import Spider
from crawlo.network.request import Request
from crawlo.items import Item, Field


class NewsItem(Item):
    """新闻数据项 - 增强版"""
    id = Field()             # 唯一ID
    title = Field()          # 标题
    url = Field()            # 链接
    content = Field()        # 内容
    summary = Field()        # 摘要
    author = Field()         # 作者
    publish_time = Field()   # 发布时间
    crawl_time = Field()     # 爬取时间
    category = Field()       # 分类
    tags = Field()           # 标签
    source = Field()         # 来源
    word_count = Field()     # 字数
    read_count = Field()     # 阅读数
    comment_count = Field()  # 评论数


class DistributedNewsSpider(Spider):
    """分布式新闻爬虫"""
    
    name = "distributed_news_spider"
    allowed_domains = [
        "example-news.com",
        "tech-news.com",
        "business-daily.com",
        "sports-world.com"
    ]
    
    # 多个起始URL，支持大规模爬取
    start_urls = [
        # 主要新闻站点
        "https://example-news.com",
        "https://example-news.com/tech",
        "https://example-news.com/business",
        "https://example-news.com/sports",
        "https://example-news.com/entertainment",
        
        # 科技新闻
        "https://tech-news.com",
        "https://tech-news.com/ai",
        "https://tech-news.com/blockchain",
        
        # 商业新闻
        "https://business-daily.com",
        "https://business-daily.com/finance",
        "https://business-daily.com/markets",
        
        # 体育新闻
        "https://sports-world.com",
        "https://sports-world.com/football",
        "https://sports-world.com/basketball"
    ]
    
    # 分布式配置
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'CONCURRENT_REQUESTS': 20,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 0.5,
        'AUTOTHROTTLE_MAX_DELAY': 10,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 2.0,
        'USER_AGENT': 'Crawlo DistributedBot 2.0',
        'RETRY_TIMES': 5,
        'DOWNLOAD_TIMEOUT': 60
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.crawled_count = 0
        
    async def start_requests(self):
        """生成初始请求"""
        for url in self.start_urls:
            yield Request(
                url=url,
                callback=self.parse,
                meta={
                    'priority': 10,  # 高优先级
                    'source': self._extract_source(url)
                },
                dont_filter=False  # 启用去重
            )
    
    async def parse(self, response):
        """解析首页和分类页面"""
        self.logger.info(f"[{response.meta.get('source', 'unknown')}] 正在解析: {response.url}")
        
        # 提取新闻链接
        news_selectors = [
            'a.news-link::attr(href)',
            'a[href*="/news/"]::attr(href)',
            'a[href*="/article/"]::attr(href)',
            '.news-item a::attr(href)',
            '.article-item a::attr(href)'
        ]
        
        news_links = []
        for selector in news_selectors:
            links = response.css(selector).getall()
            news_links.extend(links)
        
        # 去重并处理链接
        unique_links = list(set(news_links))
        
        for link in unique_links:
            if not link:
                continue
                
            full_url = urljoin(response.url, link)
            
            # 链接过滤
            if self._is_valid_news_url(full_url):
                yield Request(
                    url=full_url,
                    callback=self.parse_news,
                    meta={
                        'category': self._extract_category(response.url),
                        'source': response.meta.get('source'),
                        'priority': 5
                    }
                )
        
        # 处理分页和分类链接
        pagination_links = response.css('a.next-page::attr(href), a[rel="next"]::attr(href)').getall()
        category_links = response.css('nav a::attr(href), .category-nav a::attr(href)').getall()
        
        for link in pagination_links + category_links:
            if link:
                full_url = urljoin(response.url, link)
                yield Request(
                    url=full_url,
                    callback=self.parse,
                    meta=response.meta,
                    priority=3
                )
    
    async def parse_news(self, response):
        """解析新闻详情页"""
        self.crawled_count += 1
        self.logger.info(f"[{response.meta.get('source', 'unknown')}] 解析新闻 #{self.crawled_count}: {response.url}")
        
        # 创建新闻项
        item = NewsItem()
        
        # 基本信息
        item['id'] = self._generate_id(response.url)
        item['url'] = response.url
        item['crawl_time'] = datetime.now().isoformat()
        item['source'] = response.meta.get('source', 'unknown')
        item['category'] = response.meta.get('category', 'general')
        
        # 提取内容
        item['title'] = self._extract_title(response)
        item['content'] = self._extract_content(response)
        item['summary'] = self._extract_summary(response, item['content'])
        item['author'] = self._extract_author(response)
        item['publish_time'] = self._extract_publish_time(response)
        item['tags'] = self._extract_tags(response)
        
        # 统计信息
        if item['content']:
            item['word_count'] = len(item['content'].replace(' ', ''))
        item['read_count'] = self._extract_read_count(response)
        item['comment_count'] = self._extract_comment_count(response)
        
        # 数据验证
        if self._validate_item(item):
            yield item
            
            # 提取相关文章链接
            await self._extract_related_links(response, item)
        else:
            self.logger.warning(f"新闻数据验证失败: {response.url}")
    
    def _generate_id(self, url):
        """生成唯一ID"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def _extract_source(self, url):
        """从URL提取来源"""
        if 'example-news.com' in url:
            return '示例新闻'
        elif 'tech-news.com' in url:
            return '科技新闻'
        elif 'business-daily.com' in url:
            return '商业日报'
        elif 'sports-world.com' in url:
            return '体育世界'
        else:
            return '未知来源'
    
    def _is_valid_news_url(self, url):
        """验证是否为有效的新闻URL"""
        invalid_patterns = [
            '/login', '/register', '/contact', '/about',
            '/search', '/tag/', '/category/', '/archive/',
            '.pdf', '.doc', '.zip', '.jpg', '.png', '.gif'
        ]
        
        for pattern in invalid_patterns:
            if pattern in url.lower():
                return False
        
        return True
    
    def _extract_title(self, response):
        """提取标题"""
        selectors = [
            'h1.news-title::text',
            'h1.article-title::text',
            'h1[class*="title"]::text',
            '.title h1::text',
            'title::text',
            'h1::text'
        ]
        
        for selector in selectors:
            title = response.css(selector).get()
            if title and len(title.strip()) > 5:  # 确保标题有意义
                return title.strip()
        return None
    
    def _extract_content(self, response):
        """提取内容"""
        content_selectors = [
            '.news-content',
            '.article-content', 
            '.content',
            '.post-content',
            'article .content',
            '.entry-content'
        ]
        
        for selector in content_selectors:
            # 提取段落文本
            paragraphs = response.css(f'{selector} p::text').getall()
            if paragraphs:
                content = '\n'.join(p.strip() for p in paragraphs if p.strip())
                if len(content) > 100:  # 确保内容充实
                    return content
        
        return None
    
    def _extract_summary(self, response, content):
        """提取摘要"""
        # 首先尝试从meta标签获取
        summary = response.css('meta[name="description"]::attr(content)').get()
        if summary:
            return summary.strip()
        
        # 从内容生成摘要
        if content:
            sentences = content.split('。')
            if len(sentences) > 0:
                return sentences[0][:200] + '...' if len(sentences[0]) > 200 else sentences[0]
        
        return None
    
    def _extract_author(self, response):
        """提取作者"""
        selectors = [
            '.author::text',
            '.by-author::text',
            '[rel="author"]::text',
            '.article-author::text',
            '.post-author::text'
        ]
        
        for selector in selectors:
            author = response.css(selector).get()
            if author:
                author = author.strip().replace('作者：', '').replace('by ', '')
                if author and author != '未知':
                    return author
        return "未知作者"
    
    def _extract_publish_time(self, response):
        """提取发布时间"""
        selectors = [
            'time::attr(datetime)',
            '.publish-time::text',
            '.date::text',
            '.post-date::text',
            '[class*="time"]::text',
            '[class*="date"]::text'
        ]
        
        for selector in selectors:
            time_str = response.css(selector).get()
            if time_str:
                cleaned_time = self._clean_time_string(time_str.strip())
                if cleaned_time:
                    return cleaned_time
        return None
    
    def _extract_tags(self, response):
        """提取标签"""
        tag_selectors = [
            '.tags a::text',
            '.tag::text',
            '.keywords a::text',
            '.article-tags a::text'
        ]
        
        tags = []
        for selector in tag_selectors:
            tag_list = response.css(selector).getall()
            tags.extend([tag.strip() for tag in tag_list if tag.strip()])
        
        return list(set(tags))  # 去重
    
    def _extract_read_count(self, response):
        """提取阅读数"""
        selectors = [
            '.read-count::text',
            '.view-count::text',
            '[class*="read"]::text',
            '[class*="view"]::text'
        ]
        
        for selector in selectors:
            count_text = response.css(selector).get()
            if count_text:
                # 提取数字
                import re
                numbers = re.findall(r'\d+', count_text)
                if numbers:
                    return int(numbers[0])
        return 0
    
    def _extract_comment_count(self, response):
        """提取评论数"""
        selectors = [
            '.comment-count::text',
            '.comments-count::text',
            '[class*="comment"]::text'
        ]
        
        for selector in selectors:
            count_text = response.css(selector).get()
            if count_text:
                import re
                numbers = re.findall(r'\d+', count_text)
                if numbers:
                    return int(numbers[0])
        return 0
    
    def _extract_category(self, url):
        """从URL提取分类"""
        category_map = {
            '/tech': '科技',
            '/business': '商业', 
            '/sports': '体育',
            '/entertainment': '娱乐',
            '/ai': '人工智能',
            '/blockchain': '区块链',
            '/finance': '金融',
            '/markets': '市场',
            '/football': '足球',
            '/basketball': '篮球'
        }
        
        for path, category in category_map.items():
            if path in url:
                return category
        
        return '综合'
    
    def _clean_time_string(self, time_str):
        """清理时间字符串"""
        import re
        # 移除多余的空白字符
        time_str = re.sub(r'\s+', ' ', time_str)
        # 移除常见的前缀
        time_str = re.sub(r'^(发布时间|时间|发布于)[：:]?\s*', '', time_str)
        return time_str
    
    def _validate_item(self, item):
        """验证数据项"""
        required_fields = ['title', 'url', 'content']
        
        for field in required_fields:
            if not item.get(field):
                return False
        
        # 检查内容长度
        if len(item['content']) < 50:
            return False
            
        return True
    
    async def _extract_related_links(self, response, item):
        """提取相关文章链接"""
        related_selectors = [
            '.related-articles a::attr(href)',
            '.recommended a::attr(href)',
            '.similar-articles a::attr(href)'
        ]
        
        for selector in related_selectors:
            links = response.css(selector).getall()
            for link in links[:5]:  # 限制数量
                if link:
                    full_url = urljoin(response.url, link)
                    if self._is_valid_news_url(full_url):
                        yield Request(
                            url=full_url,
                            callback=self.parse_news,
                            meta={
                                'category': item['category'],
                                'source': item['source'],
                                'priority': 1  # 低优先级
                            }
                        )