#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ResponseCodeMiddleware 使用示例
展示如何使用ResponseCodeMiddleware处理HTTP响应状态码
"""

# ResponseCodeMiddleware是默认启用的中间件，无需特殊配置
# 它会自动记录所有响应的状态码统计信息

# 中间件配置（ResponseCodeMiddleware已默认启用）
SETTINGS = {
    # 中间件配置（ResponseCodeMiddleware已默认启用）
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
    print("ResponseCodeMiddleware配置示例:")
    print("=" * 40)
    print("中间件列表:")
    for i, middleware in enumerate(SETTINGS['MIDDLEWARES'], 1):
        print(f"  {i}. {middleware}")
    
    print("\n" + "=" * 40)
    print("ResponseCodeMiddleware功能说明:")
    print("✓ 自动记录所有HTTP响应状态码")
    print("✓ 按状态码分类统计(2xx, 3xx, 4xx, 5xx)")
    print("✓ 记录成功/错误响应数量")
    print("✓ 按域名统计响应状态码分布")
    print("✓ 提供详细的日志信息")
    print("✓ 无需特殊配置，默认启用")