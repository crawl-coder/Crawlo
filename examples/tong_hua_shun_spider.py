#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
同花顺爬虫示例
==============
使用用户提供的headers和cookies爬取同花顺网站
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo import Spider, Request


class TongHuaShunSpider(Spider):
    """同花顺网站爬虫"""
    name = 'tong_hua_shun_spider'
    
    # 用户提供的请求头
    custom_headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "priority": "u=0, i",
        "sec-ch-ua": "\"Chromium\";v=\"140\", \"Not=A?Brand\";v=\"24\", \"Google Chrome\";v=\"140\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    }
    
    # 用户提供的cookies
    custom_cookies = {
        "Hm_lvt_722143063e4892925903024537075d0d": "1758071793",
        "Hm_lvt_929f8b362150b1f77b477230541dbbc2": "1758071793",
        "historystock": "600699",
        "spversion": "20130314",
        "cid": "f9bc812da2c3a7ddf6d5df1fa2d497091758076438",
        "u_ukey": "A10702B8689642C6BE607730E11E6E4A",
        "u_uver": "1.0.0",
        "u_dpass": "Qk3U07X7SHGKa0AcRUg1R1DVWbPioD9Eg270bdikvlwWWXexbsXnRsQNt%2B04iXwdHi80LrSsTFH9a%2B6rtRvqGg%3D%3D",
        "u_did": "E3ED337393E1429DA56E380DD00B3CCD",
        "u_ttype": "WEB",
        "user_status": "0",
        "ttype": "WEB",
        "log": "",
        "Hm_lvt_69929b9dce4c22a060bd22d703b2a280": "1758079404,1758113068,1758157144",
        "HMACCOUNT": "08DF0D235A291EAA",
        "Hm_lvt_78c58f01938e4d85eaf619eae71b4ed1": "1758071793,1758113068,1758157144",
        "user": "MDpteF9lNXRkY3RpdHo6Ok5vbmU6NTAwOjgxNzYyOTAwNDo3LDExMTExMTExMTExLDQwOzQ0LDExLDQwOzYsMSw0MDs1LDEsNDA7MSwxMDEsNDA7MiwxLDQwOzMsMSw0MDs1LDEsNDA7OCwwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMSw0MDsxMDIsMSw0MDoxNjo6OjgwNzYyOTAwNDoxNzU4MTYxNTE0Ojo6MTc1ODA3MjA2MDo2MDQ4MDA6MDoxYTQ0NmFlNDY4M2VmZWY3YmNjYTczY2U3ODZmZTNiODg6ZGVmYXVsdF81OjA%3D",
        "userid": "807629004",
        "u_name": "mx_e5tdctitz",
        "escapename": "mx_e5tdctitz",
        "ticket": "85eea709becdd924d7eb975351de629e",
        "utk": "8959c4c6b6f5fb7628864feab15473f4",
        "sess_tk": "eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiIsImtpZCI6InNlc3NfdGtfMSIsImJ0eSI6InNlc3NfdGsifQ.eyJqdGkiOiI4ODNiZmU4NmU3M2NhN2NjN2JlZmVmODM0NmFlNDZhNDEiLCJpYXQiOjE3NTgxNjE1MTQsImV4cCI6MTc1ODc2NjMxNCwic3ViIjoiODA3NjI5MDA0IiwiaXNzIjoidXBhc3MuaXdlbmNhaS5jb20iLCJhdWQiOiIyMDIwMTExODUyODg5MDcyIiwiYWN0Ijoib2ZjIiwiY3VocyI6ImIwNTcyZDVjOWNlNDg0MGFlOWYxYTlhYjU3NGZkNjQyYjgzNmExN2E3Y2NhZjk4ZWRiNzI5ZmJkOWFjOGVkYmYifQ.UBNIzxGvQQtXSiIcB_1JJl-EuAc1S9j2LcTLXjwy4ImhDDbh1oJvyRdDUrXdUpwBpIyx5zgYqgt_3FEhY_iayw",
        "cuc": "ap2eap3gg99g",
        "Hm_lvt_f79b64788a4e377c608617fba4c736e2": "1758161692",
        "v": "A1glI4rWhPCQGqh0MvA0ioufKY3vQbzLHqWQT5JJpBNGLfazOlGMW261YNrh",
        "Hm_lpvt_78c58f01938e4d85eaf619eae71b4ed1": "1758163145",
        "Hm_lpvt_f79b64788a4e377c608617fba4c736e2": "1758163145",
        "Hm_lpvt_69929b9dce4c22a060bd22d703b2a280": "1758163145"
    }
    
    def start_requests(self):
        """生成初始请求"""
        # 用户提供的URL
        url = "https://stock.10jqka.com.cn/20240315/c655957791.shtml"
        
        # 创建请求并添加自定义headers和cookies
        request = Request(
            url=url,
            callback=self.parse,
            headers=self.custom_headers,
            cookies=self.custom_cookies
        )
        yield request
    
    def parse(self, response):
        """解析响应"""
        print(f"\n成功获取页面: {response.url}")
        print(f"状态码: {response.status_code}")
        
        # 提取页面标题
        title = response.css('title::text').get()
        if title:
            print(f"页面标题: {title}")
        
        # 提取页面中的关键信息
        # 例如提取文章标题、发布时间等
        article_title = response.css('h1.main-title::text').get()
        if article_title:
            print(f"文章标题: {article_title}")
        
        publish_time = response.css('.time::text').get()
        if publish_time:
            print(f"发布时间: {publish_time}")
        
        # 返回提取的数据
        return {
            'url': response.url,
            'status_code': response.status_code,
            'title': title,
            'article_title': article_title,
            'publish_time': publish_time
        }


# 配置说明
SETTINGS = {
    # 基础配置
    'LOG_LEVEL': 'INFO',
    'CONCURRENCY': 1,
    
    # 代理配置
    'PROXY_ENABLED': True,
    'PROXY_API_URL': 'http://test.proxy.api:8080/proxy/getitem/',
    'PROXY_EXTRACTOR': 'proxy',
    'PROXY_REFRESH_INTERVAL': 60,
    'PROXY_API_TIMEOUT': 10,
    'PROXY_POOL_SIZE': 3,
    'PROXY_HEALTH_CHECK_THRESHOLD': 0.5,
    
    # 下载延迟
    'DOWNLOAD_DELAY': 2,
    'RANDOMNESS': True,
    
    # 中间件
    'MIDDLEWARES': [
        'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',
        'crawlo.middleware.download_delay.DownloadDelayMiddleware',
        'crawlo.middleware.default_header.DefaultHeaderMiddleware',
        'crawlo.middleware.proxy.ProxyMiddleware',
        'crawlo.middleware.retry.RetryMiddleware',
        'crawlo.middleware.response_code.ResponseCodeMiddleware',
        'crawlo.middleware.response_filter.ResponseFilterMiddleware',
    ],
    
    # 管道
    'PIPELINES': [
        'crawlo.pipelines.console_pipeline.ConsolePipeline',
    ],
}


def main():
    """主函数"""
    print("同花顺爬虫示例")
    print("=" * 30)
    print("此示例展示如何在Crawlo框架中:")
    print("1. 使用自定义headers和cookies")
    print("2. 集成代理功能")
    print("3. 爬取同花顺网站内容")
    print("=" * 30)
    
    print("\n使用方法:")
    print("1. 在项目settings.py中配置代理参数")
    print("2. 运行爬虫: crawlo run tong_hua_shun_spider")


if __name__ == '__main__':
    main()