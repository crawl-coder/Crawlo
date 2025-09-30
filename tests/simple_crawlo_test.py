#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单的Crawlo性能测试
"""
import asyncio
import time
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo import Spider, Request
from crawlo.crawler import CrawlerProcess
from crawlo.items import Item, Field

class NewsItem(Item):
    title = Field()
    publish_time = Field()
    url = Field()
    source = Field()
    content = Field()

class OfweekSimpleSpider(Spider):
    name = "ofweek_simple"
    
    def start_requests(self):
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

        # 使用较少的页数进行测试
        max_page = 5
        for page in range(1, max_page + 1):
            url = f"https://ee.ofweek.com/CATList-2800-8100-ee-{page}.html"
            yield Request(url=url, callback=self.parse, headers=headers, cookies=cookies)

    def parse(self, response):
        rows = response.xpath("//div[@class=\"main_left\"]/div[@class=\"list_model\"]/div[@class=\"model_right model_right2\"]")
        
        for row in rows:
            try:
                url = row.xpath("./h3/a/@href").extract_first()
                title = row.xpath("./h3/a/text()").extract_first()

                if not url or not title:
                    continue

                absolute_url = response.urljoin(url)
                if not absolute_url.startswith(("http://", "https://")):
                    continue

                yield Request(
                    url=absolute_url,
                    meta={"title": title.strip() if title else "", "parent_url": response.url},
                    callback=self.parse_detail
                )
            except Exception:
                continue

    def parse_detail(self, response):
        title = response.meta.get("title", "")
        content_elements = response.xpath("//div[@class=\"TRS_Editor\"]|//*[@id=\"articleC\"]")
        if content_elements:
            content = content_elements.xpath(".//text()").extract()
            content = "\n".join([text.strip() for text in content if text.strip()])
        else:
            content = ""

        publish_time = response.xpath("//div[@class=\"time fl\"]/text()").extract_first()
        if publish_time:
            publish_time = publish_time.strip()

        source = response.xpath("//div[@class=\"source-name\"]/text()").extract_first()

        item = NewsItem()
        item["title"] = title.strip() if title else ""
        item["publish_time"] = publish_time if publish_time else ""
        item["url"] = response.url
        item["source"] = source if source else ""
        item["content"] = content

        yield item

async def main():
    start_time = time.time()
    
    process = CrawlerProcess(settings={
        "CONCURRENCY": 8,
        "DOWNLOAD_DELAY": 0.1,
        "LOG_LEVEL": "ERROR",  # 减少日志输出以提高性能
    })
    await process.crawl(OfweekSimpleSpider)
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    print(f"Crawlo执行时间: {execution_time:.2f}秒")

if __name__ == "__main__":
    asyncio.run(main())