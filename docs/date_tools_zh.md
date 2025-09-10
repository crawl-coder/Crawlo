# 日期处理工具

Crawlo 框架提供了一套完整的日期处理工具，专门针对爬虫场景中常见的多语言、多格式时间解析需求进行了优化。

## 功能特性

1. **智能时间解析**：支持多种语言和格式的时间字符串解析
2. **相对时间处理**：能够解析 "1 hour ago"、"昨天" 等相对时间表达式
3. **格式化输出**：提供灵活的时间格式化功能
4. **时间计算**：支持时间差计算、时间加减等操作
5. **时间戳转换**：方便的时间戳与时间对象相互转换

## 使用方法

### 导入工具

```python
from crawlo import (
    TimeUtils,      # 时间处理工具类
    parse_time,     # 解析时间字符串
    format_time,    # 格式化时间
    time_diff,      # 计算时间差
    to_timestamp,   # 转换为时间戳
    to_datetime,    # 从时间戳转换为时间对象
    now,            # 获取当前时间
    to_timezone,    # 转换为指定时区
    to_utc,         # 转换为UTC时区
    to_local        # 转换为本地时区
)
```

### 解析时间

```python
# 解析标准格式时间
dt = parse_time("2023-10-01 15:30:00")

# 解析英文时间
dt = parse_time("October 1, 2023 3:30 PM")

# 解析相对时间
dt = parse_time("1 hour ago")

# 解析中文相对时间
dt = parse_time("昨天 15:30")

# 解析失败时返回默认值
dt = parse_time("invalid time", default=datetime(2023, 1, 1))
```

### 格式化时间

```python
dt = parse_time("2023-10-01 15:30:00")

# 默认格式化
formatted = format_time(dt)  # "2023-10-01 15:30:00"

# 自定义格式
formatted = format_time(dt, "%Y年%m月%d日")  # "2023年10月01日"
```

### 时间差计算

```python
start = "2023-10-01 15:30:00"
end = "2023-10-02 16:45:30"

# 计算相差的秒数
diff_seconds = time_diff(start, end, "seconds")  # 90930

# 计算相差的天数
diff_days = time_diff(start, end, "days")  # 1
```

### 时间戳转换

```python
dt = parse_time("2023-10-01 15:30:00")

# 转换为时间戳
timestamp = to_timestamp(dt)  # 1696145400.0

# 从时间戳转换为时间对象
converted_dt = to_datetime(timestamp)
```

### 获取当前时间

```python
# 获取当前时间的 datetime 对象
current_dt = now()

# 获取格式化的当前时间字符串
current_str = now(fmt="%Y-%m-%d %H:%M:%S")
```

## 在爬虫中的应用

```python
from crawlo import Spider, Request, Item, Field
from crawlo import parse_time, format_time, now

class NewsItem(Item):
    title = Field()
    publish_time = Field()  # 原始时间字符串
    parsed_time = Field()   # 解析后的时间
    crawl_time = Field()    # 爬取时间

class NewsSpider(Spider):
    def parse(self, response):
        # 从网页中提取时间字符串
        publish_time_str = response.css('.publish-time::text').get()
        
        # 解析时间
        publish_time = parse_time(publish_time_str)
        
        # 创建数据项
        item = NewsItem()
        item['title'] = response.css('.title::text').get()
        item['publish_time'] = publish_time_str
        item['parsed_time'] = format_time(publish_time) if publish_time else None
        item['crawl_time'] = now(fmt="%Y-%m-%d %H:%M:%S")
        
        yield item
```

### 时区处理

```python
from datetime import datetime
from crawlo import to_utc, to_local, to_timezone

# 创建一个时间对象
dt = datetime(2023, 10, 1, 15, 30, 0)

# 转换为UTC时区
utc_dt = to_utc(dt)

# 转换为本地时区
local_dt = to_local(dt)

# 转换为指定时区
ny_dt = to_timezone(dt, "America/New_York")
```

## TimeUtils 类方法

除了函数式接口，Crawlo 还提供了 `TimeUtils` 类，包含以下静态方法：

- `TimeUtils.parse()`: 解析时间
- `TimeUtils.format()`: 格式化时间
- `TimeUtils.diff()`: 计算时间差
- `TimeUtils.to_timestamp()`: 转换为时间戳
- `TimeUtils.from_timestamp()`: 从时间戳转换
- `TimeUtils.add_days()`: 日期加减（天）
- `TimeUtils.add_months()`: 日期加减（月）
- `TimeUtils.days_between()`: 计算天数差
- `TimeUtils.is_leap_year()`: 判断闰年
- `TimeUtils.now()`: 获取当前时间
- `TimeUtils.iso_format()`: 返回 ISO 8601 格式
- `TimeUtils.to_timezone()`: 转换为指定时区
- `TimeUtils.to_utc()`: 转换为UTC时区
- `TimeUtils.to_local()`: 转换为本地时区
- `TimeUtils.from_timestamp_with_tz()`: 从时间戳创建带时区的datetime对象

这些工具使得在爬虫项目中处理各种复杂的时间格式变得简单而可靠。