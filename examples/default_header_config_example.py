#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
DefaultHeaderMiddleware 配置示例
展示如何配置DefaultHeaderMiddleware以启用随机User-Agent功能
"""

# ============================== 简化配置示例 ==============================

# 1. 基础配置（使用默认请求头和User-Agent）
# 框架已提供合理的默认配置，无需额外设置即可使用

# 2. 启用随机User-Agent功能
# 只需设置这一个参数即可启用随机User-Agent功能
RANDOM_USER_AGENT_ENABLED = True

# ============================== 推荐配置 ==============================

# 推荐配置：基础反反爬虫配置
# 启用随机User-Agent功能以提高爬虫的隐蔽性
RANDOM_USER_AGENT_ENABLED = True

# ============================== 配置说明 ==============================

"""
DefaultHeaderMiddleware 简化配置说明：

1. DEFAULT_REQUEST_HEADERS:
   - 框架已提供合理的默认请求头
   - 包含Accept、Accept-Language、Accept-Encoding等常用头部
   - 一般情况下无需修改

2. USER_AGENT:
   - 框架已提供现代浏览器的默认User-Agent
   - 一般情况下无需修改

3. RANDOM_USER_AGENT_ENABLED:
   - 是否启用随机User-Agent功能
   - 默认为False，需要手动启用
   - 设置为True后会为每个请求随机选择一个User-Agent

使用建议：
- 对于大多数爬虫项目，只需设置 RANDOM_USER_AGENT_ENABLED = True 即可
- 如有特殊需求，可以自定义 DEFAULT_REQUEST_HEADERS 和 USER_AGENT
- 随机User-Agent功能可以有效提高爬虫的隐蔽性和成功率
"""