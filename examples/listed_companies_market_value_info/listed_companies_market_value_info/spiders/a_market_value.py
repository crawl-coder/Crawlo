# -*- coding: UTF-8 -*-
"""
爬虫：a_market_value_spider A股上市公司市值数据
"""

import hashlib
import datetime
import os
from crawlo import Request
from crawlo.spider import Spider

from listed_companies_market_value_info.utils.stock_loader import load_a_stocks_market
from ..items import ListedCompaniesMarketValueItem


class AMarketValueSpider(Spider):
    """A股上市公司市值数据爬虫"""

    name = 'a_market_value'
    allowed_domains = ['push2.eastmoney.com']

    def start_requests(self):
        """生成初始请求"""
        STOCKS = []
        
        if self.crawler and self.crawler.settings.get('STOCKS'):
            stocks_config = self.crawler.settings.get('STOCKS')
            for stock_line in stocks_config[:100]:
                if '-' in stock_line:
                    parts = stock_line.split('-', 1)
                    stock_code = parts[0].strip()
                    stock_name = parts[1].strip() if len(parts) > 1 else f'股票{stock_code}'
                    STOCKS.append((stock_code, stock_name))
            self.logger.info(f'从配置文件加载了 {len(STOCKS)} 只股票代码（前100只）')
        
        for stock_code, stock_name in STOCKS:
            # 构造请求URL，使用东财的API接口
            url = "https://push2.eastmoney.com/api/qt/stock/get"

            # 提取不带后缀的股票代码用于API请求
            clean_stock_code = stock_code.split('.')[0] if '.' in stock_code else stock_code

            # 根据股票代码前缀确定交易所
            if clean_stock_code.startswith('6'):
                stock_code_api = f'1.{clean_stock_code}'  # 上交所使用1开头
            elif clean_stock_code.startswith(('0', '3', '9')):
                stock_code_api = f'0.{clean_stock_code}'  # 北交所、深交所使用0开头
            else:
                stock_code_api = f'1.{clean_stock_code}'  # 默认上交所

            # 构造请求参数
            params = {
                "invt": "2",
                "fltt": "1",
                "cb": "jQuery35109261383551550911_1769745097872",
                "fields": "f58,f734,f107,f57,f43,f59,f169,f301,f60,f170,f152,f177,f111,f46,f44,f45,f47,f260,f48,f261,f279,f277,f278,f288,f19,f17,f531,f15,f13,f11,f20,f18,f16,f14,f12,f39,f37,f35,f33,f31,f40,f38,f36,f34,f32,f211,f212,f213,f214,f215,f210,f209,f208,f207,f206,f161,f49,f171,f50,f86,f84,f85,f168,f108,f116,f167,f164,f162,f163,f92,f71,f117,f292,f51,f52,f191,f192,f262,f294,f181,f295,f748,f747,f803",
                "secid": stock_code_api,
                "ut": "fa5fd1943c7b386f172d6893dbfba10b",
                "wbp2u": "|0|1|0|web",
                "dect": "1",
                "_": str(int(datetime.datetime.now().timestamp() * 1000))
            }

            yield Request(
                url=url,
                params=params,
                callback=self.parse,
                meta={
                    'stock_code': stock_code,
                    'stock_name': stock_name,
                    'dont_cache': True,
                    'download_timeout': 30  # 设置下载超时时间
                }
            )

    def parse(self, response):
        """解析市值数据"""
        # 获取股票信息
        stock_code = response.meta.get('stock_code', '未知')
        stock_name = response.meta.get('stock_name', '未知')
        try:
            # 解析JSONP数据（去掉回调函数包装）
            import re
            response_text = response.text.strip()
            # 使用正则表达式提取JSON部分
            json_match = re.search(r'\(({.*})\);?$', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                import json
                json_data = json.loads(json_str)
            else:
                # 如果没有匹配到JSONP格式，则尝试直接解析JSON
                try:
                    import json
                    json_data = json.loads(response_text)
                except:
                    json_data = None

            if json_data and json_data.get('rc') == 0:
                data = json_data.get('data', {})

                if data:
                    # 记录API返回数据量
                    self.logger.info(f'股票 {stock_code} API返回市值数据，开始处理...')

                    # 创建并填充Item
                    item = self._create_and_populate_item(data, stock_code, stock_name)

                    if item:
                        # 设置PMID
                        self._set_pmid(item, data)

                        yield item
                    else:
                        self.logger.warning(f'股票 {stock_code} 数据处理失败')
                else:
                    self.logger.warning(f'股票 {stock_code} API返回数据为空')
            else:
                self.logger.error(
                    f'股票 {stock_code} API请求失败 - 状态码: {json_data.get("rc") if json_data else "N/A"}')

        except Exception as e:
            self.logger.error(f'股票 {stock_code} ❌ 解析失败 - URL: {response.url}, 错误: {str(e)}')

    def _create_and_populate_item(self, data_dict, stock_code, stock_name):
        """创建并填充Item对象"""
        item = ListedCompaniesMarketValueItem()

        # 填充基础字段
        item['stock_code'] = stock_code  # 股票代码（保留后缀）
        item['stock_name'] = data_dict.get('f58', stock_name)  # 股票名称
        item['disclosure_date'] = datetime.date.today().isoformat()  # 披露日期，使用采集当天日期

        # 填充市值相关字段
        item['total_mkt_cap'] = str(data_dict.get('f116', ''))  # 总市值
        item['float_mkt_cap'] = str(data_dict.get('f117', ''))  # 流通市值
        item['pb_ratio'] = str(float(data_dict.get('f167', 0)) / 100 if data_dict.get('f167') and data_dict.get(
            'f167') != '-' else '')  # 市净率
        item['forward_pe'] = str(float(data_dict.get('f162', 0)) / 100 if data_dict.get('f162') and data_dict.get(
            'f162') != '-' else '')  # 动态市盈率
        item['trailing_pe'] = str(float(data_dict.get('f163', 0)) / 100 if data_dict.get('f163') and data_dict.get(
            'f163') != '-' else '')  # 静态市盈率
        item['ttm_pe'] = str(float(data_dict.get('f164', 0)) / 100 if data_dict.get('f164') and data_dict.get(
            'f164') != '-' else '')  # 滚动市盈率
        item['is_valid'] = 1  # 默认设为有效

        return item

    def _set_pmid(self, item, data_dict):
        """设置PMID字段"""
        stock_code = item.get('stock_code', '')
        stock_name = item.get('stock_name', '')
        disclosure_date = item.get('disclosure_date', '')

        if stock_code and stock_name and disclosure_date:
            # 使用股票代码、股票名称、披露日期生成唯一PMID
            combined_key = f"{stock_code}{stock_name}{disclosure_date}"
            item['pmid'] = hashlib.md5(combined_key.encode('utf-8')).hexdigest()

    def close_spider(self, spider):
        """爬虫关闭时的清理工作"""
        self.logger.info("A股市值数据爬虫已关闭")