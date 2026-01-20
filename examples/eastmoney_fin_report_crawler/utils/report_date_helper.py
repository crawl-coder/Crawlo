# -*- coding: UTF-8 -*-
"""
A股财报报告期辅助工具
根据A股市场财报披露规则自动生成相应的报告期
"""

from datetime import datetime, date


def get_target_report_date(current_date=None):
    """
    根据当前日期和A股财报披露规则，返回应该查询的报告期
    
    A股财报披露时间规律：
    - 年报（12-31）：次年1月1日至4月30日
    - 一季报（03-31）：当年4月1日至5月31日
    - 半年报（06-30）：当年7月1日至8月31日
    - 三季报（09-30）：当年10月1日至11月30日
    
    Args:
        current_date: 指定日期，默认为今天
        
    Returns:
        str: 格式为 'YYYY-MM-DD 00:00:00' 的报告期字符串
    """
    if current_date is None:
        current_date = date.today()
    elif isinstance(current_date, str):
        # 如果输入的是字符串格式，转换为date对象
        current_date = datetime.strptime(current_date.split()[0], '%Y-%m-%d').date()
    elif isinstance(current_date, datetime):
        current_date = current_date.date()
    
    year = current_date.year
    month = current_date.month
    day = current_date.day
    
    # 根据月份和日期判断应该返回哪个报告期
    if (month == 1) or (month == 2) or (month == 3) or \
       (month == 4 and day <= 30):
        # 1-4月30日前，查询上一年年报（12-31）
        return f"{year - 1}-12-31 00:00:00"
    elif (month == 4 and day > 30) or (month == 5) or \
         (month == 6 and day <= 30):
        # 4月30日后至6月30日，查询当年一季报（03-31）
        return f"{year}-03-31 00:00:00"
    elif (month == 6 and day > 30) or month == 7 or \
         (month == 8 and day <= 31):
        # 7-8月31日前，查询半年报（06-30）
        return f"{year}-06-30 00:00:00"
    elif (month == 8 and day > 31) or month == 9 or \
         (month == 10 and day <= 31):
        # 9-10月31日前，查询三季报（09-30）
        return f"{year}-09-30 00:00:00"
    else:
        # 11-12月，查询年报（12-31）
        return f"{year}-12-31 00:00:00"


def get_available_report_periods():
    """
    获取所有可用的报告期列表
    
    Returns:
        list: 包含所有标准报告期的列表
    """
    current_year = date.today().year
    return [
        f"{current_year}-12-31 00:00:00",  # 当年年报
        f"{current_year}-09-30 00:00:00",  # 当年三季报
        f"{current_year}-06-30 00:00:00",  # 当年半年报
        f"{current_year}-03-31 00:00:00",  # 当年一季报
        f"{current_year - 1}-12-31 00:00:00",  # 上年年报
    ]


def is_report_season():
    """
    判断当前是否为财报发布季节（财报发布前后的一个月）
    
    Returns:
        bool: 是否为财报发布季节
    """
    month = date.today().month
    day = date.today().day
    
    # 财报发布高峰期：4月、5月、8月、10月、11月
    if month in [4, 5, 8, 10, 11]:
        return True
    # 3月底和6月底附近
    elif (month == 3 and day >= 20) or (month == 6 and day >= 20):
        return True
    # 9月底和12月底附近
    elif (month == 9 and day >= 20) or (month == 12 and day >= 20):
        return True
    else:
        return False


if __name__ == "__main__":
    # 测试函数
    print(f"今天是: {date.today()}")
    print(f"当前应该查询的报告期: {get_target_report_date()}")
    print(f"所有可用报告期: {get_available_report_periods()}")
    print(f"是否为财报发布季节: {is_report_season()}")