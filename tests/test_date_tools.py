#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
日期工具测试
"""
import unittest
from crawlo.tools import (
    TimeUtils,
    parse_time,
    format_time,
    time_diff,
    to_timestamp,
    to_datetime,
    now,
    to_timezone,
    to_utc,
    to_local
)


class TestDateTools(unittest.TestCase):
    """日期工具测试类"""

    def test_date_parsing(self):
        """测试日期解析功能"""
        # 测试标准格式
        dt = parse_time("2025-09-10 14:30:00")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2025)
        self.assertEqual(dt.month, 9)
        self.assertEqual(dt.day, 10)
        self.assertEqual(dt.hour, 14)
        self.assertEqual(dt.minute, 30)
        self.assertEqual(dt.second, 0)
        
        # 测试不同格式
        dt2 = parse_time("September 10, 2025 2:30 PM")
        self.assertIsNotNone(dt2)
        self.assertEqual(dt2.year, 2025)
        self.assertEqual(dt2.month, 9)
        self.assertEqual(dt2.day, 10)
        self.assertEqual(dt2.hour, 14)
        self.assertEqual(dt2.minute, 30)

    def test_date_formatting(self):
        """测试日期格式化功能"""
        dt = parse_time("2025-09-10 14:30:00")
        
        # 测试标准格式
        formatted = format_time(dt, "%Y-%m-%d")
        self.assertEqual(formatted, "2025-09-10")
        
        # 测试中文格式
        formatted_cn = format_time(dt, "%Y年%m月%d日")
        self.assertEqual(formatted_cn, "2025年09月10日")

    def test_time_difference(self):
        """测试时间差计算功能"""
        start_time = "2025-09-10 10:00:00"
        end_time = "2025-09-10 14:30:45"
        
        # 测试秒级差值
        diff_seconds = time_diff(start_time, end_time, "seconds")
        self.assertEqual(diff_seconds, 16245)  # 4小时30分45秒 = 16245秒
        
        # 测试分钟级差值
        diff_minutes = time_diff(start_time, end_time, "minutes")
        self.assertEqual(diff_minutes, 270)  # 270分钟
        
        # 测试小时级差值
        diff_hours = time_diff(start_time, end_time, "hours")
        self.assertEqual(diff_hours, 4)  # 4小时

    def test_timestamp_conversion(self):
        """测试时间戳转换功能"""
        # 测试转换为时间戳
        dt = parse_time("2025-09-10 14:30:00")
        timestamp = to_timestamp(dt)
        self.assertIsInstance(timestamp, float)
        
        # 测试从时间戳转换
        dt_from_ts = to_datetime(timestamp)
        self.assertEqual(dt.year, dt_from_ts.year)
        self.assertEqual(dt.month, dt_from_ts.month)
        self.assertEqual(dt.day, dt_from_ts.day)
        self.assertEqual(dt.hour, dt_from_ts.hour)
        self.assertEqual(dt.minute, dt_from_ts.minute)
        self.assertEqual(dt.second, dt_from_ts.second)

    def test_timezone_conversion(self):
        """测试时区转换功能"""
        dt = parse_time("2025-09-10 14:30:00")
        
        # 测试UTC转换
        utc_time = to_utc(dt)
        self.assertIsNotNone(utc_time)
        
        # 测试本地时区转换
        local_time = to_local(dt)
        self.assertIsNotNone(local_time)
        
        # 测试指定时区转换
        ny_time = to_timezone(dt, "America/New_York")
        self.assertIsNotNone(ny_time)

    def test_time_utils_class(self):
        """测试TimeUtils类方法"""
        # 测试日期加减
        base_date = "2025-09-10"
        plus_30_days = TimeUtils.add_days(base_date, 30)
        self.assertEqual(plus_30_days.month, 10)
        self.assertEqual(plus_30_days.day, 10)
        
        # 测试月份加减
        plus_3_months = TimeUtils.add_months(base_date, 3)
        self.assertEqual(plus_3_months.month, 12)
        
        # 测试闰年判断
        self.assertTrue(TimeUtils.is_leap_year(2024))
        self.assertFalse(TimeUtils.is_leap_year(2025))


if __name__ == '__main__':
    unittest.main()