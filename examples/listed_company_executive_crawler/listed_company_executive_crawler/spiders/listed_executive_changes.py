# -*- coding: UTF-8 -*-
"""
爬虫：listed_executive_changes
功能：爬取上市公司高管变动数据
数据源：东方财富数据中心
"""
import warnings

from crawlo import Request, Response
from crawlo.spider import Spider

from ..items import ListedExecutiveChangesItem
from ..settings import HEADERS
from ..utils.tools import round_if_numeric
from ..utils.stock_loader import load_a_stocks
from ..utils.pmid_loader import PmidCache
from ..utils.executive_tools import (
    generate_pmid_changes,
    parse_stock_code,
    build_api_params,
    build_base_params
)
from ..utils.progress_tracker import ProgressTracker

# 禁用aiomysql连接的ResourceWarning
warnings.filterwarnings('ignore', category=ResourceWarning, module='aiomysql')


class ListedExecutiveChangesSpider(Spider):
    """上市公司高管变动数据爬虫"""
    name = 'lec'
    allowed_domains = ['datacenter.eastmoney.com', 'datapc.eastmoney.com']
    
    custom_settings = {
        'DOWNLOAD_DELAY': 1.0,
        'CONCURRENCY': 12,
        'MYSQL_TABLE': 'listed_executive_changes'
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_stock_index = None
        self.stocks = None
        self.failed_stocks = set()
        self.progress_tracker = None
        
        # 创建PMID缓存实例（内部使用懒加载，不会立即查询数据库）
        table_name = self.custom_settings.get("MYSQL_TABLE", "listed_executive_changes")
        self.pmid_cache = PmidCache(table_name)

    def start_requests(self):
        """
        生成初始请求
        优化：只提交第一个股票，后续股票在 parse 中串行处理，避免队列拥堵
        """
        # 使用load_a_stocks加载股票数据
        stocks = load_a_stocks()
        self.logger.info(f"加载到 {len(stocks)} 只A股股票")
        
        # 保存股票列表到实例变量，供 parse 中使用
        self.stocks = stocks
        self.current_stock_index = 0
        
        # 初始化进度追踪器
        self.progress_tracker = ProgressTracker(
            total=len(stocks),
            step=100,
            logger=self.logger
        )
        
        # 只提交第一个请求，后续在 parse 中串行处理
        if stocks:
            yield self._create_stock_request(stocks[0])
            self.logger.info(f"已提交第一个股票，剩余 {len(stocks) - 1} 个股票将在 parse 中串行处理")

    def _create_stock_request(self, stock):
        """
        创建股票请求的辅助方法
        
        Args:
            stock: 元组 (stock_code, stock_name)
            
        Returns:
            Request对象
        """
        stock_with_suffix = stock[0]
        code_for_api = parse_stock_code(stock_with_suffix)
        
        # 构建请求参数
        params = build_api_params(code_for_api, page=1, page_size=20)
        base_params = build_base_params(code_for_api, page_size=20)
        
        request = Request(
            url="https://datapc.eastmoney.com/emdatacenter/ggcg/detaillist",
            callback=self.parse,
            headers=HEADERS,
            params=params,
            priority=100,
            meta={
                'stock_with_suffix': stock_with_suffix,
                'code_for_api': code_for_api,
                'current_page': 1,
                'base_params': base_params
            }
        )
        # 跳过去重过滤
        request.dont_filter = True
        
        return request

    async def parse(self, response: Response):
        """
        解析响应并实现翻页
        
        Args:
            response: 响应对象
        """
        try:
            json_data = response.json()
            msg = json_data.get('message')
            stock_with_suffix = response.meta.get('stock_with_suffix')
            current_page = response.meta.get('current_page', 1)
            base_params = response.meta.get('base_params', {})
            
            if msg != 'ok':
                # 返回数据为空不算错误，只是info
                if msg == '返回数据为空':
                    self.logger.info(f"该股票无高管变动数据: {stock_with_suffix}")
                else:
                    self.logger.error(f"API 返回错误消息：{msg}, 股票: {stock_with_suffix}, 页码: {current_page}")
                    self.failed_stocks.add(stock_with_suffix)
                
                # 无论是否有数据，都要请求下一个股票
                next_stock_request = self._get_next_stock_request()
                if next_stock_request:
                    yield next_stock_request
                return
            
            result = json_data.get('result', {})
            rows = result.get('data', [])
            total_pages = result.get('pages', 0)
            
            # 调试：打印翻页信息
            self.logger.info(f'{stock_with_suffix} Page {current_page}/{total_pages}, rows={len(rows)}')
            
            # 解析当前页数据
            for row in rows:
                item = await self._create_item(row, stock_with_suffix)
                if item:
                    yield item
            
            # 翻页逻辑：如果还有下一页，继续请求
            # 安全条件：1. 当前页<总页数  2. 当前页有数据
            if current_page < total_pages and len(rows) > 0:
                # 还有下一页，继续翻页
                next_page = current_page + 1
                self.logger.info(f'{stock_with_suffix} next_page: {next_page}/{total_pages}')
                
                next_params = base_params.copy()
                next_params['p'] = str(next_page)
                
                yield Request(
                    url=response.url.split('?')[0],  # 去掉原始参数，避免重复
                    callback=self.parse,
                    headers=HEADERS,
                    params=next_params,
                    priority=100,
                    meta={
                        'stock_with_suffix': stock_with_suffix,
                        'current_page': next_page,
                        'base_params': base_params
                    }
                )
            else:
                # 当前股票处理完毕（已到达最后一页 或 当前页无数据）
                if len(rows) == 0:
                    self.logger.info(f'{stock_with_suffix} 第{current_page}页无数据，停止翻页')
                else:
                    self.logger.info(f'{stock_with_suffix} 已处理完最后一页 ({current_page}/{total_pages})')
                
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

    async def _create_item(self, row, stock_with_suffix):
        """
        创建并验证数据项
        
        Args:
            row: API返回的数据行
            stock_with_suffix: 带后缀的股票代码
            
        Returns:
            ListedExecutiveChangesItem 或 None（如果已存在）
        """
        # 提取字段
        person_name = row.get('PERSON_NAME')
        change_date = row.get('CHANGE_DATE')
        dse_person_name = row.get('DSE_PERSON_NAME')
        change_shares = row.get('CHANGE_SHARES')
        shares_after_change = row.get('CHANGE_AFTER_HOLDNUM')
        
        # 生成PMID（业务主键）
        pmid = generate_pmid_changes(person_name, change_date, dse_person_name, change_shares, shares_after_change)
        
        # 检查PMID缓存
        if await self.pmid_cache.exists(pmid):
            self.logger.info(
                f"跳过已存在的记录：{stock_with_suffix} - {person_name} | 日期：{change_date}"
            )
            return None
        
        self.logger.debug(
            f"准备插入新记录：{stock_with_suffix} - {person_name} | 日期：{change_date}"
        )
        
        # 创建 item
        item = ListedExecutiveChangesItem()
        item['pmid'] = pmid
        item['stock_code'] = stock_with_suffix
        item['stock_name'] = row.get('SECURITY_NAME')
        item['change_date'] = change_date
        item['changer'] = person_name
        item['change_reason'] = row.get('CHANGE_REASON')
        item['change_shares'] = change_shares
        item['average_trading_price'] = round_if_numeric(row.get('AVERAGE_PRICE'))
        item['change_amount'] = round_if_numeric(row.get('CHANGE_AMOUNT'))
        item['change_ratio'] = row.get('CHANGE_RATIO')
        item['shares_after_change'] = shares_after_change
        item['share_type'] = row.get('HOLD_TYPE')
        item['supervisor_name'] = dse_person_name
        item['position'] = row.get('POSITION_NAME')
        item['relationship_with_supervisor'] = row.get('PERSON_DSE_RELATION')
        
        # 添加到缓存，避免同批次重复
        self.pmid_cache.add(pmid)
        
        return item

    def _get_next_stock_request(self):
        """
        获取下一个股票的请求，如果没有更多股票则返回None
        
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