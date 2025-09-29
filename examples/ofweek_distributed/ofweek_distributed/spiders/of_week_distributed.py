# -*- coding: UTF-8 -*-
"""
ofweek_distributed.spiders.of_week_distributed
=======================================
由 `crawlo genspider` 命令生成的爬虫。
基于 Crawlo 框架，支持异步并发、分布式爬取等功能。

使用示例：
    crawlo crawl of_week_distributed
"""

from urllib.parse import urljoin

from crawlo.spider import Spider
from crawlo import Request
from crawlo.utils.log import get_logger
from ..items import NewsItem


class OfweekdistributedSpider(Spider):
    """
    爬虫：of_week_distributed
    
    功能说明：
    - 支持并发爬取
    - 自动去重过滤
    - 错误重试机制
    - 数据管道处理
    
    运行模式演进说明：
    
    阶段1：基础单机模式
    - 使用内存队列和内存去重过滤器
    - 适合开发测试和小规模数据采集
    - 配置简单，无需额外依赖
    
    阶段2：单机模式增强
    - 增加持久化去重机制（如文件存储）
    - 优化内存使用，处理大数据量
    
    阶段3：分布式模式
    - 使用 Redis 队列和去重过滤器
    - 支持多节点协同工作
    - 需要 Redis 环境支持
    
    阶段4：分布式模式优化
    - 配置 Redis 连接池
    - 优化去重性能
    - 增加监控和故障恢复机制
    """
    name = 'of_week_distributed'  # 修改为与类名一致
    allowed_domains = ['ee.ofweek.com']
    start_urls = ['https://ee.ofweek.com/']
    
    # 高级配置（可选）
    # custom_settings = {
    #     'DOWNLOAD_DELAY': 1.0,  # Can reduce delay in distributed environment
    #     'CONCURRENCY': 16,  # Higher concurrency in distributed mode
    #     'MAX_RETRY_TIMES': 5,  # Increase retry count in distributed environment
    #     'FILTER_CLASS': 'crawlo.filters.aioredis_filter.AioRedisFilter',  # Redis deduplication
    #     'SCHEDULER': 'crawlo.core.scheduler.Scheduler',  # Redis scheduler
    # }

    def start_requests(self):
        """
        生成初始请求。
        
        支持自定义请求头、代理、优先级等。
        """
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Pragma": "no-cache",
            "Referer": "https://ee.ofweek.com/CATList-2800-8100-ee-2.html",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
            "sec-ch-ua": "\"Not;A=Brand\";v=\"99\", \"Google Chrome\";v=\"139\", \"Chromium\";v=\"139\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\""
        }
        cookies = {
            "__utmz": "57425525.1730117117.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none)",
            "Hm_lvt_abe9900db162c6d089cdbfd107db0f03": "1739244841",
            "Hm_lvt_af50e2fc51af73da7720fb324b88a975": "1740100727",
            "JSESSIONID": "FEA96D3B5FC31350B2285E711BF2A541",
            "Hm_lvt_28a416fcfc17063eb9c4f9bb1a1f5cda": "1757477622",
            "HMACCOUNT": "08DF0D235A291EAA",
            "__utma": "57425525.2080994505.1730117117.1747970718.1757477622.50",
            "__utmc": "57425525",
            "__utmt": "1",
            "__utmb": "57425525.2.10.1757477622",
            "Hm_lpvt_28a416fcfc17063eb9c4f9bb1a1f5cda": "1757477628",
            "index_burying_point": "c64d6c31e69d560efe319cc9f8be279f"
        }

        # 更可靠的翻页方案：先检查网站实际的页数范围
        # 根据网站实际情况调整页数范围，避免请求不存在的页面
        max_page = 20  # 减少页数以便测试
        start_urls = []
        for page in range(1, max_page + 1):
            url = f'https://ee.ofweek.com/CATList-2800-8100-ee-{page}.html'
            start_urls.append(url)

        self.logger.info(f"生成了 {len(start_urls)} 个起始URL")

        # 使用本地的 start_urls 变量而不是 self.start_urls
        for url in start_urls:
            self.logger.info(f"添加起始URL: {url}")
            try:
                yield Request(
                    url=url,
                    callback=self.parse,
                    headers=headers,
                    cookies=cookies
                )
            except Exception as e:
                self.logger.error(f"创建请求失败: {url}, 错误: {e}")

    def parse(self, response):
        """
        解析响应的主方法。

        Args:
            response: 响应对象，包含页面内容和元数据

        Yields:
            Request: 新的请求对象（用于深度爬取）
            Item: 数据项对象（用于数据存储）
        """
        self.logger.info(f'正在解析页面: {response.url}')

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
            rows = response.xpath(
                '//div[@class="main_left"]/div[@class="list_model"]/div[@class="model_right model_right2"]')
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
                    absolute_url = urljoin(response.url, url)

                    # 验证URL格式
                    if not absolute_url.startswith(('http://', 'https://')):
                        self.logger.warning(f"无效的URL格式，跳过: {absolute_url}")
                        continue

                    self.logger.info(f"提取到详情页链接: {absolute_url}, 标题: {title}")
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

        # ================== 翻页处理 ==================
        # 如果需要额外的翻页逻辑，可以在这里添加
        # 当前方案通过 start_requests 生成所有页面URL，更加可靠

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
            item = NewsItem()
            item['title'] = title.strip() if title else ''
            item['publish_time'] = publish_time if publish_time else ''
            item['url'] = response.url
            item['source'] = source if source else ''
            item['content'] = content

            # 验证必要字段
            if not item['title']:
                self.logger.warning(f"详情页缺少标题: {response.url}")

            self.logger.info(f"成功提取详情页数据: {item['title']}")
            yield item

        except Exception as e:
            self.logger.error(f"解析详情页 {response.url} 时出错: {e}")