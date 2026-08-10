import os

from crawlo import Item, Request, Spider


class SimpleOfweekSpider(Spider):
    name = "simple_ofweek"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base = os.environ.get("OFWEEK_BASE_URL", "https://ee.ofweek.com")
        self.start_urls = [f"{base}/CATList-2800-8100-ee-1.html"]

    def parse(self, response):
        for row in response.xpath('//div[@class="model_right model_right2"]'):
            href = row.xpath("./h3/a/@href").get()
            title = row.xpath("./h3/a/text()").get("").strip()
            if href:
                yield Request(response.urljoin(href), self.parse_detail, meta={"title": title})

    def parse_detail(self, response):
        title = response.meta.get("title") or response.xpath('//h1/text()').get("").strip()
        yield Item(title=title, url=response.url)
