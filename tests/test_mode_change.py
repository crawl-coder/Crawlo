#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试运行模式日志级别修改
"""
import sys
import os
sys.path.insert(0, '/')

def test_mode_log_level():
    print("=== 测试运行模式日志级别修改 ===")
    
    # 删除旧的日志文件
    test_log_file = '/Users/oscar/projects/Crawlo/test_mode_change.log'
    if os.path.exists(test_log_file):
        os.remove(test_log_file)
    
    # 准备测试设置
    test_settings = {
        'PROJECT_NAME': 'test_mode_change',
        'LOG_LEVEL': 'INFO',
        'LOG_FILE': test_log_file,
        'RUN_MODE': 'standalone'
    }
    
    try:
        # 初始化框架
        from crawlo.core.framework_initializer import initialize_framework
        settings = initialize_framework(test_settings)
        
        print(f"设置初始化完成: {settings.get('PROJECT_NAME')}")
        
        # 检查日志文件是否包含运行模式信息
        if os.path.exists(test_log_file):
            with open(test_log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"日志文件内容长度: {len(content)} 字符")
                
                # 检查是否还有INFO级别的运行模式信息
                info_lines = [line for line in content.split('\n') if 'INFO' in line and '使用单机模式' in line]
                debug_lines = [line for line in content.split('\n') if 'DEBUG' in line and '使用单机模式' in line]
                
                if info_lines:
                    print("❌ 仍然发现INFO级别的运行模式信息:")
                    for line in info_lines:
                        print(f"   {line}")
                else:
                    print("✅ 没有发现INFO级别的运行模式信息")
                
                if debug_lines:
                    print("✅ 发现DEBUG级别的运行模式信息:")
                    for line in debug_lines:
                        print(f"   {line}")
                else:
                    print("❌ 没有发现DEBUG级别的运行模式信息")
                    
                print("\n所有日志内容:")
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if line.strip():
                        print(f"{i:3d}: {line}")
        else:
            print("❌ 日志文件未创建")
    
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("=== 测试完成 ===")

if __name__ == "__main__":
    test_mode_log_level()