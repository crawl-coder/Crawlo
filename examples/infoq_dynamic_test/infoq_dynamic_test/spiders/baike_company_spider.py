# -*- coding: UTF-8 -*-
"""
百度百科企业工商信息爬虫
========================

功能：
1. 使用 CloakBrowser 下载器绕过百度百科反爬
2. 集成代理API实现IP轮换
3. 支持批量采集成百上千家企业
4. 提取企业工商登记信息

测试URL：https://baike.baidu.com/item/小米科技有限责任公司
"""
import os
import re
import json
from datetime import datetime
from urllib.parse import quote
from crawlo import Spider, Request
from ..items_baike import BaikeCompany


class BaikeCompanySpider(Spider):
    """百度百科企业工商信息爬虫"""
    
    name = 'baike_company'
    
    # 起始URL模板（批量采集时使用）
    BASE_URL = 'https://baike.baidu.com/item/{}'
    
    # 代理API配置（按需填写）
    # PROXY_API_URL = ''
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 支持从文件读取企业列表
        self.company_file = kwargs.get('company_file')
        self.max_companies = int(kwargs.get('max_companies', 100))
        
        # 统计信息
        self.success_count = 0
        self.failed_count = 0
        
    def start_requests(self):
        """生成起始请求"""
        self.logger.info("=" * 70)
        self.logger.info("百度百科企业工商信息爬虫启动")
        self.logger.info("=" * 70)
        self.logger.info(f"代理API: {self.PROXY_API_URL}")
        self.logger.info(f"最大采集数量: {self.max_companies}")
        
        # 方式1: 从文件读取企业列表
        if self.company_file and os.path.exists(self.company_file):
            yield from self._load_companies_from_file()
            return
        
        # 方式2: 测试模式 - 单个企业
        yield from self._test_single_company()
    
    def _generate_test_companies(self, count=100):
        """生成测试企业列表"""
        # 真实知名企业列表（确保百科存在）
        companies = [
            # 科技巨头
            '小米科技有限责任公司',
            '华为技术有限公司',
            '阿里巴巴集团控股有限公司',
            '腾讯科技有限公司',
            '百度在线网络技术（北京）有限公司',
            '京东集团股份有限公司',
            '美团科技有限公司',
            '滴滴出行科技有限公司',
            '字节跳动科技有限公司',
            '网易（杭州）网络有限公司',
            # 手机厂商
            'OPPO广东移动通信有限公司',
            '维沃移动通信有限公司',
            '荣耀终端有限公司',
            ' Realme 中国移动通信有限公司',
            '一加科技有限公司',
            # 家电企业
            '珠海格力电器股份有限公司',
            '美的集团股份有限公司',
            '海尔智家股份有限公司',
            'TCL科技集团股份有限公司',
            '海信集团有限公司',
            # 互联网企业
            '北京奇虎科技有限公司',
            '蚂蚁科技集团股份有限公司',
            '上海寻梦信息技术有限公司',
            '拼多多科技有限公司',
            '快手科技有限公司',
            '北京微梦创科网络技术有限公司',
            # 金融企业
            '中国平安保险（集团）股份有限公司',
            '中国工商银行股份有限公司',
            '中国建设银行股份有限公司',
            '招商银行股份有限公司',
            '交通银行股份有限公司',
            # 房地产
            '万科企业股份有限公司',
            '碧桂园控股有限公司',
            '恒大集团有限公司',
            '融创中国控股有限公司',
            '保利发展控股集团股份有限公司',
            # 汽车企业
            '比亚迪股份有限公司',
            '蔚来汽车有限公司',
            '小鹏汽车科技有限公司',
            '理想汽车有限公司',
            '吉利汽车集团有限公司',
            '长城汽车股份有限公司',
            '上海汽车集团股份有限公司',
            # 餐饮食品
            '贵州茅台酒股份有限公司',
            '五粮液股份有限公司',
            '青岛啤酒股份有限公司',
            '伊利实业集团股份有限公司',
            '蒙牛乳业有限公司',
            '康师傅控股有限公司',
            '统一企业中国控股有限公司',
            # 零售
            '永辉超市股份有限公司',
            '苏宁易购集团股份有限公司',
            '国美零售控股有限公司',
            '华润万家有限公司',
            '大润发投资有限公司',
            # 医药
            '国药控股股份有限公司',
            '上海复星医药（集团）股份有限公司',
            '云南白药集团股份有限公司',
            '北京同仁堂股份有限公司',
            '华润三九医药股份有限公司',
            # 能源
            '中国石油天然气股份有限公司',
            '中国石油化工股份有限公司',
            '中国海洋石油有限公司',
            '国家电网有限公司',
            '中国南方电网有限责任公司',
            # 通信
            '中国移动通信集团有限公司',
            '中国电信集团有限公司',
            '中国联合网络通信集团有限公司',
            '中国铁塔股份有限公司',
            # 航空
            '中国航空集团有限公司',
            '中国东方航空股份有限公司',
            '中国南方航空股份有限公司',
            '海南航空控股股份有限公司',
            # 快递物流
            '顺丰控股股份有限公司',
            '中通快递股份有限公司',
            '圆通速递股份有限公司',
            '申通快递有限公司',
            '韵达控股股份有限公司',
            '百世物流科技（中国）有限公司',
        ]
        
        # 如果数量不够，重复补充
        while len(companies) < count:
            companies.extend(companies[:count-len(companies)])
        
        return companies[:count]
    
    def _load_companies_from_file(self):
        """从文件加载企业列表"""
        self.logger.info(f"从文件加载企业列表: {self.company_file}")
        
        with open(self.company_file, 'r', encoding='utf-8') as f:
            companies = [line.strip() for line in f if line.strip()]
        
        self.logger.info(f"加载了 {len(companies)} 家企业")
        
        # 限制数量
        companies = companies[:self.max_companies]
        
        for idx, company_name in enumerate(companies, 1):
            # URL编码
            encoded_name = quote(company_name)
            url = self.BASE_URL.format(encoded_name)
            
            yield Request(
                url=url,
                callback=self.parse_company,
                meta={
                    'company_name': company_name,
                    'use_dynamic_loader': True,
                    'cloakbrowser_headless': True,
                    'cloakbrowser_timeout': 30000,
                    'cloakbrowser_block_resources': ['image', 'font', 'media', 'stylesheet'],
                    'dont_redirect': True,
                    'handle_httpstatus_list': [302, 403, 404, 500],
                },
                dont_filter=True
            )
            
            if idx % 100 == 0:
                self.logger.info(f"已提交 {idx}/{len(companies)} 家企业请求")
    
    def _test_single_company(self):
        """测试模式：生成100家企业"""
        # 生成100家测试企业
        test_companies = self._generate_test_companies(100)
        
        self.logger.info(f"测试模式: 生成 {len(test_companies)} 家企业")
        
        for idx, company_name in enumerate(test_companies, 1):
            encoded_name = quote(company_name)
            url = self.BASE_URL.format(encoded_name)
            
            yield Request(
                url=url,
                callback=self.parse_company,
                meta={
                    'company_name': company_name,
                    'use_dynamic_loader': True,
                    'cloakbrowser_headless': True,  # 批量测试使用无头模式
                    'cloakbrowser_timeout': 30000,
                    'cloakbrowser_block_resources': ['image', 'font', 'media', 'stylesheet'],
                },
                dont_filter=True
            )
            
            if idx % 20 == 0:
                self.logger.info(f"已提交 {idx}/{len(test_companies)} 家企业请求")
    
    def parse_company(self, response):
        """解析企业百科页面（简化版：只验证企业名称）"""
        company_name = response.meta.get('company_name', '')
        
        self.logger.info(f"[{self.success_count + self.failed_count + 1}] 采集: {company_name}")
        
        # 错误处理
        if response.status != 200:
            self.logger.warning(f"  ❌ 失败: HTTP {response.status}")
            self.failed_count += 1
            item = BaikeCompany(
                company_name=company_name,
                url=response.url,
                status='failed',
                error_message=f'HTTP {response.status}'
            )
            yield item
            return
        
        # 检查是否被重定向到搜索页
        if 'search' in response.url or '列表' in response.text[:1000]:
            self.logger.warning(f"  ❌ 词条不存在")
            self.failed_count += 1
            item = BaikeCompany(
                company_name=company_name,
                url=response.url,
                status='failed',
                error_message='词条不存在'
            )
            yield item
            return
        
        try:
            # 简化：只提取页面标题验证是否成功
            page_title = response.xpath('//title/text()').get()
            if page_title:
                page_title = page_title.strip()
                self.logger.info(f"  ✅ 成功: {page_title}")
                self.success_count += 1
                item = BaikeCompany(
                    company_name=company_name,
                    url=response.url,
                    page_title=page_title,
                    status='success'
                )
                yield item
            else:
                self.logger.warning(f"  ⚠️ 未找到标题")
                self.failed_count += 1
                item = BaikeCompany(
                    company_name=company_name,
                    url=response.url,
                    status='failed',
                    error_message='未找到标题'
                )
                yield item
        
        except Exception as e:
            self.logger.error(f"  ❌ 解析错误: {e}")
            self.failed_count += 1
            item = BaikeCompany(
                company_name=company_name,
                url=response.url,
                status='failed',
                error_message=str(e)
            )
            yield item
        
        # 输出统计
        total = self.success_count + self.failed_count
        self.logger.info(f"📊 统计: 成功={self.success_count}, 失败={self.failed_count}, 总计={total}\n")
    
    def _extract_company_info(self, response, company_name):
        """提取企业工商信息"""
        company = BaikeCompany(
            url=response.url,
            company_name=company_name,
            crawl_time=datetime.now().isoformat(),
            status='success'
        )
        
        # 方法1: 提取基本信息表格（dl-definitionList）
        self._extract_basic_info_table(response, company)
        
        # 方法2: 提取企业简介
        self._extract_company_profile(response, company)
        
        return company
    
    def _extract_basic_info_table(self, response, company):
        """提取基本信息表格"""
        # 百度百科的基本信息使用 dl-definitionList 结构
        # dt 是标签名，dd 是值
        
        basic_items = response.xpath('//dl[contains(@class, "basicInfo-item")]')
        
        if not basic_items:
            self.logger.warning("未找到基本信息表格")
            return
        
        self.logger.info(f"找到 {len(basic_items)} 个基本信息项")
        
        for item in basic_items:
            # 提取标签名
            label = item.xpath('.//dt[contains(@class, "basicInfo-item-name")]//text()').get()
            if not label:
                continue
            
            label = label.strip().rstrip('：').rstrip(':')
            
            # 提取值
            value_nodes = item.xpath('.//dd[contains(@class, "basicInfo-item-value")]//text()')
            value = ''.join([t.strip() for t in value_nodes.getall()]).strip()
            
            if not value:
                continue
            
            # 映射到字段
            self._map_field(company, label, value)
    
    def _map_field(self, company, label, value):
        """将标签映射到字段"""
        field_mapping = {
            '法定代表人': 'legal_representative',
            '董事长': 'chairman',
            '总经理': 'general_manager',
            '实际控制人': 'actual_controller',
            '注册资本': 'registered_capital',
            '实缴资本': 'paid_capital',
            '成立日期': 'establishment_date',
            '经营状态': 'business_status',
            '统一社会信用代码': 'unified_social_credit_code',
            '工商注册号': 'registration_number',
            '组织机构代码': 'organization_code',
            '企业类型': 'company_type',
            '所属行业': 'industry',
            '登记机关': 'registration_authority',
            '注册地址': 'registered_address',
            '营业期限': 'business_term',
            '电话': 'phone',
            '邮箱': 'email',
            '官网': 'website',
            '英文名称': 'company_name_en',
        }
        
        # 模糊匹配
        for key, field_name in field_mapping.items():
            if key in label:
                company[field_name] = value
                self.logger.debug(f"  {label} -> {field_name}: {value}")
                return
        
        # 经营范围特殊处理（可能跨多行）
        if '经营范围' in label:
            company['business_scope'] = value
            self.logger.debug(f"  经营范围: {value[:50]}...")
    
    def _extract_company_profile(self, response, company):
        """提取企业简介"""
        # 查找"企业简介"标题
        profile_selector = '//h2[contains(text(), "企业简介") or contains(text(), "公司简介")]'
        profile_title = response.xpath(profile_selector)
        
        if profile_title:
            # 提取标题后的段落
            profile = profile_title.xpath(
                'following-sibling::p[1]//text()'
            ).getall()
            
            if profile:
                company['company_profile'] = ' '.join([t.strip() for t in profile if t.strip()])
