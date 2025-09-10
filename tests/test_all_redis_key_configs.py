#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
所有Redis Key配置测试脚本
用于验证所有配置文件是否符合新的Redis key命名规范
"""
import sys
import os
import re

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_all_redis_key_configs():
    """测试所有Redis key配置"""
    print("🔍 测试所有Redis key配置...")
    
    try:
        # 检查示例项目配置文件
        example_projects = [
            "examples/books_distributed/books_distributed/settings.py",
            "examples/api_data_collection/api_data_collection/settings.py",
            "examples/telecom_licenses_distributed/telecom_licenses_distributed/settings.py"
        ]
        
        for project_config in example_projects:
            print(f"   检查 {project_config}...")
            if not os.path.exists(project_config):
                print(f"❌ 配置文件不存在: {project_config}")
                return False
                
            with open(project_config, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否移除了旧的REDIS_KEY配置
            if re.search(r'REDIS_KEY\s*=', content) and 'crawlo:{PROJECT_NAME}:filter:fingerprint' not in content:
                print(f"❌ {project_config}中仍然存在旧的REDIS_KEY配置")
                return False
                
            # 检查是否添加了新的注释
            if 'crawlo:{PROJECT_NAME}:filter:fingerprint' not in content:
                print(f"❌ {project_config}中缺少新的Redis key命名规范注释")
                return False
                
            print(f"      ✅ {project_config}符合新的Redis key命名规范")
        
        # 检查模板文件
        template_file = "crawlo/templates/project/settings.py.tmpl"
        print(f"   检查 {template_file}...")
        if not os.path.exists(template_file):
            print(f"❌ 模板文件不存在: {template_file}")
            return False
            
        with open(template_file, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # 检查是否移除了旧的REDIS_KEY配置
        if "REDIS_KEY = f'{{project_name}}:fingerprint'" in template_content:
            print("❌ 模板文件中仍然存在旧的REDIS_KEY配置")
            return False
            
        # 检查是否添加了新的注释
        if '# crawlo:{project_name}:filter:fingerprint (请求去重)' not in template_content:
            print("❌ 模板文件中缺少请求去重的Redis key命名规范注释")
            return False
            
        if '# crawlo:{project_name}:item:fingerprint (数据项去重)' not in template_content:
            print("❌ 模板文件中缺少数据项去重的Redis key命名规范注释")
            return False
            
        print(f"      ✅ {template_file}符合新的Redis key命名规范")
        
        # 检查mode_manager.py
        mode_manager_file = "crawlo/mode_manager.py"
        print(f"   检查 {mode_manager_file}...")
        if not os.path.exists(mode_manager_file):
            print(f"❌ 文件不存在: {mode_manager_file}")
            return False
            
        with open(mode_manager_file, 'r', encoding='utf-8') as f:
            mode_manager_content = f.read()
        
        # 检查是否移除了旧的REDIS_KEY配置
        if "'REDIS_KEY': f'{project_name}:fingerprint'" in mode_manager_content:
            print("❌ mode_manager.py中仍然存在旧的REDIS_KEY配置")
            return False
            
        # 检查是否添加了新的注释
        if 'crawlo:{project_name}:filter:fingerprint (请求去重)' not in mode_manager_content:
            print("❌ mode_manager.py中缺少新的Redis key命名规范注释")
            return False
            
        print(f"      ✅ {mode_manager_file}符合新的Redis key命名规范")
        
        # 检查默认设置文件
        default_settings_file = "crawlo/settings/default_settings.py"
        print(f"   检查 {default_settings_file}...")
        if not os.path.exists(default_settings_file):
            print(f"❌ 文件不存在: {default_settings_file}")
            return False
            
        with open(default_settings_file, 'r', encoding='utf-8') as f:
            default_settings_content = f.read()
        
        # 检查是否移除了旧的REDIS_KEY配置
        if re.search(r'REDIS_KEY\s*=\s*.*fingerprint', default_settings_content):
            print("❌ 默认设置文件中仍然存在旧的REDIS_KEY配置")
            return False
            
        print(f"      ✅ {default_settings_file}符合新的Redis key命名规范")
        
        print("✅ 所有Redis key配置测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 开始所有Redis key配置测试...")
    print("=" * 50)
    
    try:
        success = test_all_redis_key_configs()
        
        print("=" * 50)
        if success:
            print("🎉 所有测试通过！所有配置文件符合新的Redis key命名规范")
        else:
            print("❌ 测试失败，请检查配置文件")
            return 1
            
    except Exception as e:
        print("=" * 50)
        print(f"❌ 测试过程中发生异常: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)