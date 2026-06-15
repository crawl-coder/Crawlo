# Helpers 工具集参考

> Crawlo 内置工具类，覆盖时间格式化、文本清洗、文件下载和数据库去重检查。

## 概述

`crawlo.helpers` 提供多个独立工具类，可在爬虫、Pipeline 或脚本中直接引入使用。

## TimeUtils — 时间格式化

```python
from crawlo.helpers import TimeUtils

# 格式化时间戳
TimeUtils.format_timestamp(1718000000)                # '2024-06-10 14:13:20'
TimeUtils.format_timestamp(1718000000, fmt='%Y-%m-%d') # '2024-06-10'

# 解析时间字符串
TimeUtils.parse('2024-06-10 14:13:20')                # datetime(2024,6,10,14,13,20)
TimeUtils.parse('June 10, 2024', fmt='%B %d, %Y')    # datetime(2024,6,10,0,0)

# 相对时间
TimeUtils.time_ago(3600)                               # '1 hours ago'
TimeUtils.time_ago(86400 * 3)                          # '3 days ago'
```

## TextCleaner — 文本清洗

```python
from crawlo.helpers import TextCleaner

text = "  商品名称：\n\tiPhone 15 Pro  （深空黑色） \r\n  "

# 基础清洗
TextCleaner.clean(text)                     # '商品名称：iPhone 15 Pro（深空黑色）'
TextCleaner.strip_spaces(text)              # '商品名称： iPhone 15 Pro （深空黑色）'

# HTML 清洗
html = "<div>价格：<span>¥<em>6999</em></span></div>"
TextCleaner.strip_tags(html)                # '价格：¥6999'

# 空白符处理
TextCleaner.normalize_whitespace(text)      # 合并连续空白为单个空格
TextCleaner.remove_blank_lines(text)        # 删除空行

# 指定字符替换
TextCleaner.replace(text, old='\t', new=' ')  # Tab 替换为空格
```

## FileDownloader — 文件下载

```python
from crawlo.helpers import FileDownloader

# 同步下载
downloader = FileDownloader(save_dir='./downloads')
path = downloader.download('https://example.com/file.pdf')
# → './downloads/file.pdf'

# 异步下载
path = await downloader.download_async('https://example.com/image.png')
# → './downloads/image.png'

# 自定义文件名
path = downloader.download(
    'https://example.com/report.pdf',
    filename='report_2024.pdf'
)

# 带进度回调
def on_progress(total, downloaded):
    print(f"{downloaded}/{total} bytes")

downloader.download(url, progress_callback=on_progress)

# 断点续传
downloader = FileDownloader(
    save_dir='./downloads',
    resume=True,                         # 启用断点续传
    chunk_size=8192                      # 分块大小
)
```

## MySQLExistsChecker — 数据库去重检查

在 Pipeline 中快速检查数据是否已存在，避免重复写入：

```python
from crawlo.helpers import MySQLExistsChecker

# 初始化（复用现有 MySQL 连接配置）
checker = MySQLExistsChecker(
    host='127.0.0.1',
    port=3306,
    user='root',
    password='123456',
    database='crawlo_db',
    table='products',
    unique_key='url',                    # 唯一键字段
)

# 检查是否存在
if checker.exists('https://example.com/product/123'):
    print('已存在，跳过')
else:
    # 写入数据库
    ...

# 批量检查
urls = ['url1', 'url2', 'url3']
new_urls = checker.filter_existing(urls)  # 返回不存在的 URL 列表

# 关闭连接
checker.close()
```

在 Pipeline 中使用：

```python
class DedupPipeline:
    def __init__(self, settings):
        self.checker = MySQLExistsChecker(
            host=settings.get('MYSQL_HOST'),
            port=settings.get_int('MYSQL_PORT'),
            user=settings.get('MYSQL_USER'),
            password=settings.get('MYSQL_PASSWORD'),
            database=settings.get('MYSQL_DB'),
            table=settings.get('MYSQL_TABLE'),
            unique_key='url',
        )

    def process_item(self, item, spider):
        if self.checker.exists(item['url']):
            raise DropItem(f"Duplicate: {item['url']}")
        return item

    def close_spider(self, spider):
        self.checker.close()
```
