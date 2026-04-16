# -*- coding: UTF-8 -*-
"""
爬虫：senior_executives
功能：爬取上市公司高级管理人员信息
数据源：东方财富数据中心
"""
import warnings

from crawlo import Request, Response
from crawlo.spider import Spider

from ..items import SeniorExecutivesItem
from ..settings import HEADERS
from ..utils.stock_loader import load_a_stocks
from ..utils.pmid_loader import PmidCache
from ..utils.executive_tools import (
    generate_pmid_executive,
    get_v_params,
    parse_tenure_dates
)
from ..utils.progress_tracker import ProgressTracker

# 禁用aiomysql连接的ResourceWarning
warnings.filterwarnings('ignore', category=ResourceWarning, module='asyncmy')


class SeniorExecutivesSpider(Spider):
    """上市公司高级管理人员信息爬虫"""
    name = 'senior_executives'
    allowed_domains = ['datacenter.eastmoney.com', 'datapc.eastmoney.com']
    
    custom_settings = {
        'DOWNLOAD_DELAY': 1.0,
        'CONCURRENCY': 12,
        'MYSQL_TABLE': 'listed_senior_executives'
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_stock_index = None
        self.stocks = None
        self.failed_stocks = set()
        self.progress_tracker = None
        
        # 创建PMID缓存实例（内部使用懒加载）
        table_name = self.custom_settings.get("MYSQL_TABLE", "listed_senior_executives")
        self.pmid_cache = PmidCache(table_name)

    def start_requests(self):
        """
        生成初始请求
        优化：只提交第一个股票，后续股票在 parse 中串行处理，避免队列拥堵
        """
        # 加载股票数据
        stocks = load_a_stocks()
        self.logger.info(f"加载到 {len(stocks)} 只A股股票")
        
        # 保存股票列表
        self.stocks = stocks
        self.current_stock_index = 0
        
        # 初始化进度追踪器
        self.progress_tracker = ProgressTracker(
            total=len(stocks),
            step=100,
            logger=self.logger
        )
        
        # 只提交第一个请求
        if stocks:
            yield self._create_stock_request(stocks[0])
            self.logger.info(f"已提交第一个股票，剩余 {len(stocks) - 1} 个股票将在 parse 中串行处理")

    def _create_stock_request(self, stock):
        """
        创建股票请求
        
        Args:
            stock: 元组 (stock_code, stock_name)
            
        Returns:
            Request对象
        """
        stock_code = stock[0]
        url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
        
        # 构建请求参数
        params = {
            "reportName": "RPT_F10_ORGINFO_MANAINTRO",
            "columns": "ALL",
            "quoteColumns": "",
            "filter": f'(SECUCODE="{stock_code}")',
            "pageNumber": "1",
            "pageSize": "",
            "sortTypes": "",
            "sortColumns": "",
            "source": "HSF10",
            "client": "PC",
            "v": "04693675080409824"  # 初始值，会被 get_v_params 替换
        }
        
        # 生成 v 参数
        v_value = get_v_params(params)
        params['v'] = v_value
        
        request = Request(
            url=url,
            callback=self.parse,
            headers=HEADERS,
            params=params,
            priority=100,
            meta={'stock_code': stock_code}
        )
        # 跳过去重过滤
        request.dont_filter = True
        
        return request

    async def parse(self, response: Response):
        """
        解析响应
        
        Args:
            response: 响应对象
        """
        try:
            json_data = response.json()
            msg = json_data.get('message')
            stock_code = response.meta.get('stock_code')
            
            # 检查 API 响应
            if msg != 'ok':
                self.logger.error(f"API 返回错误消息：{msg}, 股票: {stock_code}")
                self.failed_stocks.add(stock_code)
                
                # 请求下一个股票
                next_stock_request = self._get_next_stock_request()
                if next_stock_request:
                    yield next_stock_request
                return
            
            # 解析数据
            rows = json_data.get('result', {}).get('data', [])
            self.logger.info(f'{stock_code} 获取到 {len(rows)} 条高管信息')
            
            # 处理每条高管信息
            for row in rows:
                item = await self._create_item(row, stock_code)
                if item:
                    yield item
            
            # 请求下一个股票
            next_stock_request = self._get_next_stock_request()
            if next_stock_request:
                yield next_stock_request
                
        except Exception as e:
            self.logger.exception(f"解析出错: {e}, URL: {response.url}")
            # 即使出错也继续处理下一个股票
            next_stock_request = self._get_next_stock_request()
            if next_stock_request:
                yield next_stock_request

    async def _create_item(self, row, stock_code):
        """
        创建并验证数据项
        
        Args:
            row: API返回的数据行
            stock_code: 股票代码
            
        Returns:
            SeniorExecutivesItem 或 None（如果已存在）
        """
        person_name = row.get('PERSON_NAME')
        
        # 验证必要字段
        if not person_name:
            self.logger.warning(f'{stock_code} 高管姓名缺失，跳过该记录')
            return None
        
        incumbent_time = row.get('INCUMBENT_TIME')
        
        # 解析任职时间
        date_info = parse_tenure_dates(incumbent_time)
        
        # 生成PMID
        pmid = generate_pmid_executive(stock_code, person_name)
        
        # 检查PMID缓存
        if await self.pmid_cache.exists(pmid):
            self.logger.info(f"跳过已存在的记录：{stock_code} - {person_name}")
            return None
        
        self.logger.debug(f"准备插入新记录：{stock_code} - {person_name}")
        
        # 创建 item
        item = SeniorExecutivesItem()
        item['pmid'] = pmid
        item['stock_code'] = stock_code
        item['stock_name'] = row.get('SECURITY_NAME_ABBR')
        item['name'] = person_name
        item['gender'] = row.get('SEX')
        item['age'] = row.get('AGE')
        item['education'] = row.get('HIGH_DEGREE')
        item['shareholding_num'] = row.get('HOLD_NUM')
        item['salary'] = row.get('SALARY')
        item['position'] = row.get('POSITION')
        item['tenure_start_date'] = date_info.get('tenure_start_date')
        item['tenure_end_date'] = date_info.get('tenure_end_date')
        item['introduction'] = row.get('RESUME')
        
        # 添加到缓存
        self.pmid_cache.add(pmid)
        
        return item

    def _get_next_stock_request(self):
        """
        获取下一个股票的请求
        
        Returns:
            Request对象 或 None
        """
        if not self.stocks:
            return None
            
        self.current_stock_index += 1
        
        if self.current_stock_index < len(self.stocks):
            next_stock = self.stocks[self.current_stock_index]
            stock_code = next_stock[0]
            
            # 更新进度
            self.progress_tracker.update(self.current_stock_index, stock_code)
            
            return self._create_stock_request(next_stock)
        else:
            # 完成
            self.progress_tracker.finish(failed_count=len(self.failed_stocks))
            return None
