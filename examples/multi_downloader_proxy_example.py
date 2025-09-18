#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Crawlo框架多下载器代理配置示例
展示如何在Crawlo中配置不同下载器并使用代理功能
"""

# aiohttp下载器配置
DOWNLOADER_CONFIGS = {
    "aiohttp": {
        'DOWNLOADER': 'crawlo.downloader.aiohttp_downloader.AioHttpDownloader',
        'DOWNLOADER_TYPE': 'aiohttp',
        # aiohttp特定配置
        'AIOHTTP_AUTO_DECOMPRESS': True,
        'AIOHTTP_FORCE_CLOSE': False,
    },
    
    "httpx": {
        'DOWNLOADER': 'crawlo.downloader.httpx_downloader.HttpXDownloader',
        'DOWNLOADER_TYPE': 'httpx',
        # httpx特定配置
        'HTTPX_HTTP2': True,
        'HTTPX_FOLLOW_REDIRECTS': True,
    },
    
    "curl_cffi": {
        'DOWNLOADER': 'crawlo.downloader.cffi_downloader.CurlCffiDownloader',
        'DOWNLOADER_TYPE': 'curl_cffi',
        # curl-cffi特定配置
        'CURL_BROWSER_TYPE': 'chrome',
    }
}

# 通用配置（适用于所有下载器）
COMMON_SETTINGS = {
    # 代理配置
    'PROXY_ENABLED': True,
    'PROXY_API_URL': 'http://test.proxy.api:8080/proxy/getitem/',
    'PROXY_EXTRACTOR': 'proxy',
    'PROXY_REFRESH_INTERVAL': 60,
    'PROXY_POOL_SIZE': 5,
    
    # 下载器通用配置
    'DOWNLOAD_TIMEOUT': 30,
    'CONNECTION_POOL_LIMIT': 100,
    'CONNECTION_POOL_LIMIT_PER_HOST': 20,
    'DOWNLOAD_MAXSIZE': 10 * 1024 * 1024,  # 10MB
    'VERIFY_SSL': True,
    
    # 日志配置
    'LOG_LEVEL': 'INFO',
}

def get_downloader_settings(downloader_type):
    """
    获取指定下载器的完整配置
    """
    if downloader_type not in DOWNLOADER_CONFIGS:
        raise ValueError(f"不支持的下载器类型: {downloader_type}")
    
    # 合并通用配置和特定下载器配置
    settings = COMMON_SETTINGS.copy()
    settings.update(DOWNLOADER_CONFIGS[downloader_type])
    return settings

# 使用示例
if __name__ == "__main__":
    print("Crawlo框架多下载器代理配置示例")
    print("=" * 50)
    
    for downloader_type in DOWNLOADER_CONFIGS.keys():
        print(f"\n{downloader_type.upper()} 下载器配置:")
        settings = get_downloader_settings(downloader_type)
        for key, value in settings.items():
            print(f"  {key}: {value}")
    
    print("\n" + "=" * 50)
    print("所有下载器均已适配代理中间件:")
    print("✓ aiohttp: 通过 meta 传递代理认证信息")
    print("✓ httpx: 直接使用代理URL")
    print("✓ curl-cffi: 支持 str 和 dict 格式代理")
