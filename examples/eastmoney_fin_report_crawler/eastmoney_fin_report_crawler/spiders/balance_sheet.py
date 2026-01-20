# -*- coding: UTF-8 -*-
"""
爬虫：balance_sheet
"""

from crawlo import Request
from crawlo.spider import Spider

from data.field_mapping import BALANCE_SHEET_FIELD_MAPPING
from utils.tools import generate_pmid, get_v_params, round_if_numeric
from ..items import BalanceSheetItem
from ..settings import HEADERS, STOCKS


class BalanceSheetSpider(Spider):
    """
    爬虫：core_financial_indicators 主要指标

    功能说明：
    - 支持并发爬取
    - 自动去重过滤
    - 错误重试机制
    - 数据管道处理
    """
    name = 'bs'
    allowed_domains = ['datacenter.eastmoney.com', 'datapc.eastmoney.com']
    start_urls = STOCKS

    # 高级配置（可选）
    custom_settings = {
        "DOWNLOAD_DELAY": 5,
        "MYSQL_TABLE": "listed_balance_sheet_of_companies",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.failed_stocks = set()

    def start_requests(self):
        """
        生成初始请求。

        支持自定义请求头、代理、优先级等。
        """
        url = "https://datacenter.eastmoney.com/securities/api/data/get"
        # dates_str = ",".join(f"'{d}'" for d in REPORT_DATES)
        for stock_code in self.start_urls:
            filter_str = f"(SECUCODE=\"{stock_code}\")"
            params = {
                "type": "RPT_F10_FINANCE_GBALANCE",
                "sty": "F10_FINANCE_GBALANCE",
                "filter": filter_str,
                "p": "1",
                "ps": "200",
                "sr": "-1",
                "st": "REPORT_DATE",
                "source": "HSF10",
                "client": "PC",
                # "v": "014887267379124525"
            }
            v_value = get_v_params(params)
            params['v'] = v_value
            yield Request(
                url=url,
                callback=self.parse,
                headers=HEADERS,
                params=params,
                meta={'stock_code': stock_code},
            )

    def parse(self, response):
        try:
            json_data = response.json()
            msg = json_data.get('message')
            stock_code = response.meta.get('stock_code')

            # 关键修改：如果消息不是'ok'，直接返回None，不产生任何item
            if msg != 'ok':
                self.logger.error(f"API返回错误消息: {msg}, URL: {response.url}")
                self.failed_stocks.add(stock_code)
                return None  # 直接返回None，不产生任何数据

            rows = json_data.get('result', {}).get('data', [])

            if not rows:
                stock_code = response.meta.get('stock_code', '未知')
                self.logger.info(f"股票 {stock_code} 无资产负债表数据返回，URL: {response.url}")
                return None  # 返回None，不产生空数据

            for idx, row in enumerate(rows, 1):
                try:
                    item = BalanceSheetItem()

                    # 第一步：填充所有字段
                    for field_name, original_key in BALANCE_SHEET_FIELD_MAPPING.items():
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
                    if report_date != '2025-09-30 00:00:00':
                        self.logger.info(
                            f"第 {idx} 条数据报告期不符合要求，跳过 - stock_code: {stock_code}, report_date: {report_date}, URL: {response.url}"
                        )
                        continue  # 跳过不符合报告期要求的数据

                    # 第三步：生成 pmid
                    item['pmid'] = generate_pmid(stock_code=stock_code, report_date=report_date)

                    yield item

                except Exception as row_e:
                    self.logger.error(
                        f"处理第 {idx} 条数据失败: {row_e}, 数据: {row}, URL: {response.url}",
                        exc_info=True
                    )
                    continue

        except Exception as e:
            self.logger.error(
                f"❌ 响应解析失败 - URL: {response.url}, 状态码: {response.status_code}, 错误: {e}",
                exc_info=True
            )
            return None  # 解析失败时返回None

    def close_spider(self, spider):
        if self.failed_stocks:
            # 可选：写入文件
            with open('balance_sheet_failed_stocks.txt', 'w', encoding='utf-8') as f:
                for stock in sorted(self.failed_stocks):
                    f.write(stock + '\n')
            self.logger.info("失败股票列表已保存至: balance_sheet_failed_stocks.txt")
        else:
            self.logger.info("✅ 所有股票数据采集成功！")

