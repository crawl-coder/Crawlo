# -*- coding: UTF-8 -*-
"""
数据项定义
"""

from crawlo.items import Item, Field


# ==================== A股市值数据 ITEM ====================
class ListedCompaniesMarketValueItem(Item):
    """上市公司市值数据表"""
    pmid = Field()  # 主键id，MD5(stock_code+stock_name+disclosure_date)
    stock_code = Field()  # 股票代码
    stock_name = Field()  # 股票名称
    disclosure_date = Field()  # 披露日期，采集当天的日期
    total_mkt_cap = Field()  # 总市值
    pb_ratio = Field()  # 市净率
    float_mkt_cap = Field()  # 流通市值
    forward_pe = Field()  # 动态市盈率
    trailing_pe = Field()  # 静态市盈率
    ttm_pe = Field()  # 滚动市盈率
    is_valid = Field()  # 是否有效，0-否，1-是
