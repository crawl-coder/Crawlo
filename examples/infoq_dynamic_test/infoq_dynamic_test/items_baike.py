# -*- coding: UTF-8 -*-
"""
百度百科企业工商信息数据项
"""
from crawlo.items import Item, Field


class BaikeCompany(Item):
    """百度百科企业数据项"""
    # 基本信息
    url = Field()  # 百科页面URL
    company_name = Field()  # 企业名称
    company_name_en = Field()  # 英文名称
    company_logo = Field()  # 企业logo
    
    # 工商登记信息
    legal_representative = Field()  # 法定代表人
    registered_capital = Field()  # 注册资本
    paid_capital = Field()  # 实缴资本
    establishment_date = Field()  # 成立日期
    business_status = Field()  # 经营状态
    unified_social_credit_code = Field()  # 统一社会信用代码
    registration_number = Field()  # 工商注册号
    organization_code = Field()  # 组织机构代码
    
    # 企业属性
    company_type = Field()  # 企业类型
    industry = Field()  # 所属行业
    business_scope = Field()  # 经营范围
    registration_authority = Field()  # 登记机关
    registered_address = Field()  # 注册地址
    business_term = Field()  # 营业期限
    
    # 人员信息
    actual_controller = Field()  # 实际控制人
    chairman = Field()  # 董事长/法人代表
    general_manager = Field()  # 总经理
    
    # 联系信息
    phone = Field()  # 电话
    email = Field()  # 邮箱
    website = Field()  # 官网
    
    # 其他信息
    company_profile = Field()  # 企业简介
    development_history = Field()  # 发展历程
    main_products = Field()  # 主营产品
    main_markets = Field()  # 主要市场
    
    # 元数据
    crawl_time = Field()  # 爬取时间
    status = Field()  # 状态（success/failed）
    error_message = Field()  # 错误信息
