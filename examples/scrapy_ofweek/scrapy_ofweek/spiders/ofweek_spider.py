# -*- coding: UTF-8 -*-
"""
Scrapy 爬虫：ofweek_spider
=========================

此爬虫与 Crawlo 的 of_week_standalone 使用完全相同的逻辑：
- 相同的目标网站和URL
- 相同的页面解析XPath
- 相同的数据提取逻辑
- 相同的并发和延迟配置

用于公平对比 Scrapy 和 Crawlo 的性能差异。
"""

import scrapy
from scrapy_ofweek.items import NewsItem


class OfweekSpider(scrapy.Spider):
    """
    OFweek电子工程网爬虫（Scrapy版本）
    
    与 Crawlo 版本的对等实现，确保测试公平性：
    - 相同的起始URL数量（2页列表）
    - 相同的headers和cookies
    - 相同的XPath选择器
    - 相同的数据提取逻辑
    """
    name = 'ofweek_spider'
    allowed_domains = ['ee.ofweek.com']
    
    # 自定义配置（确保与 Crawlo 一致）
    custom_settings = {
        'CONCURRENT_REQUESTS': 8,  # 与 Crawlo 的 CONCURRENCY=8 一致
        'DOWNLOAD_DELAY': 1.0,     # 与 Crawlo 的 DOWNLOAD_DELAY=1.0 一致
        'LOG_LEVEL': 'INFO',
    }
    
    def start_requests(self):
        """生成初始请求（与 Crawlo 完全相同的逻辑）"""
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
        
        # 中等规模测试：爬取30页（与 Crawlo 版本完全一致）
        max_page = 30
        start_urls = []
        for page in range(1, max_page + 1):
            url = f'https://ee.ofweek.com/CATList-2800-8100-ee-{page}.html'
            start_urls.append(url)
        
        self.logger.info(f"生成了 {len(start_urls)} 个起始URL")
        
        for url in start_urls:
            self.logger.info(f"添加起始URL: {url}")
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                headers=headers,
                cookies=cookies,
                dont_filter=True
            )
        
        self.logger.info("start_requests方法执行完成")
    
    def parse(self, response):
        """解析列表页（与 Crawlo 完全相同的逻辑）"""
        self.logger.info(f'正在解析页面: {response.url}')
        
        if response.status != 200:
            self.logger.warning(f"页面返回非200状态码: {response.status}, URL: {response.url}")
            return
        
        if not response.text or len(response.text.strip()) == 0:
            self.logger.warning(f"页面内容为空: {response.url}")
            return
        
        try:
            rows = response.xpath(
                '//div[@class="main_left"]/div[@class="list_model"]/div[@class="model_right model_right2"]')
            self.logger.info(f"在页面 {response.url} 中找到 {len(rows)} 个条目")
            
            for row in rows:
                try:
                    url = row.xpath('./h3/a/@href').extract_first()
                    title = row.xpath('./h3/a/text()').extract_first()
                    
                    if not url:
                        self.logger.warning(f"条目缺少URL，跳过")
                        continue
                    
                    if not title:
                        self.logger.warning(f"条目缺少标题，跳过")
                        continue
                    
                    absolute_url = response.urljoin(url)
                    
                    if not absolute_url.startswith(('http://', 'https://')):
                        self.logger.warning(f"无效的URL格式，跳过: {absolute_url}")
                        continue
                    
                    self.logger.info(f"提取到详情页链接: {absolute_url}, 标题: {title}")
                    yield scrapy.Request(
                        url=absolute_url,
                        meta={
                            "title": title.strip() if title else '',
                            "parent_url": response.url
                        },
                        callback=self.parse_detail
                    )
                except Exception as e:
                    self.logger.error(f"处理条目时出错: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"解析页面 {response.url} 时出错: {e}")
    
    def parse_detail(self, response):
        """解析详情页（与 Crawlo 完全相同的逻辑）"""
        self.logger.info(f'正在解析详情页: {response.url}')
        
        if response.status != 200:
            self.logger.warning(f"详情页返回非200状态码: {response.status}, URL: {response.url}")
            return
        
        if not response.text or len(response.text.strip()) == 0:
            self.logger.warning(f"详情页内容为空: {response.url}")
            return
        
        try:
            title = response.meta.get('title', '')
            
            content_elements = response.xpath('//div[@class="TRS_Editor"]|//*[@id="articleC"]')
            if content_elements:
                content = content_elements.xpath('.//text()').extract()
                content = '\n'.join([text.strip() for text in content if text.strip()])
            else:
                content = ''
                self.logger.warning(f"未找到内容区域: {response.url}")
            
            publish_time = response.xpath('//div[@class="time fl"]/text()').extract_first()
            if publish_time:
                publish_time = publish_time.strip()
            
            source = response.xpath('//div[@class="source-name"]/text()').extract_first()
            
            item = NewsItem()
            item['title'] = title.strip() if title else ''
            item['publish_time'] = publish_time if publish_time else ''
            item['url'] = response.url
            item['source'] = source if source else ''
            item['content'] = content
            
            if not item['title']:
                self.logger.warning(f"详情页缺少标题: {response.url}")
            
            self.logger.info(f"成功提取详情页数据: {item['title']}")
            yield item
        
        except Exception as e:
            self.logger.error(f"解析详情页 {response.url} 时出错: {e}")
