#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模板文件内容测试脚本
用于验证模板文件是否符合新的Redis key命名规范
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_template_content():
    """测试模板文件内容"""
    print("🔍 测试模板文件内容...")
    
    try:
        # 检查settings.py.tmpl模板文件
        template_file = "crawlo/templates/project/settings.py.tmpl"
        if not os.path.exists(template_file):
            print(f"模板文件不存在: {template_file}")
            return False
            
        with open(template_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否移除了旧的REDIS_KEY配置
        old_config = "REDIS_KEY = f'{{project_name}}:fingerprint'"
        if old_config in content:
            print("仍然存在旧的REDIS_KEY配置")
            return False
        print("      已移除旧的REDIS_KEY配置")
        
        # 检查是否添加了新的注释
        filter_comment = "# crawlo:{project_name}:filter:fingerprint (请求去重)"
        if filter_comment not in content:
            print("缺少请求去重的Redis key命名规范注释")
            return False
        print("      包含请求去重的Redis key命名规范注释")
        
        item_comment = "# crawlo:{project_name}:item:fingerprint (数据项去重)"
        if item_comment not in content:
            print("缺少数据项去重的Redis key命名规范注释")
            return False
        print("      包含数据项去重的Redis key命名规范注释")
        
        # 检查是否保留了队列名称配置
        queue_config = "SCHEDULER_QUEUE_NAME = f'crawlo:{{project_name}}:queue:requests'"
        if queue_config not in content:
            print("缺少队列名称配置")
            return False
        print("      包含队列名称配置")
        
        print("模板文件内容测试通过！")
        return True
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        return False


def main():
    """主测试函数"""
    print("开始模板文件内容测试...")
    print("=" * 50)
    
    try:
        success = test_template_content()
        
        print("=" * 50)
        if success:
            print("所有测试通过！模板文件符合新的Redis key命名规范")
        else:
            print("测试失败，请检查模板文件")
            return 1
            
    except Exception as e:
        print("=" * 50)
        print(f"测试过程中发生异常: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)