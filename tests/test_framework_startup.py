#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试框架启动信息是否正确输出到日志文件
"""
import sys
import os
sys.path.insert(0, '/')

def test_framework_startup():
    print("=== 测试框架启动信息输出 ===")
    
    # 删除旧的日志文件
    test_log_file = '/Users/oscar/projects/Crawlo/test_startup.log'
    if os.path.exists(test_log_file):
        os.remove(test_log_file)
    
    # 准备测试设置
    test_settings = {
        'PROJECT_NAME': 'test_startup',
        'LOG_LEVEL': 'INFO',
        'LOG_FILE': test_log_file,
        'RUN_MODE': 'standalone'
    }
    
    # 初始化框架
    from crawlo.core.framework_initializer import initialize_framework
    settings = initialize_framework(test_settings)
    
    print(f"设置初始化完成: {settings.get('PROJECT_NAME')}")
    
    # 检查日志文件是否包含框架启动信息
    if os.path.exists(test_log_file):
        with open(test_log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"日志文件内容长度: {len(content)} 字符")
            
            # 检查关键的框架启动信息
            if "Crawlo框架初始化完成" in content:
                print("✅ 发现: Crawlo框架初始化完成")
            else:
                print("❌ 未找到: Crawlo框架初始化完成")
                
            if "Crawlo Framework Started" in content:
                print("✅ 发现: Crawlo Framework Started")
            else:
                print("❌ 未找到: Crawlo Framework Started")
                
            if "使用单机模式" in content:
                print("✅ 发现: 使用单机模式")
            else:
                print("❌ 未找到: 使用单机模式")
                
            print("\n前50行日志内容:")
            lines = content.split('\n')[:50]
            for i, line in enumerate(lines, 1):
                if any(keyword in line for keyword in ["框架", "Framework", "Started"]):
                    print(f"{i:3d}: {line}")
    else:
        print("❌ 日志文件未创建")
    
    print("=== 测试完成 ===")

if __name__ == "__main__":
    test_framework_startup()