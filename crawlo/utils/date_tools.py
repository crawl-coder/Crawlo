#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2025-05-17 10:20
# @Author  : crawl-coder
# @Desc    : 智能时间工具库（专为爬虫场景设计）
"""
import dateparser
from typing import Optional, Union, Literal
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# 支持的单位类型
TimeUnit = Literal["seconds", "minutes", "hours", "days"]
# 时间输入类型
TimeType = Union[str, datetime]

# 常见时间格式列表（作为 dateparser 的后备方案）
COMMON_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%d-%m-%Y %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%Y年%m月%d日",
    "%Y年%m月%d日 %H时%M分%S秒",
    "%a %b %d %H:%M:%S %Y",
    "%a, %d %b %Y %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
]


class TimeUtils:
    """
    时间处理工具类，提供日期解析、格式化、计算等一站式服务。
    特别适用于爬虫中处理多语言、多格式、相对时间的场景。
    """

    @staticmethod
    def _try_strptime(time_str: str) -> Optional[datetime]:
        """尝试使用预定义格式解析，作为 dateparser 的后备"""
        for fmt in COMMON_FORMATS:
            try:
                return datetime.strptime(time_str.strip(), fmt)
            except ValueError:
                continue
        return None

    @classmethod
    def parse(cls, time_input: TimeType, *, default: Optional[datetime] = None) -> Optional[datetime]:
        """
        智能解析时间输入（字符串或 datetime）。

        :param time_input: 时间字符串（支持各种语言、格式、相对时间）或 datetime 对象
        :param default: 解析失败时返回的默认值
        :return: 解析成功返回 datetime，失败返回 default
        """
        if isinstance(time_input, datetime):
            return time_input

        if not isinstance(time_input, str) or not time_input.strip():
            return default

        # 1. 优先使用 dateparser（支持多语言和相对时间）
        try:
            parsed = dateparser.parse(time_input.strip())
            if parsed:
                return parsed
        except Exception:
            pass  # 忽略异常，尝试后备方案

        # 2. 尝试使用常见格式解析
        try:
            parsed = cls._try_strptime(time_input)
            if parsed:
                return parsed
        except Exception:
            pass

        return default

    @classmethod
    def format(cls, dt: TimeType, fmt: str = "%Y-%m-%d %H:%M:%S") -> Optional[str]:
        """
        格式化时间。

        :param dt: datetime 对象或可解析的字符串
        :param fmt: 输出格式
        :return: 格式化后的字符串，失败返回 None
        """
        if isinstance(dt, str):
            dt = cls.parse(dt)
            if dt is None:
                return None
        try:
            return dt.strftime(fmt)
        except Exception:
            return None

    @classmethod
    def to_timestamp(cls, dt: TimeType) -> Optional[float]:
        """转换为时间戳（秒级）"""
        if isinstance(dt, str):
            dt = cls.parse(dt)
            if dt is None:
                return None
        try:
            return dt.timestamp()
        except Exception:
            return None

    @classmethod
    def from_timestamp(cls, ts: float) -> Optional[datetime]:
        """从时间戳创建 datetime"""
        try:
            return datetime.fromtimestamp(ts)
        except Exception:
            return None

    @classmethod
    def diff(cls, start: TimeType, end: TimeType, unit: TimeUnit = "seconds") -> Optional[int]:
        """
        计算两个时间的差值（自动解析字符串）。

        :param start: 起始时间
        :param end: 结束时间
        :param unit: 单位 ('seconds', 'minutes', 'hours', 'days')
        :return: 差值（绝对值），失败返回 None
        """
        start_dt = cls.parse(start)
        end_dt = cls.parse(end)
        if not start_dt or not end_dt:
            return None

        delta = abs((end_dt - start_dt).total_seconds())

        unit_map = {
            "seconds": 1,
            "minutes": 60,
            "hours": 3600,
            "days": 86400,
        }
        return int(delta // unit_map.get(unit, 1))

    @classmethod
    def add_days(cls, dt: TimeType, days: int) -> Optional[datetime]:
        """日期加减（天）"""
        dt = cls.parse(dt)
        if dt is None:
            return None
        return dt + timedelta(days=days)

    @classmethod
    def add_months(cls, dt: TimeType, months: int) -> Optional[datetime]:
        """日期加减（月）"""
        dt = cls.parse(dt)
        if dt is None:
            return None
        return dt + relativedelta(months=months)

    @classmethod
    def days_between(cls, dt1: TimeType, dt2: TimeType) -> Optional[int]:
        """计算两个日期之间的天数差"""
        return cls.diff(dt1, dt2, "days")

    @classmethod
    def is_leap_year(cls, year: int) -> bool:
        """判断是否是闰年"""
        return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)

    @classmethod
    def now(cls, fmt: Optional[str] = None) -> Union[datetime, str]:
        """
        获取当前时间。

        :param fmt: 如果提供，则返回格式化字符串；否则返回 datetime 对象。
        :return: datetime 或 str
        """
        dt = datetime.now()
        if fmt is not None:
            return dt.strftime(fmt)
        return dt

    @classmethod
    def iso_format(cls, dt: TimeType) -> Optional[str]:
        """返回 ISO 8601 格式字符串"""
        dt = cls.parse(dt)
        if dt is None:
            return None
        return dt.isoformat()


# =======================对外接口=======================

def parse_time(time_input: TimeType, default: Optional[datetime] = None) -> Optional[datetime]:
    """解析时间字符串或对象"""
    return TimeUtils.parse(time_input, default=default)


def format_time(dt: TimeType, fmt: str = "%Y-%m-%d %H:%M:%S") -> Optional[str]:
    """格式化时间"""
    return TimeUtils.format(dt, fmt)


def time_diff(start: TimeType, end: TimeType, unit: TimeUnit = "seconds") -> Optional[int]:
    """计算时间差"""
    return TimeUtils.diff(start, end, unit)


def to_timestamp(dt: TimeType) -> Optional[float]:
    """转时间戳"""
    return TimeUtils.to_timestamp(dt)


def to_datetime(ts: float) -> Optional[datetime]:
    """从时间戳转 datetime"""
    return TimeUtils.from_timestamp(ts)


def now(fmt: Optional[str] = None) -> Union[datetime, str]:
    """获取当前时间"""
    return TimeUtils.now(fmt)


if __name__ == '__main__':
    get_current_time = now(fmt="%Y-%m-%d %H:%M:%S")
    print(get_current_time)
