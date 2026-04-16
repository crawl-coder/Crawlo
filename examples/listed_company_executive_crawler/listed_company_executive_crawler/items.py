# -*- coding: UTF-8 -*-
"""
数据项定义
"""

from crawlo.items import Item, Field


class SeniorExecutivesItem(Item):
    pmid  = Field() # （stock_code + name）MD5 32位 业务主键、唯一索引
    stock_code  = Field() # 股票代码
    stock_name  = Field() # 股票名称
    name  = Field() # 姓名
    gender  = Field() # 性别
    age  = Field() #
    education  = Field() # 学历
    shareholding_num  = Field() # 持股数 (股)
    salary  = Field() # 薪酬 (元)
    position  = Field() # 职务
    tenure_start_date = Field() # 任职开始时间
    tenure_end_date  = Field() # 任职结束时间
    introduction  = Field() # 高管简介 text 类型


class ListedExecutiveChangesItem(Item):
    pmid = Field()
    change_date = Field() # 变动日期
    stock_code = Field() # 股票代码
    stock_name = Field() # 股票名称
    changer = Field() # 变动人
    change_shares = Field() # 变动股数
    average_trading_price = Field() # 成交均价
    change_amount = Field() # 变动金额（万）
    change_reason = Field() # 变动原因
    change_ratio = Field() # 变动比例（%）
    shares_after_change = Field() # 变动后持股数
    share_type = Field() # 持股种类
    supervisor_name = Field() # 董监高人员姓名
    position = Field() # 职务
    relationship_with_supervisor = Field() # 变动人与董监高的关系