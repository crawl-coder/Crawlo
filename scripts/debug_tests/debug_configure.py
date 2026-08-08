#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
逐步调试LoggerManager.configure
"""
import sys
import os
sys.path.insert(0, '/')

from crawlo.utils.log import LoggerManager

print("=== 逐步调试LoggerManager.configure ===")

print("1. 检查初始状态")
print(f"   _early_initialized: {LoggerManager._early_initialized}")
print(f"   _configured: {LoggerManager._configured}")

print("2. 调用early_initialize")
LoggerManager.early_initialize()
print(f"   _early_initialized: {LoggerManager._early_initialized}")

print("3. 进入configure - 开始")
# 模拟configure方法的各个步骤
with LoggerManager._config_lock:
    print("   获得锁")
    
    if LoggerManager._configured:
        print("   已配置，直接返回")
    else:
        print("   开始配置...")
        
        # 更新状态
        print("   设置_log_state")
        from crawlo.utils.log import _log_state
        _log_state['current_step'] = 'basic_setup'
        
        print("   处理参数")
        kwargs = {'LOG_LEVEL': 'INFO', 'LOG_FILE': 'test.log'}
        get_val = lambda k, d=None: kwargs.get(k, d)
        
        filename = get_val('LOG_FILE')
        level = get_val('LOG_LEVEL', None)
        if level is None:
            level = 'INFO'
        
        print(f"     filename: {filename}")
        print(f"     level: {level}")
        
        print("   设置默认值")
        LoggerManager._default_filename = filename
        LoggerManager._default_level = LoggerManager._to_level(level)
        LoggerManager._default_file_level = LoggerManager._to_level(level)
        LoggerManager._default_console_level = LoggerManager._default_level
        
        print("   清空缓存")
        LoggerManager.logger_cache.clear()
        
        print("   设置已配置状态")
        LoggerManager._configured = True
        _log_state['current_step'] = 'full_config'
        
        print("   配置完成")

print("4. 测试创建logger")
from crawlo.utils.log import get_logger
logger = get_logger('test')
print(f"   Logger: {logger}")
print(f"   Handlers: {len(logger.handlers)}")

print("=== 调试完成 ===")