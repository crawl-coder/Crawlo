#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
User-Agent 数据库
================
包含各种设备、浏览器和应用的 User-Agent 字符串，用于爬虫伪装。

功能特性:
- 按设备类型分类（桌面/移动/平板）
- 按浏览器分类（Chrome/Firefox/Safari/Edge等）
- 支持国内特殊浏览器（QQ/360/UC等）
- 支持应用内 WebView（微信/支付宝/微博等）
- 提供便捷的查询和随机选择功能
"""

import random
from typing import List, Optional


# ============================================================================
# 桌面浏览器 User-Agent
# ============================================================================

DESKTOP_USER_AGENTS = [
    # Chrome (最新版本 - 2025年2月)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    
    # Chrome (稳定版本)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    
    # Firefox (最新版本)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:135.0) Gecko/20100101 Firefox/135.0",
    "Mozilla/5.0 (X11; Linux i686; rv:135.0) Gecko/20100101 Firefox/135.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0",
    
    # Firefox (稳定版本)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0",
    
    # Safari (最新版本 - macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_7_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    
    # Edge (最新版本)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",
    
    # Opera
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 OPR/117.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 OPR/117.0.0.0",
    
    # 国内浏览器 - QQ浏览器
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 QQBrowser/14.8.6723.400",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 QQBrowser/14.8.6723.400",
    
    # 国内浏览器 - 360浏览器
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 QIHU 360SE/15.3.2128.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 QIHU 360EE/15.3.2128.0",
]

# ============================================================================
# 移动设备 User-Agent
# ============================================================================

MOBILE_USER_AGENTS = [
    # iPhone (最新版本 - iOS 18)
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_7_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.7 Mobile/15E148 Safari/604.1",
    
    # iPad (最新版本 - iPadOS 18)
    "Mozilla/5.0 (iPad; CPU OS 18_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_7_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.7 Mobile/15E148 Safari/604.1",
    
    # Android Chrome (最新版本)
    "Mozilla/5.0 (Linux; Android 15; SM-S938B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.6943.98 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 15; Pixel 9 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.6943.98 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.6943.98 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.6943.98 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.6943.98 Mobile Safari/537.36",
    
    # Android 国内品牌
    "Mozilla/5.0 (Linux; Android 14; V2324A Build/UP1A.231005.007) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.6943.98 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; 23116PN5BC Build/UP1A.231005.007) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.6943.98 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; PGT-AN10 Build/HONORPGT-AN10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.6943.98 Mobile Safari/537.36",
]

# ============================================================================
# 平板设备 User-Agent
# ============================================================================

TABLET_USER_AGENTS = [
    # iPad
    "Mozilla/5.0 (iPad; CPU OS 18_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_7_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.7 Mobile/15E148 Safari/604.1",
    
    # Android Tablet
    "Mozilla/5.0 (Linux; Android 14; SM-X916C Build/UP1A.231005.007) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.6943.98 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel Tablet Build/AP2A.240905.004) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.6943.98 Safari/537.36",
]

# ============================================================================
# 应用内 WebView User-Agent
# ============================================================================

WEBVIEW_USER_AGENTS = [
    # 微信内置浏览器
    "Mozilla/5.0 (Linux; Android 14; SM-S938B Build/UP1A.231005.007) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/133.0.6943.98 Mobile Safari/537.36 MicroMessenger/8.0.47",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.47",
    
    # 支付宝内置浏览器
    "Mozilla/5.0 (Linux; Android 14; SM-S938B Build/UP1A.231005.007) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/133.0.6943.98 Mobile Safari/537.36 Ariver/1.2.0 AlipayDefined(nt:WIFI,ws:412|892|2.0) AliApp(AP/10.5.88)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 AlipayDefined(nt:WIFI,ws:390|844|2.0) AliApp(AP/10.5.88)",
    
    # 微博内置浏览器
    "Mozilla/5.0 (Linux; Android 14; SM-S938B Build/UP1A.231005.007) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/133.0.6943.98 Mobile Safari/537.36 Weibo (Android)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Weibo (iPhone)",
    
    # QQ内置浏览器
    "Mozilla/5.0 (Linux; Android 14; SM-S938B Build/UP1A.231005.007) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/133.0.6943.98 Mobile Safari/537.36 MQQBrowser/8.9",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Mobile/15E148 Safari/604.1 MQQBrowser/8.9",
    
    # 抖音内置浏览器
    "Mozilla/5.0 (Linux; Android 14; SM-S938B Build/UP1A.231005.007) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/133.0.6943.98 Mobile Safari/537.36 aweme/290000",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 aweme/290000",
]

# ============================================================================
# 爬虫/机器人 User-Agent (用于测试)
# ============================================================================

BOT_USER_AGENTS = [
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)",
    "Mozilla/5.0 (compatible; Baiduspider/2.0; +http://www.baidu.com/search/spider.html)",
    "Mozilla/5.0 (compatible; Yahoo! Slurp; http://help.yahoo.com/help/us/ysearch/slurp)",
    "Mozilla/5.0 (compatible; DuckDuckBot/1.1; +http://duckduckgo.com/duckduckbot.html)",
    "Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)",
    "Mozilla/5.0 (compatible; facebookexternalhit/1.1; +http://www.facebook.com/externalhit_uatext.php)",
    "Mozilla/5.0 (compatible; Twitterbot/1.0)",
    "Mozilla/5.0 (compatible; LinkedInBot/1.0; +http://www.linkedin.com)",
    "Mozilla/5.0 (compatible; AhrefsBot/7.0; +http://ahrefs.com/robot/)",
]


# ============================================================================
# 按浏览器分类的 User-Agent (动态生成)
# ============================================================================

CHROME_USER_AGENTS = [
    ua for ua in DESKTOP_USER_AGENTS + MOBILE_USER_AGENTS 
    if "Chrome" in ua and "Edg" not in ua and "OPR" not in ua and "QQBrowser" not in ua and "360" not in ua
]

FIREFOX_USER_AGENTS = [
    ua for ua in DESKTOP_USER_AGENTS + MOBILE_USER_AGENTS 
    if "Firefox" in ua
]

SAFARI_USER_AGENTS = [
    ua for ua in DESKTOP_USER_AGENTS + MOBILE_USER_AGENTS 
    if "Safari" in ua and "Chrome" not in ua and "MicroMessenger" not in ua
]

EDGE_USER_AGENTS = [
    ua for ua in DESKTOP_USER_AGENTS + MOBILE_USER_AGENTS 
    if "Edg" in ua
]

OPERA_USER_AGENTS = [
    ua for ua in DESKTOP_USER_AGENTS + MOBILE_USER_AGENTS 
    if "OPR" in ua
]

# 国内浏览器
CHINA_BROWSER_USER_AGENTS = [
    ua for ua in DESKTOP_USER_AGENTS + MOBILE_USER_AGENTS
    if any(browser in ua for browser in ["QQBrowser", "360", "MicroMessenger", "MQQBrowser"])
]


# ============================================================================
# 组合列表
# ============================================================================

ALL_USER_AGENTS = DESKTOP_USER_AGENTS + MOBILE_USER_AGENTS

# 按类型分类的字典
USER_AGENTS_BY_TYPE = {
    "desktop": DESKTOP_USER_AGENTS,
    "mobile": MOBILE_USER_AGENTS,
    "tablet": TABLET_USER_AGENTS,
    "bot": BOT_USER_AGENTS,
    "webview": WEBVIEW_USER_AGENTS,
    "all": ALL_USER_AGENTS,
    "chrome": CHROME_USER_AGENTS,
    "firefox": FIREFOX_USER_AGENTS,
    "safari": SAFARI_USER_AGENTS,
    "edge": EDGE_USER_AGENTS,
    "opera": OPERA_USER_AGENTS,
    "china": CHINA_BROWSER_USER_AGENTS,
}


# ============================================================================
# 工具函数
# ============================================================================

def get_user_agents(device_type: str = "all") -> List[str]:
    """
    获取指定类型的 User-Agent 列表
    
    Args:
        device_type: 设备类型，可选值:
            - "desktop": 桌面浏览器
            - "mobile": 移动设备
            - "tablet": 平板设备
            - "bot": 爬虫/机器人
            - "webview": 应用内 WebView（微信/支付宝等）
            - "all": 所有类型（桌面+移动）
            - "chrome": Chrome 浏览器
            - "firefox": Firefox 浏览器
            - "safari": Safari 浏览器
            - "edge": Edge 浏览器
            - "opera": Opera 浏览器
            - "china": 国内浏览器（QQ/360/微信等）
    
    Returns:
        User-Agent 字符串列表
    
    Example:
        >>> get_user_agents("desktop")
        ['Mozilla/5.0 (Windows NT 10.0...', ...]
        
        >>> get_user_agents("webview")
        ['Mozilla/5.0 ... MicroMessenger/8.0.47', ...]
    """
    return USER_AGENTS_BY_TYPE.get(device_type, ALL_USER_AGENTS)


def get_random_user_agent(device_type: str = "all") -> str:
    """
    获取随机 User-Agent
    
    Args:
        device_type: 设备类型（同上）
    
    Returns:
        随机 User-Agent 字符串
    
    Example:
        >>> get_random_user_agent("mobile")
        'Mozilla/5.0 (iPhone; CPU iPhone OS 18_3_1...'
    """
    user_agents = get_user_agents(device_type)
    return random.choice(user_agents) if user_agents else ""


def parse_user_agent(ua_string: str) -> dict:
    """
    解析 User-Agent 字符串，提取关键信息
    
    Args:
        ua_string: User-Agent 字符串
    
    Returns:
        包含解析结果的字典
    
    Example:
        >>> parse_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64)...")
        {
            'browser': 'Chrome',
            'version': '133.0.0.0',
            'os': 'Windows',
            'os_version': '10.0',
            'device_type': 'desktop'
        }
    """
    result = {
        'browser': 'Unknown',
        'version': 'Unknown',
        'os': 'Unknown',
        'os_version': 'Unknown',
        'device_type': 'unknown'
    }
    
    # 检测浏览器
    if "Chrome" in ua_string and "Edg" not in ua_string and "OPR" not in ua_string:
        result['browser'] = 'Chrome'
        if "Chrome/" in ua_string:
            result['version'] = ua_string.split("Chrome/")[1].split(" ")[0]
    elif "Firefox" in ua_string:
        result['browser'] = 'Firefox'
        if "Firefox/" in ua_string:
            result['version'] = ua_string.split("Firefox/")[1]
    elif "Edg" in ua_string:
        result['browser'] = 'Edge'
        if "Edg/" in ua_string:
            result['version'] = ua_string.split("Edg/")[1]
    elif "Safari" in ua_string and "Chrome" not in ua_string:
        result['browser'] = 'Safari'
        if "Version/" in ua_string:
            result['version'] = ua_string.split("Version/")[1].split(" ")[0]
    elif "MicroMessenger" in ua_string:
        result['browser'] = 'WeChat'
        if "MicroMessenger/" in ua_string:
            result['version'] = ua_string.split("MicroMessenger/")[1].split(" ")[0]
    
    # 检测操作系统
    if "Windows NT" in ua_string:
        result['os'] = 'Windows'
        if "Windows NT 10.0" in ua_string:
            result['os_version'] = '10'
        elif "Windows NT 6.1" in ua_string:
            result['os_version'] = '7'
    elif "Macintosh" in ua_string or "Mac OS X" in ua_string:
        result['os'] = 'macOS'
        if "Mac OS X " in ua_string:
            result['os_version'] = ua_string.split("Mac OS X ")[1].split(")")[0].replace("_", ".")
    elif "Linux" in ua_string:
        result['os'] = 'Linux'
    elif "iPhone" in ua_string:
        result['os'] = 'iOS'
        if "iPhone OS " in ua_string:
            result['os_version'] = ua_string.split("iPhone OS ")[1].split(" ")[0].replace("_", ".")
    elif "iPad" in ua_string:
        result['os'] = 'iPadOS'
        if "OS " in ua_string:
            result['os_version'] = ua_string.split("OS ")[1].split(" ")[0].replace("_", ".")
    elif "Android" in ua_string:
        result['os'] = 'Android'
        if "Android " in ua_string:
            result['os_version'] = ua_string.split("Android ")[1].split(";")[0]
    
    # 检测设备类型
    if any(keyword in ua_string for keyword in ["iPhone", "Android"]) and "Mobile" in ua_string:
        result['device_type'] = 'mobile'
    elif any(keyword in ua_string for keyword in ["iPad"]) or ("Android" in ua_string and "Mobile" not in ua_string):
        result['device_type'] = 'tablet'
    elif "Windows NT" in ua_string or "Macintosh" in ua_string or "Linux" in ua_string:
        result['device_type'] = 'desktop'
    
    return result


def is_mobile_user_agent(ua_string: str) -> bool:
    """判断是否是移动设备 User-Agent"""
    return "Mobile" in ua_string or "iPhone" in ua_string or "iPad" in ua_string


def is_wechat_user_agent(ua_string: str) -> bool:
    """判断是否是微信内置浏览器"""
    return "MicroMessenger" in ua_string


def is_bot_user_agent(ua_string: str) -> bool:
    """判断是否是爬虫/机器人 User-Agent"""
    return any(bot in ua_string for bot in ["bot", "Bot", "spider", "Spider", "crawl", "Crawl"])


# ============================================================================
# 导出接口
# ============================================================================

__all__ = [
    # User-Agent 列表
    "DESKTOP_USER_AGENTS",
    "MOBILE_USER_AGENTS",
    "TABLET_USER_AGENTS",
    "WEBVIEW_USER_AGENTS",
    "BOT_USER_AGENTS",
    "CHROME_USER_AGENTS",
    "FIREFOX_USER_AGENTS",
    "SAFARI_USER_AGENTS",
    "EDGE_USER_AGENTS",
    "OPERA_USER_AGENTS",
    "CHINA_BROWSER_USER_AGENTS",
    "ALL_USER_AGENTS",
    "USER_AGENTS_BY_TYPE",
    # 工具函数
    "get_user_agents",
    "get_random_user_agent",
    "parse_user_agent",
    "is_mobile_user_agent",
    "is_wechat_user_agent",
    "is_bot_user_agent",
]