#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
附件下载功能示例
================

展示如何使用附件下载中间件和工具函数。
"""

import asyncio
from scrapy import Request
from crawlo.spider import Spider
from crawlo.items import Item, Field
from crawlo.tools.attachment_downloader import AttachmentDownloader, download_attachment
from crawlo.middleware.download_attachment_middleware import DownloadAttachmentMiddleware


# 示例1：使用中间件下载附件
class AttachmentSpider(Spider):
    """
    使用中间件下载附件的示例爬虫
    """
    name = 'attachment_spider'
    
    def start_requests(self):
        # 发起请求并标记需要下载附件
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
            # 为每个附件发起下载请求
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


# 示例2：使用工具函数下载附件
async def download_attachments_with_tool():
    """
    使用工具函数下载附件的示例
    """
    print("=== 使用工具函数下载附件 ===")
    
    # 创建下载器实例
    downloader = AttachmentDownloader(
        download_dir='./downloads',
        allowed_extensions=['.pdf', '.doc', '.zip', '.jpg'],
        max_file_size=10 * 1024 * 1024  # 10MB
    )
    
    # 单个下载示例
    result = await downloader.download(
        url='http://example.com/sample.pdf',
        filename='sample_document.pdf'
    )
    
    if result['success']:
        print(f"单个文件下载成功: {result['filename']}")
    else:
        print(f"单个文件下载失败: {result['error']}")
    
    # 批量下载示例
    urls = [
        'http://example.com/file1.pdf',
        'http://example.com/file2.doc',
        'http://example.com/file3.zip'
    ]
    
    batch_results = await downloader.download_batch(urls, concurrency=3)
    
    successful_downloads = [r for r in batch_results if r['success']]
    failed_downloads = [r for r in batch_results if not r['success']]
    
    print(f"批量下载完成: 成功 {len(successful_downloads)}, 失败 {len(failed_downloads)}")


# 示例3：使用便捷函数
async def download_with_convenience_functions():
    """
    使用便捷函数下载附件的示例
    """
    print("\n=== 使用便捷函数下载附件 ===")
    
    # 使用便捷函数下载单个文件
    result = await download_attachment(
        url='http://example.com/sample.pdf',
        download_dir='./quick_downloads',
        filename='quick_sample.pdf'
    )
    
    if result['success']:
        print(f"便捷函数下载成功: {result['filepath']}")
    else:
        print(f"便捷函数下载失败: {result['error']}")


# 示例4：自定义设置
def get_custom_settings():
    """
    返回自定义设置，用于启用附件下载中间件
    """
    return {
        'ATTACHMENT_DOWNLOAD_DIR': './spider_attachments',
        'ATTACHMENT_ALLOWED_EXTENSIONS': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar', '.ppt', '.pptx'],
        'ATTACHMENT_MAX_FILE_SIZE': 50 * 1024 * 1024,  # 50MB
        'ATTACHMENT_CREATE_DIRS': True,
        'ATTACHMENT_RENAME_DUPLICATES': True,
        'ATTACHMENT_VERIFY_CONTENT_TYPE': True,
        
        # 启用中间件
        'MIDDLEWARES': {
            'crawlo.middleware.download_attachment_middleware.DownloadAttachmentMiddleware': 543,
        }
    }


# 配置示例
class CustomAttachmentSpider(Spider):
    """
    自定义配置的附件下载爬虫
    """
    name = 'custom_attachment_spider'
    
    custom_settings = get_custom_settings()
    
    def start_requests(self):
        yield Request(
            url='http://example.com/documents',
            callback=self.parse_documents
        )
    
    def parse_documents(self, response):
        # 查找所有文档链接
        doc_links = response.css('a[href$=".pdf"], a[href$=".doc"], a[href$=".zip"]').getall()
        
        for href in doc_links:
            yield Request(
                url=response.urljoin(href),
                callback=self.parse_doc_page,
                meta={'download_attachment': True}
            )
    
    def parse_doc_page(self, response):
        # 提取文档信息
        title = response.css('title::text').get()
        
        # 检查附件下载结果
        attachment_info = response.meta.get('attachment_info')
        if attachment_info:
            yield {
                'title': title,
                'document_url': attachment_info['url'],
                'saved_path': attachment_info['filepath'],
                'file_size': attachment_info['size'],
                'success': attachment_info['success']
            }


if __name__ == '__main__':
    print("Crawlo 附件下载功能示例")
    print("=" * 50)
    
    # 运行工具函数示例
    asyncio.run(download_attachments_with_tool())
    
    # 运行便捷函数示例
    asyncio.run(download_with_convenience_functions())
    
    print("\n使用方法:")
    print("1. 在爬虫中使用 DownloadAttachmentMiddleware 中间件自动下载附件")
    print("2. 在代码中使用 AttachmentDownloader 类进行灵活下载")
    print("3. 使用便捷函数 download_attachment() 进行快速下载")
    print("4. 通过设置配置自定义下载行为")