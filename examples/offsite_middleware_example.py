#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OffsiteMiddleware 使用示例
展示如何配置和使用OffsiteMiddleware来限制爬虫只爬取指定域名
"""

# 基础配置
SETTINGS = {
    # 允许的域名列表（OffsiteMiddleware会使用这个配置）
    'ALLOWED_DOMAINS': [
        'example.com',
        'www.example.com',
        'subdomain.example.com'
    ],
    
    # 中间件配置（OffsiteMiddleware已默认启用）
    'MIDDLEWARES': [
        # === 请求预处理阶段 ===
        'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',  # 1. 忽略无效请求
        'crawlo.middleware.download_delay.DownloadDelayMiddleware',  # 2. 控制请求频率
        'crawlo.middleware.default_header.DefaultHeaderMiddleware',  # 3. 添加默认请求头
        'crawlo.middleware.proxy.ProxyMiddleware',  # 4. 设置代理
        'crawlo.middleware.offsite.OffsiteMiddleware',  # 5. 站外请求过滤
        
        # === 响应处理阶段 ===
        'crawlo.middleware.retry.RetryMiddleware',  # 6. 失败请求重试
        'crawlo.middleware.response_code.ResponseCodeMiddleware',  # 7. 处理特殊状态码
        'crawlo.middleware.response_filter.ResponseFilterMiddleware',  # 8. 响应内容过滤
    ],
    
    # 其他常用配置
    'DOWNLOAD_DELAY': 1,
    'CONCURRENCY': 8,
    'LOG_LEVEL': 'INFO',
}

def get_settings():
    """获取配置"""
    return SETTINGS

if __name__ == "__main__":
    print("OffsiteMiddleware配置示例:")
    print("=" * 40)
    print(f"允许的域名: {SETTINGS['ALLOWED_DOMAINS']}")
    print("\n中间件列表:")
    for i, middleware in enumerate(SETTINGS['MIDDLEWARES'], 1):
        print(f"  {i}. {middleware}")
    
    print("\n" + "=" * 40)
    print("OffsiteMiddleware功能说明:")
    print("✓ 自动过滤不在ALLOWED_DOMAINS中的请求")
    print("✓ 支持子域名匹配")
    print("✓ 记录被过滤的请求统计信息")
    print("✓ 可通过设置ALLOWED_DOMAINS=[]来禁用此中间件")