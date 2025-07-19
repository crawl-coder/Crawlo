#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
# @Time    :    2025-05-17 10:20
# @Author  :   crawl-coder
# @Desc    :   时间工具
"""
import dateparser
from typing import Optional, Union
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# 常见时间格式列表
COMMON_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%d-%m-%Y %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%b %d, %Y",  # Jan 01, 2023
    "%B %d, %Y",  # January 01, 2023
    "%Y年%m月%d日",  # 2023年01月01日
    "%Y年%m月%d日 %H时%M分%S秒",  # 2023年01月01日 12时30分45秒
    "%a %b %d %H:%M:%S %Y",  # Wed Jan 01 12:00:00 2020
    "%a, %d %b %Y %H:%M:%S",  # Wed, 01 Jan 2020 12:00:00
    "%Y-%m-%dT%H:%M:%S.%f",  # ✅ 新增：ISO 8601 格式（带毫秒）
]


def normalize_time(time_str: str) -> Optional[datetime]:
    """
    尝试使用常见格式解析时间字符串。

    :param time_str: 时间字符串（如 "2023-01-01 12:00:00"）
    :return: 解析成功返回 datetime 对象，失败返回 None 或抛出异常（可选）
    """
    for fmt in COMMON_FORMATS:
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"无法解析时间字符串：{time_str}")


def get_current_time(fmt: str = '%Y-%m-%d %H:%M:%S'):
    """
    获取当前时间，根据是否传入格式化参数决定返回类型
    :param fmt: 格式化字符串，如 "%Y-%m-%d %H:%M:%S"
    :return: datetime 或 str
    """
    dt = datetime.now()
    if fmt is not None:
        return dt.strftime(fmt)
    return dt


def time_diff_seconds(start_time: str, end_time: str, fmt: str = '%Y-%m-%d %H:%M:%S'):
    """
        计算两个时间字符串之间的秒数差。

        :param start_time: 起始时间字符串
        :param end_time: 结束时间字符串
        :param fmt: 时间格式，默认为 '%Y-%m-%d %H:%M:%S'
        :return: 秒数差（总是正整数）
        """
    start = datetime.strptime(start_time, fmt)
    end = datetime.strptime(end_time, fmt)
    delta = end - start
    return int(delta.total_seconds())


TimeType = Union[str, datetime]


def time_diff(start: TimeType, end: TimeType, fmt: str = None, unit='seconds', auto_parse=True) -> Optional[int]:
    """
    计算两个时间之间的差值（支持字符串或 datetime）。

    :param start: 起始时间（字符串或 datetime）
    :param end: 结束时间（字符串或 datetime）
    :param fmt: 时间格式（如果传入字符串且 auto_parse=False 时需要）
    :param unit: 单位（seconds, minutes, hours, days）
    :param auto_parse: 是否自动尝试解析任意格式的字符串（推荐开启）
    :return: 差值整数（根据 unit 返回），失败返回 None
    """

    def ensure_datetime(t):
        if isinstance(t, datetime):
            return t
        elif isinstance(t, str):
            if auto_parse:
                parsed = normalize_time(t)
                if parsed:
                    return parsed
            if fmt:
                return datetime.strptime(t, fmt)
            raise ValueError("字符串时间未提供格式，或无法自动解析")
        else:
            raise TypeError(f"不支持的时间类型: {type(t)}")

    start_dt = ensure_datetime(start)
    end_dt = ensure_datetime(end)

    delta = (end_dt - start_dt)
    abs_seconds = int(abs(delta.total_seconds()))

    if unit == 'seconds':
        return abs_seconds
    elif unit == 'minutes':
        return abs_seconds // 60
    elif unit == 'hours':
        return abs_seconds // 3600
    elif unit == 'days':
        return abs_seconds // 86400
    else:
        raise ValueError(f"Unsupported unit: {unit}")


def format_datetime(dt, fmt="%Y-%m-%d %H:%M:%S"):
    """格式化时间"""
    return dt.strftime(fmt)


def parse_datetime(s, fmt="%Y-%m-%d %H:%M:%S"):
    """将字符串解析为 datetime 对象"""
    return datetime.strptime(s, fmt)


def datetime_to_timestamp(dt):
    """将 datetime 转换为时间戳"""
    return dt.timestamp()


def timestamp_to_datetime(ts):
    """将时间戳转换为 datetime"""
    return datetime.fromtimestamp(ts)


def add_days(dt, days=0):
    """日期加减（天）"""
    return dt + timedelta(days=days)


def add_months(dt, months=0):
    """日期加减（月）"""
    return dt + relativedelta(months=months)


def days_between(dt1, dt2):
    """计算两个日期之间的天数差"""
    return abs((dt2 - dt1).days)


def is_leap_year(year):
    """判断是否是闰年"""
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def parse_relative_time(time_str: str) -> str:
    """
    解析相对时间字符串（如 "3分钟前"、"昨天"）为 datetime 对象。
    """
    dt = dateparser.parse(time_str)
    return dt.isoformat()


if __name__ == '__main__':
    print(normalize_time(parse_relative_time("30分钟前")))
    print(parse_relative_time("昨天"))
    print(parse_relative_time("10小时前"))
    print(parse_relative_time("1个月前"))
    print(parse_relative_time("10天前"))
    print(parse_relative_time("2024年1月1日"))
    print(parse_relative_time('2025年5月30日'))
