# -*- coding: UTF-8 -*-
"""
爬虫：of_week
"""

from crawlo.spider import Spider
from crawlo import Request, Response
from ..items import OfWeekStandaloneItem


class OfWeekSpider(Spider):
    """of_week 爬虫"""
    name = 'of_week'
    allowed_domains = ['ee.ofweek.com']
    start_urls = ['https://ee.ofweek.com/']
    
    # 自定义设置（可选）
    custom_settings = {}

    def start_requests(self):
        """生成初始请求"""
        max_pages = 50
        start_urls = []
        for page in range(1, max_pages + 1):
            url = f'https://ee.ofweek.com/CATList-2800-8100-ee-{page}.html'
            start_urls.append(url)
        self.logger.info(f"生成了 {len(start_urls)} 个起始URL")

        for url in start_urls:
            yield Request(url, callback=self.parse, dont_filter=True)

    def parse(self, response: Response):
        """解析响应"""
        # 检查响应状态
        if response.status_code != 200:
            self.logger.warning(f"页面返回非200状态码: {response.status_code}, URL: {response.url}")
            return

        # 检查页面内容是否为空
        if not response.text or len(response.text.strip()) == 0:
            self.logger.warning(f"页面内容为空: {response.url}")
            return

        # ================== 数据提取 ==================
        try:
            rows = response.xpath('//div[@class="main_left"]/div[@class="list_model"]/div[@class="model_right model_right2"]')
            self.logger.info(f"在页面 {response.url} 中找到 {len(rows)} 个条目")

            for row in rows:
                try:
                    # 提取URL和标题
                    url = row.xpath('./h3/a/@href').extract_first()
                    title = row.xpath('./h3/a/text()').extract_first()

                    # 容错处理
                    if not url:
                        self.logger.warning(f"条目缺少URL，跳过: {row.get()}")
                        continue

                    if not title:
                        self.logger.warning(f"条目缺少标题，跳过: {row.get()}")
                        continue

                    # 确保 URL 是绝对路径
                    absolute_url = response.urljoin(url)

                    # 验证URL格式
                    if not absolute_url.startswith(('http://', 'https://')):
                        self.logger.warning(f"无效的URL格式，跳过: {absolute_url}")
                        continue

                    # self.logger.info(f"提取到详情页链接: {absolute_url}, 标题: {title}")
                    yield Request(
                        url=absolute_url,
                        meta={
                            "title": title.strip() if title else '',
                            "parent_url": response.url
                        },
                        callback=self.parse_detail
                    )
                except Exception as e:
                    self.logger.error(f"处理条目时出错: {e}, 条目内容: {row.get()}")
                    continue

        except Exception as e:
            self.logger.error(f"解析页面 {response.url} 时出错: {e}")

    def parse_detail(self, response):
        """
        解析详情页面的方法（可选）。

        用于处理从列表页跳转而来的详情页。
        """
        self.logger.info(f'正在解析详情页: {response.url}')

        # 检查响应状态
        if response.status_code != 200:
            self.logger.warning(f"详情页返回非200状态码: {response.status_code}, URL: {response.url}")
            return

        # 检查页面内容是否为空
        if not response.text or len(response.text.strip()) == 0:
            self.logger.warning(f"详情页内容为空: {response.url}")
            return

        try:
            title = response.meta.get('title', '')

            # 提取内容，增加容错处理
            content_elements = response.xpath('//div[@class="TRS_Editor"]|//*[@id="articleC"]')
            if content_elements:
                content = content_elements.xpath('.//text()').extract()
                content = '\n'.join([text.strip() for text in content if text.strip()])
            else:
                content = ''
                self.logger.warning(f"未找到内容区域: {response.url}")

            # 提取发布时间
            publish_time = response.xpath('//div[@class="time fl"]/text()').extract_first()
            if publish_time:
                publish_time = publish_time.strip()

            source = response.xpath('//div[@class="source-name"]/text()').extract_first()

            # 创建数据项
            item = OfWeekStandaloneItem()
            item['title'] = title.strip() if title else ''
            item['publish_time'] = publish_time if publish_time else ''
            item['url'] = response.url
            item['source'] = source if source else ''
            item['content'] = content

            # 验证必要字段
            if not item['title']:
                self.logger.warning(f"详情页缺少标题: {response.url}")

            yield item

        except Exception as e:
            self.logger.error(f"解析详情页 {response.url} 时出错: {e}")