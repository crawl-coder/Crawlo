#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo框架日期工具使用示例
"""
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


def demo_date_parsing():
    """演示日期解析功能"""
    print("=== 日期解析演示 ===\n")
    
    # 解析各种格式的日期字符串
    date_strings = [
        "2025-09-10 14:30:00",
        "September 10, 2025 2:30 PM",
        "2025/09/10 14:30:00",
        "10-09-2025 14:30:00",
        "2025年9月10日 14时30分00秒"
    ]
    
    for date_str in date_strings:
        parsed = parse_time(date_str)
        print(f"解析 '{date_str}' -> {parsed}")
    
    print()


def demo_date_formatting():
    """演示日期格式化功能"""
    print("=== 日期格式化演示 ===\n")
    
    # 获取当前时间
    current_time = now()
    print(f"当前时间: {current_time}")
    
    # 使用不同格式进行格式化
    formats = [
        "%Y-%m-%d",
        "%Y年%m月%d日",
        "%Y-%m-%d %H:%M:%S",
        "%B %d, %Y at %I:%M %p",
        "%A, %B %d, %Y"
    ]
    
    for fmt in formats:
        formatted = format_time(current_time, fmt)
        print(f"格式化为 '{fmt}' -> {formatted}")
    
    print()


def demo_time_calculations():
    """演示时间计算功能"""
    print("=== 时间计算演示 ===\n")
    
    # 计算时间差
    start_time = "2025-09-10 10:00:00"
    end_time = "2025-09-10 14:30:45"
    
    diff_seconds = time_diff(start_time, end_time, "seconds")
    diff_minutes = time_diff(start_time, end_time, "minutes")
    diff_hours = time_diff(start_time, end_time, "hours")
    
    print(f"起始时间: {start_time}")
    print(f"结束时间: {end_time}")
    print(f"时间差 - 秒: {diff_seconds}")
    print(f"时间差 - 分钟: {diff_minutes}")
    print(f"时间差 - 小时: {diff_hours}")
    
    print()
    
    # 日期加减
    base_date = "2025-09-10"
    plus_30_days = TimeUtils.add_days(base_date, 30)
    minus_15_days = TimeUtils.add_days(base_date, -15)
    plus_3_months = TimeUtils.add_months(base_date, 3)
    
    print(f"基础日期: {base_date}")
    print(f"加30天: {plus_30_days}")
    print(f"减15天: {minus_15_days}")
    print(f"加3个月: {plus_3_months}")
    
    print()


def demo_timezone_conversion():
    """演示时区转换功能"""
    print("=== 时区转换演示 ===\n")
    
    # 创建一个时间
    dt = parse_time("2025-09-10 14:30:00")
    print(f"原始时间: {dt}")
    
    # 转换为UTC时区
    utc_time = to_utc(dt)
    print(f"UTC时间: {utc_time}")
    
    # 转换为本地时区
    local_time = to_local(dt)
    print(f"本地时间: {local_time}")
    
    # 转换为纽约时区
    ny_time = to_timezone(dt, "America/New_York")
    print(f"纽约时间: {ny_time}")
    
    # 转换为伦敦时区
    london_time = to_timezone(dt, "Europe/London")
    print(f"伦敦时间: {london_time}")
    
    print()


def demo_timestamp_conversion():
    """演示时间戳转换功能"""
    print("=== 时间戳转换演示 ===\n")
    
    # 获取当前时间戳
    current_timestamp = to_timestamp(now())
    print(f"当前时间戳: {current_timestamp}")
    
    # 从时间戳转换为datetime
    dt_from_timestamp = to_datetime(current_timestamp)
    print(f"从时间戳转换: {dt_from_timestamp}")
    
    # 从时间戳创建带时区的datetime
    dt_with_tz = to_timezone(to_datetime(current_timestamp), "Asia/Shanghai")
    print(f"带时区的时间: {dt_with_tz}")
    
    print()


def demo_in_spider():
    """演示在爬虫中使用日期工具"""
    print("=== 在爬虫中使用日期工具 ===\n")
    print("在爬虫项目中，您可以这样使用日期工具:")
    print("""
from crawlo import Spider
from crawlo.tools import parse_time, format_time

class NewsSpider(Spider):
    def parse(self, response):
        # 提取文章发布时间
        publish_time_str = response.css('.publish-time::text').get()
        
        # 解析发布时间
        publish_time = parse_time(publish_time_str)
        
        # 格式化时间为标准格式
        formatted_time = format_time(publish_time, "%Y-%m-%d %H:%M:%S")
        
        # 计算文章发布多久了
        current_time = self.tools.now()
        hours_since_publish = self.tools.time_diff(publish_time, current_time, "hours")
        
        # 根据发布时间决定是否继续处理
        if hours_since_publish < 24:  # 只处理24小时内的文章
            # 处理文章...
            pass
    """)


if __name__ == '__main__':
    # 运行演示
    demo_date_parsing()
    demo_date_formatting()
    demo_time_calculations()
    demo_timezone_conversion()
    demo_timestamp_conversion()
    demo_in_spider()