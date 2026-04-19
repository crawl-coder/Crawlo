# -*- coding: UTF-8 -*-
"""
of_week_with_exists_checker - 使用 MySQLExistsChecker 进行数据存在性检查

真实场景测试：
1. 采集列表页
2. 检查数据是否已存在于 ofweek_news 表
3. 只采集不存在的详情页
4. 验证连接池复用和性能优化
"""

from crawlo.spider import Spider
from crawlo import Request, Response
from crawlo.tools.mysql_exists_checker import MySQLExistsChecker
from ..items import OfWeekStandaloneItem


class OfWeekWithExistsCheckerSpider(Spider):
    """of_week 爬虫（使用 MySQLExistsChecker）"""
    name = 'of_week_with_exists_checker'
    allowed_domains = ['ee.ofweek.com']
    
    custom_settings = {
        'LOG_LEVEL': 'INFO',
        'CONCURRENT_REQUESTS': 8,
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_checker = None
        self.total_count = 0
        self.new_count = 0
        self.skip_count = 0
        self._checker_initialized = False
    
    def start_requests(self):
        """生成初始请求"""
        # 生成列表页请求
        max_pages = 2  # 测试用 2 页
        for page in range(1, max_pages + 1):
            url = f'https://ee.ofweek.com/CATList-2800-8100-ee-{page}.html'
            self.logger.info(f"添加列表页: {url}")
            yield Request(url, callback=self.parse_list)
    
    async def parse_list(self, response: Response):
        """解析列表页"""
        # 延迟初始化检查器（在第一次 parse_list 调用时）
        if not self._checker_initialized:
            self.db_checker = MySQLExistsChecker.from_settings(self.crawler.settings)
            self._checker_initialized = True
            self.logger.info("✅ MySQLExistsChecker 已创建，连接池已初始化")
        
        if response.status != 200:
            self.logger.warning(f"页面返回非 200 状态码：{response.status}")
            return
        
        try:
            rows = response.xpath('//div[@class="main_left"]/div[@class="list_model"]/div[@class="model_right model_right2"]')
            self.logger.info(f"列表页找到 {len(rows)} 个条目")
            
            for row in rows:
                try:
                    url = row.xpath('./h3/a/@href').extract_first()
                    title = row.xpath('./h3/a/text()').extract_first()
                    
                    if not url or not title:
                        continue
                    
                    absolute_url = response.urljoin(url)
                    self.total_count += 1
                    
                    # 检查数据是否已存在
                    sql = "SELECT 1 FROM ofweek_news WHERE url = %s LIMIT 1"
                    exists = await self.db_checker.exists(sql, (absolute_url,))
                    
                    if exists:
                        self.skip_count += 1
                        self.logger.debug(f"数据已存在，跳过: {title}")
                    else:
                        self.new_count += 1
                        self.logger.info(f"新数据，采集详情: {title}")
                        yield Request(
                            url=absolute_url,
                            meta={
                                "title": title.strip(),
                                "parent_url": response.url
                            },
                            callback=self.parse_detail
                        )
                except Exception as e:
                    self.logger.error(f"处理条目时出错：{e}")
            
        except Exception as e:
            self.logger.error(f"解析列表页失败：{e}")
    
    async def parse_detail(self, response: Response):
        """解析详情页"""
        try:
            title = response.meta.get('title', '')
            
            # 提取内容
            content_parts = []
            for p in response.xpath('//div[@class="article_content"]//p'):
                text = p.xpath('string(.)').extract_first()
                if text:
                    content_parts.append(text.strip())
            
            content = '\n'.join(content_parts)
            
            # 提取发布时间
            publish_date = response.xpath('//span[@class="article_time"]/text()').extract_first()
            
            # 创建 Item
            item = OfWeekStandaloneItem()
            item['title'] = title
            item['url'] = response.url
            item['content'] = content[:500] if content else ''  # 限制长度
            item['publish_time'] = publish_date.strip() if publish_date else ''
            
            self.logger.info(f"采集成功: {title}")
            yield item
            
        except Exception as e:
            self.logger.error(f"解析详情页失败：{e}, URL: {response.url}")
    
    async def closed(self, reason):
        """爬虫结束时关闭连接池"""
        if self.db_checker:
            await self.db_checker.close()
            self.logger.info("🔒 MySQL 连接池已关闭")
        
        # 输出统计信息
        self.logger.info(f"📊 数据统计:")
        self.logger.info(f"   - 总条目数: {self.total_count}")
        self.logger.info(f"   - 新数据: {self.new_count}")
        self.logger.info(f"   - 跳过: {self.skip_count}")
        self.logger.info(f"   - 关闭原因: {reason}")
