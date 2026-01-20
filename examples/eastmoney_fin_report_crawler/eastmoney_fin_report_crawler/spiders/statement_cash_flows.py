# -*- coding: UTF-8 -*-
"""
financial_reports_spider.spiders.core_financial_indicators
=======================================
由 `crawlo genspider` 命令生成的爬虫。
基于 Crawlo 框架，支持异步并发、分布式爬取等功能。

使用示例：
    crawlo crawl core_financial_indicators
"""

from crawlo import Request
from crawlo.spider import Spider

from data.field_mapping import CASHFLOW_STATEMENT_FIELD_MAPPING
from utils.tools import generate_pmid, get_v_params, round_if_numeric
from ..items import CashflowStatementItem
from ..settings import HEADERS, STOCKS, REPORT_DATE_FILTER


class CashFlowStatementSpider(Spider):
    """
    爬虫：cash_flow_statement 主要指标

    功能说明：
    - 支持并发爬取
    - 自动去重过滤
    - 错误重试机制
    - 数据管道处理
    """
    name = 'cash_flow_statement'
    allowed_domains = ['datacenter.eastmoney.com']
    # start_urls = STOCKS

    # 高级配置（可选）
    custom_settings = {
        "DOWNLOAD_DELAY": 5,
        "MYSQL_TABLE": "listed_statement_of_cash_flows",
    }

    def start_requests(self):
        """
        生成初始请求。

        支持自定义请求头、代理、优先级等。
        """
        url = "https://datacenter.eastmoney.com/securities/api/data/get"
        # dates_str = ",".join(f"'{d}'" for d in REPORT_DATES_ALL)
        for stock_code in STOCKS:
            filter_str = f"(SECUCODE=\"{stock_code}\")"
            params = {
                "type": "RPT_F10_FINANCE_GCASHFLOW",
                "sty": "APP_F10_GCASHFLOW",
                "filter": filter_str,#f"(SECUCODE=\"{stock_code}\")(REPORT_DATE in ('2025-03-31','2024-12-31','2024-09-30','2024-06-30','2024-03-31'))",
                "p": "1",
                "ps": "200",
                "sr": "-1",
                "st": "REPORT_DATE",
                "source": "HSF10",
                "client": "PC",
                "v": "016633324830707397"
            }
            v_value = get_v_params(params)
            params['v'] = v_value
            yield Request(
                url=url,
                callback=self.parse,
                headers=HEADERS,
                params=params
            )

    def parse(self, response):
        try:
            json_data = response.json()
            rows = json_data.get('result', {}).get('data', [])

            if not rows:
                self.logger.info(f"无数据返回，URL: {response.url}")
                return

            for idx, row in enumerate(rows, 1):
                # print(row)
                try:
                    item = CashflowStatementItem()

                    # 第一步：填充所有字段
                    for field_name, original_key in CASHFLOW_STATEMENT_FIELD_MAPPING.items():
                        # item[field_name] = row.get(original_key)

                        raw_value = row.get(original_key)
                        item[field_name] = round_if_numeric(raw_value, decimal_places=4)

                    # 第二步：校验关键字段
                    stock_code = item.get('stock_code')
                    report_date = item.get('report_date')

                    if not stock_code or not report_date:
                        self.logger.warning(
                            f"第 {idx} 条数据缺失关键字段，跳过 - stock_code: {stock_code}, report_date: {report_date}, URL: {response.url}"
                        )
                        continue  # 跳过该条脏数据

                    # 检查报告期是否为指定日期
                    if report_date != REPORT_DATE_FILTER:
                        self.logger.info(
                            f"第 {idx} 条数据报告期不符合要求，跳过 - stock_code: {stock_code}, report_date: {report_date}, URL: {response.url}"
                        )
                        continue  # 跳过不符合报告期要求的数据

                    # 第三步：生成 pmid（此时字段已填充，安全）
                    item['pmid'] = generate_pmid(stock_code=stock_code, report_date=report_date)

                    yield item

                except Exception as row_e:
                    # 单行数据错误，记录并跳过，不影响其他行
                    self.logger.error(
                        f"处理第 {idx} 条数据失败: {row_e}, 数据: {row}, URL: {response.url}",
                        exc_info=True
                    )
                    continue  # 跳过当前行，继续处理下一条

        except Exception as e:
            # 整体解析失败（如 JSON 格式错误）
            self.logger.error(
                f"❌ 响应解析失败 - URL: {response.url}, 状态码: {response.status_code}, 错误: {e}",
                exc_info=True
            )

    def parse_detail(self, response):
        """
        解析详情页面的方法（可选）。

        用于处理从列表页跳转而来的详情页。
        """
        self.logger.info(f'正在解析详情页: {response.url}')

        # parent_url = response.meta.get('parent_url', '')
        #
        # yield {
        #     'title': response.xpath('//h1/text()').get(default=''),
        #     'content': '\n'.join(response.xpath('//div[@class="content"]//text()').getall()),
        #     'url': response.url,
        #     'parent_url': parent_url,
        #     'publish_time': response.xpath('//time/@datetime').get(),
        # }

        pass