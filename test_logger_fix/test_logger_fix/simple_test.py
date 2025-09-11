#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
简单测试logger pickle问题修复
"""
import sys
import os
from copy import deepcopy

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.settings.setting_manager import SettingManager
from crawlo.utils.log import get_logger


def test_logger_pickle_fix():
    """测试logger pickle问题是否已修复"""
    print("开始测试logger pickle问题修复...")
    
    # 创建SettingManager实例
    settings = SettingManager()
    settings.set('TEST_KEY', 'test_value')
    
    # 添加一个logger对象到settings中（模拟可能的情况）
    logger = get_logger('test_logger')
    settings.set('TEST_LOGGER', logger)
    
    try:
        # 尝试深度复制settings对象（这会触发pickle问题）
        copied_settings = deepcopy(settings)
        print("✅ SettingManager deepcopy成功，logger pickle问题已修复！")
        print(f"原始settings TEST_KEY: {settings.get('TEST_KEY')}")
        print(f"复制settings TEST_KEY: {copied_settings.get('TEST_KEY')}")
        return True
    except Exception as e:
        print(f"❌ SettingManager deepcopy失败: {e}")
        if "logger cannot be pickled" in str(e):
            print("❌ Logger pickle问题仍然存在！")
        return False


def test_settings_copy_method():
    """测试SettingManager的copy方法"""
    print("\n开始测试SettingManager.copy()方法...")
    
    # 创建SettingManager实例
    settings = SettingManager()
    settings.set('TEST_KEY', 'test_value')
    
    # 添加一个logger对象到settings中（模拟可能的情况）
    logger = get_logger('test_logger_copy')
    settings.set('TEST_LOGGER', logger)
    
    try:
        # 尝试使用copy方法
        copied_settings = settings.copy()
        print("✅ SettingManager.copy()方法执行成功！")
        print(f"原始settings TEST_KEY: {settings.get('TEST_KEY')}")
        print(f"复制settings TEST_KEY: {copied_settings.get('TEST_KEY')}")
        return True
    except Exception as e:
        print(f"❌ SettingManager.copy()方法执行失败: {e}")
        if "logger cannot be pickled" in str(e):
            print("❌ Logger pickle问题仍然存在！")
        return False


if __name__ == "__main__":
    print("=== 测试Logger Pickle问题修复 ===")
    success1 = test_logger_pickle_fix()
    success2 = test_settings_copy_method()
    
    if success1 and success2:
        print("\n🎉 所有测试通过，logger pickle问题已成功修复！")
    else:
        print("\n❌ 部分测试失败，请检查代码。")