#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
User-Agent列表
包含各种设备和浏览器的User-Agent字符串，用于爬虫伪装
"""

# 桌面浏览器User-Agent
DESKTOP_USER_AGENTS = [
    # Chrome (最新版本)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    
    # Chrome (较新版本)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    
    # Chrome (常用版本)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    
    # Firefox (最新版本)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:136.0) Gecko/20100101 Firefox/136.0",
    "Mozilla/5.0 (X11; Linux i686; rv:136.0) Gecko/20100101 Firefox/136.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
    
    # Firefox (较新版本)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:135.0) Gecko/20100101 Firefox/135.0",
    "Mozilla/5.0 (X11; Linux i686; rv:135.0) Gecko/20100101 Firefox/135.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0",
    
    # Safari (最新版本)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    
    # Safari (较新版本)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    
    # Edge (最新版本)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.2917.92",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/135.0.2916.12",
    
    # Edge (较新版本)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.2915.72",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.2914.89",
    
    # Opera
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 OPR/122.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 OPR/122.0.0.0",
]

# 移动设备User-Agent
MOBILE_USER_AGENTS = [
    # iPhone (最新版本)
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1",
    
    # iPhone (较新版本)
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    
    # iPad (最新版本)
    "Mozilla/5.0 (iPad; CPU OS 18_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1",
    
    # iPad (较新版本)
    "Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    
    # Android (最新版本)
    "Mozilla/5.0 (Linux; Android 15; SM-S921B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.6367.118 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.6367.118 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.6367.118 Mobile Safari/537.36",
    
    # Android (较新版本)
    "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.6367.118 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.6367.118 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.6367.118 Mobile Safari/537.36",
    
    # Android平板
    "Mozilla/5.0 (Linux; Android 14; SM-X916C Build/UP1A.231005.007; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/136.0.6367.118 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-X906C Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/136.0.6367.118 Safari/537.36",
    
    # 其他移动浏览器
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Mobile Safari/537.36 EdgA/136.0.2917.92",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1 EdgiOS/136.2917.92",
]

# 爬虫/机器人User-Agent (用于测试)
BOT_USER_AGENTS = [
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)",
    "Mozilla/5.0 (compatible; Baiduspider/2.0; +http://www.baidu.com/search/spider.html)",
    "Mozilla/5.0 (compatible; Yahoo! Slurp; http://help.yahoo.com/help/us/ysearch/slurp)",
    "Mozilla/5.0 (compatible; DuckDuckBot/1.1; +http://duckduckgo.com/duckduckbot.html)",
    "Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)",
    "Mozilla/5.0 (compatible; facebookexternalhit/1.1; +http://www.facebook.com/externalhit_uatext.php)",
    "Mozilla/5.0 (compatible; Twitterbot/1.0)",
]

# 按浏览器分类的User-Agent
CHROME_USER_AGENTS = [
    ua for ua in DESKTOP_USER_AGENTS + MOBILE_USER_AGENTS 
    if "Chrome" in ua and "Edg" not in ua and "OPR" not in ua
]

FIREFOX_USER_AGENTS = [
    ua for ua in DESKTOP_USER_AGENTS + MOBILE_USER_AGENTS 
    if "Firefox" in ua
]

SAFARI_USER_AGENTS = [
    ua for ua in DESKTOP_USER_AGENTS + MOBILE_USER_AGENTS 
    if "Safari" in ua and "Chrome" not in ua
]

EDGE_USER_AGENTS = [
    ua for ua in DESKTOP_USER_AGENTS + MOBILE_USER_AGENTS 
    if "Edg" in ua
]

OPERA_USER_AGENTS = [
    ua for ua in DESKTOP_USER_AGENTS + MOBILE_USER_AGENTS 
    if "OPR" in ua
]

# 所有User-Agent的组合列表
ALL_USER_AGENTS = DESKTOP_USER_AGENTS + MOBILE_USER_AGENTS

# 按设备类型分类的User-Agent字典
USER_AGENTS_BY_TYPE = {
    "desktop": DESKTOP_USER_AGENTS,
    "mobile": MOBILE_USER_AGENTS,
    "bot": BOT_USER_AGENTS,
    "all": ALL_USER_AGENTS,
    "chrome": CHROME_USER_AGENTS,
    "firefox": FIREFOX_USER_AGENTS,
    "safari": SAFARI_USER_AGENTS,
    "edge": EDGE_USER_AGENTS,
    "opera": OPERA_USER_AGENTS,
}


def get_user_agents(device_type="all"):
    """
    获取指定类型的User-Agent列表
    
    Args:
        device_type (str): 设备类型，可选值: "desktop", "mobile", "bot", "all", "chrome", "firefox", "safari", "edge", "opera"
        
    Returns:
        list: User-Agent字符串列表
    """
    return USER_AGENTS_BY_TYPE.get(device_type, ALL_USER_AGENTS)


def get_random_user_agent(device_type="all"):
    """
    获取随机User-Agent
    
    Args:
        device_type (str): 设备类型，可选值: "desktop", "mobile", "bot", "all", "chrome", "firefox", "safari", "edge", "opera"
        
    Returns:
        str: 随机User-Agent字符串
    """
    import random
    user_agents = get_user_agents(device_type)
    return random.choice(user_agents) if user_agents else ""


# 导出常用的User-Agent列表
__all__ = [
    "DESKTOP_USER_AGENTS",
    "MOBILE_USER_AGENTS",
    "BOT_USER_AGENTS",
    "CHROME_USER_AGENTS",
    "FIREFOX_USER_AGENTS",
    "SAFARI_USER_AGENTS",
    "EDGE_USER_AGENTS",
    "OPERA_USER_AGENTS",
    "ALL_USER_AGENTS",
    "USER_AGENTS_BY_TYPE",
    "get_user_agents",
    "get_random_user_agent"
]