#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DefaultHeaderMiddleware 使用示例
展示如何配置和使用DefaultHeaderMiddleware来添加默认请求头，支持随机更换功能
"""

# 基础配置
SETTINGS = {
    # 默认请求头配置
    'DEFAULT_REQUEST_HEADERS': {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    },
    
    # 固定User-Agent（优先级高于随机User-Agent）
    # 'USER_AGENT': 'Custom User Agent String',
    
    # 自定义User-Agent列表（可选，如果不配置将使用内置列表）
    # 'USER_AGENTS': [
    #     'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    #     'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    # ],
    
    # 启用随机User-Agent功能
    'RANDOM_USER_AGENT_ENABLED': True,
    
    # 指定User-Agent设备类型（可选值: "desktop", "mobile", "all"）
    'USER_AGENT_DEVICE_TYPE': 'all',
    
    # 随机请求头配置（启用RANDOMNESS时使用）
    'RANDOM_HEADERS': {
        'Accept': [
            'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
        ],
        'Accept-Language': [
            'zh-CN,zh;q=0.9,en;q=0.8',
            'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7'
        ],
        'Cache-Control': 'no-cache'  # 固定值
    },
    
    # 启用随机性功能（用于随机请求头）
    'RANDOMNESS': True,
    
    # 中间件配置（DefaultHeaderMiddleware已默认启用）
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
    print("DefaultHeaderMiddleware配置示例:")
    print("=" * 40)
    print("默认请求头配置:")
    for key, value in SETTINGS['DEFAULT_REQUEST_HEADERS'].items():
        print(f"  {key}: {value}")
    
    print(f"\n随机User-Agent功能: {'启用' if SETTINGS['RANDOM_USER_AGENT_ENABLED'] else '禁用'}")
    print(f"User-Agent设备类型: {SETTINGS['USER_AGENT_DEVICE_TYPE']}")
    
    print(f"\n随机请求头功能: {'启用' if SETTINGS['RANDOMNESS'] else '禁用'}")
    print("随机请求头配置:")
    for key, value in SETTINGS['RANDOM_HEADERS'].items():
        if isinstance(value, list):
            print(f"  {key}: {len(value)}个可选值")
        else:
            print(f"  {key}: {value}")
    
    print("\n中间件列表:")
    for i, middleware in enumerate(SETTINGS['MIDDLEWARES'], 1):
        print(f"  {i}. {middleware}")
    
    print("\n" + "=" * 40)
    print("DefaultHeaderMiddleware功能说明:")
    print("✓ 自动为所有请求添加默认请求头")
    print("✓ 不会覆盖请求中已存在的同名头部")
    print("✓ 支持随机User-Agent更换（降低被识别风险）")
    print("✓ 支持按设备类型选择User-Agent（桌面/移动/全部）")
    print("✓ 支持随机请求头更换（增加请求多样性）")
    print("✓ 可通过设置相关配置项来启用/禁用随机功能")
    print("✓ 在调试模式下会记录添加的请求头信息")