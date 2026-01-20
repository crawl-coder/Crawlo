# 附件下载功能使用指南

## 概述

Crawlo 框架提供了两种方式来下载附件：

1. **中间件方式**：通过 `DownloadAttachmentMiddleware` 自动下载页面中的附件
2. **工具类方式**：通过 `AttachmentDownloader` 类进行灵活的附件下载

## 中间件方式

### 启用中间件

在爬虫设置中启用中间件：

```python
# settings.py 或在爬虫类中定义 custom_settings
custom_settings = {
    'MIDDLEWARES': {
        'crawlo.middleware.download_attachment_middleware.DownloadAttachmentMiddleware': 543,
    },
    
    # 附件下载配置
    'ATTACHMENT_DOWNLOAD_DIR': './attachments',  # 下载目录
    'ATTACHMENT_ALLOWED_EXTENSIONS': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar'],  # 允许的扩展名
    'ATTACHMENT_MAX_FILE_SIZE': 50 * 1024 * 1024,  # 最大文件大小 50MB
    'ATTACHMENT_CREATE_DIRS': True,  # 自动创建目录
    'ATTACHMENT_RENAME_DUPLICATES': True,  # 重命名重复文件
    'ATTACHMENT_VERIFY_CONTENT_TYPE': True,  # 验证内容类型
}
```

### 使用方法

在请求中添加 `download_attachment` 标志：

```python
from scrapy import Request
from crawlo.spider import Spider

class AttachmentSpider(Spider):
    name = 'attachment_spider'
    
    def start_requests(self):
        yield Request(
            url='http://example.com/page-with-attachments',
            callback=self.parse,
            meta={
                'download_attachment': True  # 标记需要下载附件
            }
        )
    
    def parse(self, response):
        # 查找页面中的附件链接
        attachment_links = response.css('a[href$=".pdf"], a[href$=".doc"], a[href$=".zip"]').xpath('@href').getall()
        
        for link in attachment_links:
            yield Request(
                url=response.urljoin(link),
                callback=self.parse_attachment,
                meta={
                    'download_attachment': {
                        'filename': f'custom_name_{hash(link)}.pdf',  # 自定义文件名
                        'allowed_extensions': ['.pdf', '.doc', '.zip']  # 自定义允许的扩展名
                    }
                }
            )
    
    def parse_attachment(self, response):
        # 处理下载的附件信息
        attachment_info = response.meta.get('attachment_info')
        if attachment_info:
            print(f"附件下载成功: {attachment_info['filename']}")
            yield {
                'attachment_url': attachment_info['url'],
                'saved_path': attachment_info['filepath'],
                'file_size': attachment_info['size']
            }
```

## 工具类方式

### 基本使用

```python
from crawlo.tools.attachment_downloader import AttachmentDownloader

# 创建下载器实例
downloader = AttachmentDownloader(
    download_dir='./downloads',
    allowed_extensions=['.pdf', '.doc', '.zip', '.jpg'],
    max_file_size=10 * 1024 * 1024  # 10MB
)

# 下载单个文件
result = await downloader.download(
    url='http://example.com/sample.pdf',
    filename='sample_document.pdf'
)

if result['success']:
    print(f"下载成功: {result['filepath']}")
else:
    print(f"下载失败: {result['error']}")
```

### 批量下载

```python
# 批量下载多个文件
urls = [
    'http://example.com/file1.pdf',
    'http://example.com/file2.doc',
    'http://example.com/file3.zip'
]

batch_results = await downloader.download_batch(urls, concurrency=3)

successful_downloads = [r for r in batch_results if r['success']]
failed_downloads = [r for r in batch_results if not r['success']]

print(f"批量下载完成: 成功 {len(successful_downloads)}, 失败 {len(failed_downloads)}")
```



## 配置选项

### 中间件配置

- `ATTACHMENT_DOWNLOAD_DIR`: 下载目录（默认: './attachments'）
- `ATTACHMENT_ALLOWED_EXTENSIONS`: 允许的文件扩展名（默认: 常见文档格式）
- `ATTACHMENT_MAX_FILE_SIZE`: 最大文件大小（默认: 50MB）
- `ATTACHMENT_CREATE_DIRS`: 是否自动创建目录（默认: True）
- `ATTACHMENT_RENAME_DUPLICATES`: 是否重命名重复文件（默认: True）
- `ATTACHMENT_VERIFY_CONTENT_TYPE`: 是否验证内容类型（默认: True）

### 工具类配置

在创建 `AttachmentDownloader` 实例时可以配置：

- `download_dir`: 下载目录
- `allowed_extensions`: 允许的扩展名列表
- `max_file_size`: 最大文件大小
- `create_dirs`: 是否自动创建目录
- `rename_duplicates`: 是否重命名重复文件
- `verify_content_type`: 是否验证内容类型
- `timeout`: 下载超时时间（秒）

## 返回结果格式

下载操作返回字典格式的结果：

```python
{
    'success': True,           # 下载是否成功
    'filepath': '/path/file',  # 文件保存路径
    'filename': 'file.pdf',    # 文件名
    'size': 123456,           # 文件大小（字节）
    'url': 'http://...',      # 下载URL
    'content_type': '...',    # 内容类型
    'error': '...',           # 错误信息（失败时）
}
```

## 注意事项

1. 安全性：下载器会自动清理文件名，防止路径遍历攻击
2. 性能：支持异步下载，可配置并发数
3. 兼容性：支持多种文件格式和内容类型验证
4. 错误处理：完善的错误处理和日志记录