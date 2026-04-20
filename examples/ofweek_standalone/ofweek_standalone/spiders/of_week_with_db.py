# -*- coding: UTF-8 -*-
"""
of_week_spider_with_db - 演示如何在 of_week.py 中使用 mysql_helper
"""

from crawlo.spider import Spider
from crawlo import Request, Response
from ..items import OfWeekStandaloneItem
from crawlo.utils.db.mysql_helper import get_mysql_helper


class OfWeekWithDBSpider(Spider):
    """of_week 爬虫（带数据库去重）"""
    name = 'of_week_with_db'
    allowed_domains = ['ee.ofweek.com']
    start_urls = ['https://ee.ofweek.com/']
    
    # 自定义设置
    custom_settings = {}

    def __init__(self, *args, **kwargs):
        """初始化数据库助手"""
        super().__init__(*args, **kwargs)
        self.db_helper = None
    
    def start_requests(self):
        """生成初始请求"""
        max_pages = 5
        start_urls = []
        for page in range(1, max_pages + 1):
            url = f'https://ee.ofweek.com/CATList-2800-8100-ee-{page}.html'
            start_urls.append(url)
        self.logger.info(f"生成了 {len(start_urls)} 个起始 URL")

        for url in start_urls:
            yield Request(url, callback=self.parse, dont_filter=True)

    def parse(self, response: Response):
        """解析响应"""
        if response.status != 200:
            self.logger.warning(f"页面返回非 200 状态码：{response.status}, URL: {response.url}")
            return

        if not response.text or len(response.text.strip()) == 0:
            self.logger.warning(f"页面内容为空：{response.url}")
            return

        try:
            rows = response.xpath('//div[@class="main_left"]/div[@class="list_model"]/div[@class="model_right model_right2"]')
            self.logger.info(f"在页面 {response.url} 中找到 {len(rows)} 个条目")

            for row in rows:
                try:
                    url = row.xpath('./h3/a/@href').extract_first()
                    title = row.xpath('./h3/a/text()').extract_first()

                    if not url:
                        self.logger.warning(f"条目缺少 URL，跳过：{row.get()}")
                        continue

                    if not title:
                        self.logger.warning(f"条目缺少标题，跳过：{row.get()}")
                        continue

                    absolute_url = response.urljoin(url)

                    if not absolute_url.startswith(('http://', 'https://')):
                        self.logger.warning(f"无效的 URL 格式，跳过：{absolute_url}")
                        continue

                    yield Request(
                        url=absolute_url,
                        meta={
                            "title": title.strip() if title else '',
                            "parent_url": response.url
                        },
                        callback=self.parse_detail
                    )
                except Exception as e:
                    self.logger.error(f"处理条目时出错：{e}, 条目内容：{row.get()}")
                    continue

        except Exception as e:
            self.logger.error(f"解析页面 {response.url} 时出错：{e}")

    async def parse_detail(self, response):
        """解析详情页面（异步方法，支持数据库操作）"""
        # 【关键】在首次使用时初始化 MySQLHelper（直接传入 spider，自动获取配置）
        if self.db_helper is None:
            self.db_helper = await get_mysql_helper(spider=self)
            self.logger.info("MySQLHelper 初始化成功")
        
        self.logger.info(f'正在解析详情页：{response.url}')

        if response.status != 200:
            self.logger.warning(f"详情页返回非 200 状态码：{response.status}, URL: {response.url}")
            return

        if not response.text or len(response.text.strip()) == 0:
            self.logger.warning(f"详情页内容为空：{response.url}")
            return

        try:
            # 【关键】使用数据库检查数据是否已存在（表名从 custom_settings 获取）
            table_name = self.crawler.settings.get('MYSQL_TABLE', 'ofweek_articles')
            exists = await self.db_helper.exists(
                table_name,
                {"url": response.url}
            )
            
            if exists:
                self.logger.info(f"数据已存在，跳过：{response.url}")
                return
            
            self.logger.info(f"数据不存在，继续采集：{response.url}")

            title = response.meta.get('title', '')

            content_elements = response.xpath('//div[@class="TRS_Editor"]|//*[@id="articleC"]')
            if content_elements:
                content = content_elements.xpath('.//text()').extract()
                content = '\n'.join([text.strip() for text in content if text.strip()])
            else:
                content = ''
                self.logger.warning(f"未找到内容区域：{response.url}")

            publish_time = response.xpath('//div[@class="time fl"]/text()').extract_first()
            if publish_time:
                publish_time = publish_time.strip()

            source = response.xpath('//div[@class="source_name"]/text()').extract_first()

            item = OfWeekStandaloneItem()
            item['title'] = title.strip() if title else ''
            item['publish_time'] = publish_time if publish_time else ''
            item['url'] = response.url
            item['source'] = source if source else ''
            item['content'] = content

            if not item['title']:
                self.logger.warning(f"详情页缺少标题：{response.url}")

            yield item

        except Exception as e:
            self.logger.error(f"解析详情页 {response.url} 时出错：{e}")
