# -*- coding: UTF-8 -*-
"""
爬虫：of_week_adaptive
使用自适应元素追踪的示例爬虫

此爬虫演示如何使用 Crawlo 的自适应元素追踪功能：
- 使用 adaptive=True 自动保存/更新元素指纹
- 当网站改版导致选择器失效时，自动匹配最相似的元素

使用示例：
    # 1. 直接运行爬虫（首次运行会保存元素指纹）
    python run.py of_week_adaptive
    
    # 2. 或者在 settings.py 中配置定时任务，每天自动运行
    # 首次运行：选择器命中，自动保存指纹到 .crawlo/adaptive_fingerprints.db
    # 网站改版后：选择器失效，自动使用指纹匹配最相似的元素

自适应追踪原理：
    1. 首次爬取：response.xpath('//div[@class="item"]', adaptive=True)
       → 选择器命中，提取元素特征（tag、text、attributes、path等）保存为指纹
       
    2. 网站改版：class 从 "item" 变成 "product"
       → 原选择器失效，但指纹已保存
       
    3. 自动恢复：框架使用指纹在页面中查找最相似的元素
       → 基于文本内容、DOM路径、属性等多维度相似度匹配
       → 返回匹配度最高的元素，爬虫继续正常工作

关键配置（custom_settings）：
    ADAPTIVE_STORAGE_BACKEND = 'sqlite'   # 存储后端：sqlite 或 redis
    ADAPTIVE_SIMILARITY_THRESHOLD = 0.0   # 最低相似度阈值（0-100）
"""

from crawlo.spider import Spider
from crawlo import Request, Response
from ..items import OfWeekStandaloneItem


class OfWeekAdaptiveSpider(Spider):
    """使用自适应元素追踪的 ofweek 爬虫"""
    name = 'of_week_adaptive'
    allowed_domains = ['ee.ofweek.com']
    start_urls = ['https://ee.ofweek.com/']
    
    # 自定义设置
    custom_settings = {
        # 自适应选择器：只要 css/xpath 传了 adaptive=True 就会自动启用
        'ADAPTIVE_STORAGE_BACKEND': 'sqlite',
        'ADAPTIVE_SQLITE_PATH': '.crawlo/adaptive_fingerprints.db',
        'ADAPTIVE_SIMILARITY_THRESHOLD': 0.0,
    }

    def start_requests(self):
        """生成初始请求"""
        max_pages = 5
        start_urls = []
        for page in range(1, max_pages + 1):
            url = f'https://ee.ofweek.com/CATList-2800-8100-ee-{page}.html'
            start_urls.append(url)
        self.logger.info(f"生成了 {len(start_urls)} 个起始URL")

        for url in start_urls:
            yield Request(url, callback=self.parse, dont_filter=True)

    def parse(self, response: Response):
        """解析列表页 - 使用自适应元素追踪"""
        # 检查响应状态
        if response.status_code != 200:
            self.logger.warning(f"页面返回非200状态码: {response.status_code}, URL: {response.url}")
            return

        # 检查页面内容是否为空
        if not response.text or len(response.text.strip()) == 0:
            self.logger.warning(f"页面内容为空: {response.url}")
            return

        # ================== 使用自适应元素追踪提取数据 ==================
        try:
            # 使用 adaptive=True 启用自适应追踪
            # 选择器命中时自动保存指纹，失效时自动匹配相似元素
            rows = response.xpath(
                '//div[@class="main_left"]/div[@class="list_model"]/div[@class="model_right model_right2"]',
                adaptive=True,
                identifier='list_item_selector'  # 自定义标识符，用于指纹存储
            )
            self.logger.info(f"在页面 {response.url} 中找到 {len(rows)} 个条目")

            for row in rows:
                try:
                    # 提取URL和标题（详情页选择器也使用自适应追踪）
                    url = row.xpath('./h3/a/@href', adaptive=True, identifier='detail_link').extract_first()
                    title = row.xpath('./h3/a/text()', adaptive=True, identifier='detail_title').extract_first()

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
        """解析详情页 - 使用自适应元素追踪"""
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

            # 使用自适应元素追踪提取内容
            content_elements = response.xpath(
                '//div[@class="TRS_Editor"]|//*[@id="articleC"]',
                adaptive=True,
                identifier='article_content'
            )
            if content_elements:
                content = content_elements.xpath('.//text()').extract()
                content = '\n'.join([text.strip() for text in content if text.strip()])
            else:
                content = ''
                self.logger.warning(f"未找到内容区域: {response.url}")

            # 使用自适应元素追踪提取发布时间
            publish_time = response.xpath(
                '//div[@class="time fl"]/text()',
                adaptive=True,
                identifier='publish_time'
            ).extract_first()
            if publish_time:
                publish_time = publish_time.strip()

            # 使用自适应元素追踪提取来源
            source = response.xpath(
                '//div[@class="source-name"]/text()',
                adaptive=True,
                identifier='article_source'
            ).extract_first()

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
