#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ResponseFilterMiddleware 使用示例
展示如何使用ResponseFilterMiddleware过滤HTTP响应
"""

# ResponseFilterMiddleware默认允许2xx状态码
# 可通过配置ALLOWED_RESPONSE_CODES和DENIED_RESPONSE_CODES来自定义过滤规则

# 中间件配置示例
SETTINGS = {
    # 允许的响应状态码列表（除了默认的2xx）
    'ALLOWED_RESPONSE_CODES': [
        301,  # 永久重定向
        302,  # 临时重定向
        404,  # 页面未找到（可能需要特殊处理）
    ],
    
    # 拒绝的响应状态码列表（优先级高于ALLOWED_RESPONSE_CODES）
    'DENIED_RESPONSE_CODES': [
        200,  # 明确拒绝正常响应（仅作示例）
        403,  # 禁止访问
    ],
    
    # 中间件配置（ResponseFilterMiddleware已默认启用）
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
    print("ResponseFilterMiddleware配置示例:")
    print("=" * 40)
    print(f"允许的状态码: {SETTINGS['ALLOWED_RESPONSE_CODES']}")
    print(f"拒绝的状态码: {SETTINGS['DENIED_RESPONSE_CODES']}")
    print("\n中间件列表:")
    for i, middleware in enumerate(SETTINGS['MIDDLEWARES'], 1):
        print(f"  {i}. {middleware}")
    
    print("\n" + "=" * 40)
    print("ResponseFilterMiddleware功能说明:")
    print("✓ 默认允许2xx状态码")
    print("✓ 支持自定义允许的状态码列表")
    print("✓ 支持自定义拒绝的状态码列表")
    print("✓ 拒绝列表优先级高于允许列表")
    print("✓ 自动过滤不符合要求的响应")
    print("✓ 提供详细的日志信息")