# -*- coding: UTF-8 -*-
"""
telecom_licenses_standalone.items
======================
定义电信设备许可证数据结构。
"""

from crawlo.items import Item, Field


class TelecomLicenseItem(Item):
    """
    电信设备许可证数据项
    对应工信部API返回的articleField字段
    """
    # 基本信息字段（对应 API 返回的 articleField 字段）
    license_number = Field(description="许可证编号")
    device_name = Field(description="设备名称")
    device_model = Field(description="设备型号")
    applicant = Field(description="申请单位")
    manufacturer = Field(description="生产厂商")
    issue_date = Field(description="发证日期")
    expiry_date = Field(description="到期日期")
    certificate_type = Field(description="证书类型")
    remarks = Field(description="备注")
    certificate_status = Field(description="证书状态")
    origin = Field(description="原产地")
    
    # 原始数据字段
    article_id = Field(description="文章ID")
    article_edit_date = Field(description="文章编辑日期")
    create_time = Field(description="创建时间")