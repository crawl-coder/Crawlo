# -*- coding: UTF-8 -*-
"""
financial_reports_spider.spiders.core_financial_indicators
=======================================
由 `crawlo genspider` 命令生成的爬虫。
基于 Crawlo 框架，支持异步并发、分布式爬取等功能。

使用示例：
    crawlo crawl core_financial_indicators
"""

from crawlo.spider import Spider
from crawlo import Request

from utils.tools import generate_pmid, get_v_params, round_if_numeric
from ..items import CoreFinancialIndicatorsItem
from ..settings import HEADERS, STOCKS, REPORT_DATE_FILTER
from data.field_mapping import CORE_FIELD_MAPPING


class CoreFinancialIndicatorsSpider(Spider):
    """
    爬虫：core_financial_indicators 主要指标

    功能说明：
    - 支持并发爬取
    - 自动去重过滤
    - 错误重试机制（含业务错误重试）
    - 失败股票收集与报告
    - 数据管道处理
    """
    name = 'core_financial_indicators'
    allowed_domains = ['datacenter.eastmoney.com', 'datapc.eastmoney.com']
    # start_urls = STOCKS

    # 高级配置（可选）
    custom_settings = {
        "DOWNLOAD_DELAY": 5,
        "MYSQL_TABLE": "listed_finance_and_taxation_report",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.failed_stocks = set()  # 用于收集最终失败的股票代码

    def start_requests(self):
        """
        生成初始请求。
        """
        url = "https://datacenter.eastmoney.com/securities/api/data/get"
        for stock_code in STOCKS:
            params = {
                "type": "RPT_F10_FINANCE_MAINFINADATA",
                "sty": "APP_F10_MAINFINADATA",
                "quoteColumns": "",
                "filter": f"(SECUCODE=\"{stock_code}\")",
                "p": "1",
                "ps": "200",
                "sr": "-1",
                "st": "REPORT_DATE",
                "source": "HSF10",
                "client": "PC",
                # "v": "0735573993472252"
            }
            v_value = get_v_params(params)
            params['v'] = v_value
            yield Request(
                url=url,
                callback=self.parse,
                headers=HEADERS,
                params=params,
                meta={'stock_code': stock_code}  # 👈 传递股票代码
            )

    def parse(self, response):
        stock_code = response.meta.get('stock_code', 'UNKNOWN')
        retry_times = response.meta.get('retry_times', 0)
        max_retry_times = 3

        try:
            json_data = response.json()
            msg = json_data.get('message', '').strip()

            # 检查 API 是否返回成功
            if msg != 'ok':
                self.logger.warning(
                    f"股票 {stock_code} API 返回非 'ok' 消息: '{msg}' (重试 {retry_times}/{max_retry_times}), URL: {response.url}"
                )
                if retry_times < max_retry_times:
                    # 重试：复用原请求，增加重试次数
                    new_request = response.request.replace(
                        meta={
                            'stock_code': stock_code,
                            'retry_times': retry_times + 1
                        }
                    )
                    yield new_request
                else:
                    self.logger.error(f"股票 {stock_code} 达到最大重试次数，标记为失败。最终消息: {msg}")
                    self.failed_stocks.add(stock_code)
                return

            rows = json_data.get('result', {}).get('data', [])
            if not rows:
                self.logger.info(f"股票 {stock_code} 无主要财务指标数据返回")
                # 注意：这里不视为“失败”，因为可能是正常无数据（如新上市）
                # 如果业务上认为“必须有数据”，则取消下面注释：
                # self.failed_stocks.add(stock_code)
                return

            for idx, row in enumerate(rows, 1):
                try:
                    item = CoreFinancialIndicatorsItem()
                    for field_name, original_key in CORE_FIELD_MAPPING.items():
                        # item[field_name] = row.get(original_key)
                        raw_value = row.get(original_key)
                        item[field_name] = round_if_numeric(raw_value, decimal_places=4)

                    stock_code_item = item.get('stock_code')
                    report_date = item.get('report_date')

                    if not stock_code_item or not report_date:
                        self.logger.warning(
                            f"股票 {stock_code} 第 {idx} 条数据缺失关键字段，跳过 - stock_code: {stock_code_item}, report_date: {report_date}"
                        )
                        continue

                    # 检查报告期是否为指定日期
                    if report_date != REPORT_DATE_FILTER:
                        self.logger.info(
                            f"股票 {stock_code} 第 {idx} 条数据报告期不符合要求，跳过 - stock_code: {stock_code_item}, report_date: {report_date}"
                        )
                        continue  # 跳过不符合报告期要求的数据

                    item['pmid'] = generate_pmid(stock_code=stock_code_item, report_date=report_date)
                    yield item

                except Exception as row_e:
                    self.logger.error(
                        f"处理股票 {stock_code} 第 {idx} 条数据失败: {row_e}, 数据: {row}",
                        exc_info=True
                    )
                    continue

        except Exception as e:
            self.logger.error(
                f"❌ 股票 {stock_code} 响应解析失败 - 状态码: {response.status_code}, URL: {response.url}, 错误: {e}",
                exc_info=True
            )
            if retry_times < max_retry_times:
                yield response.request.replace(
                    meta={
                        'stock_code': stock_code,
                        'retry_times': retry_times + 1
                    }
                )
            else:
                self.failed_stocks.add(stock_code)

    def close(self, reason):
        """
        爬虫关闭时调用，输出失败股票列表
        """
        if self.failed_stocks:
            self.logger.info("=" * 60)
            self.logger.info("❌ 以下股票的主要财务指标采集失败（已达最大重试次数）:")
            for stock in sorted(self.failed_stocks):
                self.logger.info(f"  - {stock}")
            self.logger.info(f"总计失败股票数量: {len(self.failed_stocks)}")
            self.logger.info("=" * 60)

            # 保存到文件
            with open('failed_core_financial_stocks.txt', 'w', encoding='utf-8') as f:
                for stock in sorted(self.failed_stocks):
                    f.write(stock + '\n')
            self.logger.info("失败股票列表已保存至: failed_core_financial_stocks.txt")
        else:
            self.logger.info("✅ 所有股票的主要财务指标数据采集成功！")