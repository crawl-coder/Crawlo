#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试User-Agent列表的功能
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.data.user_agents import (
    DESKTOP_USER_AGENTS,
    MOBILE_USER_AGENTS,
    BOT_USER_AGENTS,
    CHROME_USER_AGENTS,
    FIREFOX_USER_AGENTS,
    SAFARI_USER_AGENTS,
    EDGE_USER_AGENTS,
    OPERA_USER_AGENTS,
    ALL_USER_AGENTS,
    USER_AGENTS_BY_TYPE,
    get_user_agents,
    get_random_user_agent
)


def test_user_agent_counts():
    """测试User-Agent数量"""
    print("=== User-Agent数量测试 ===")
    print(f"桌面浏览器User-Agent数量: {len(DESKTOP_USER_AGENTS)}")
    print(f"移动设备User-Agent数量: {len(MOBILE_USER_AGENTS)}")
    print(f"爬虫User-Agent数量: {len(BOT_USER_AGENTS)}")
    print(f"Chrome User-Agent数量: {len(CHROME_USER_AGENTS)}")
    print(f"Firefox User-Agent数量: {len(FIREFOX_USER_AGENTS)}")
    print(f"Safari User-Agent数量: {len(SAFARI_USER_AGENTS)}")
    print(f"Edge User-Agent数量: {len(EDGE_USER_AGENTS)}")
    print(f"Opera User-Agent数量: {len(OPERA_USER_AGENTS)}")
    print(f"所有User-Agent数量: {len(ALL_USER_AGENTS)}")
    print()


def test_get_user_agents():
    """测试get_user_agents函数"""
    print("=== get_user_agents函数测试 ===")
    for device_type in ["desktop", "mobile", "bot", "all", "chrome", "firefox", "safari", "edge", "opera"]:
        user_agents = get_user_agents(device_type)
        print(f"{device_type}类型User-Agent数量: {len(user_agents)}")
    print()


def test_get_random_user_agent():
    """测试get_random_user_agent函数"""
    print("=== get_random_user_agent函数测试 ===")
    for device_type in ["desktop", "mobile", "all", "chrome", "firefox"]:
        ua = get_random_user_agent(device_type)
        print(f"{device_type}类型随机User-Agent: {ua[:100]}...")
    print()


def test_user_agents_content():
    """测试User-Agent内容"""
    print("=== User-Agent内容测试 ===")
    
    # 检查是否包含最新的浏览器版本
    chrome_ua_count = sum(1 for ua in ALL_USER_AGENTS if "Chrome/136" in ua)
    firefox_ua_count = sum(1 for ua in ALL_USER_AGENTS if "Firefox/136" in ua)
    safari_ua_count = sum(1 for ua in ALL_USER_AGENTS if "Version/18" in ua and "Safari" in ua)
    
    print(f"包含Chrome 136的User-Agent数量: {chrome_ua_count}")
    print(f"包含Firefox 136的User-Agent数量: {firefox_ua_count}")
    print(f"包含Safari 18的User-Agent数量: {safari_ua_count}")
    
    # 检查是否包含移动设备User-Agent
    ios_ua_count = sum(1 for ua in ALL_USER_AGENTS if "iPhone" in ua or "iPad" in ua)
    android_ua_count = sum(1 for ua in ALL_USER_AGENTS if "Android" in ua)
    
    print(f"包含iOS设备的User-Agent数量: {ios_ua_count}")
    print(f"包含Android设备的User-Agent数量: {android_ua_count}")
    print()


def main():
    """主测试函数"""
    print("开始测试User-Agent列表...\n")
    
    test_user_agent_counts()
    test_get_user_agents()
    test_get_random_user_agent()
    test_user_agents_content()
    
    print("所有测试完成!")


if __name__ == "__main__":
    main()