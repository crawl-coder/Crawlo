#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模板项目Redis Key测试脚本
用于验证通过模板生成的项目是否符合新的Redis key命名规范
"""
import sys
import os
import tempfile
import shutil
import subprocess
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_template_project_redis_key():
    """测试模板项目Redis key命名规范"""
    print("🔍 测试模板项目Redis key命名规范...")
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # 切换到临时目录
            original_cwd = os.getcwd()
            os.chdir(temp_dir)
            
            # 创建测试项目
            print("   1. 创建测试项目...")
            result = subprocess.run([
                sys.executable, "-m", "crawlo.commands.startproject", "test_project"
            ], cwd=original_cwd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ 创建项目失败: {result.stderr}")
                return False
            
            print("      ✅ 项目创建成功")
            
            # 检查生成的文件
            project_dir = Path(temp_dir) / "test_project"
            if not project_dir.exists():
                print("❌ 项目目录未创建")
                return False
                
            settings_file = project_dir / "test_project" / "settings.py"
            if not settings_file.exists():
                print("❌ settings.py文件未创建")
                return False
            
            # 读取settings.py内容
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings_content = f.read()
            
            # 检查是否移除了旧的REDIS_KEY配置
            if "REDIS_KEY = f'{{project_name}}:fingerprint'" in settings_content:
                print("❌ 仍然存在旧的REDIS_KEY配置")
                return False
                
            # 检查是否添加了新的注释
            if "# crawlo:{project_name}:filter:fingerprint (请求去重)" not in settings_content:
                print("❌ 缺少新的Redis key命名规范注释")
                return False
                
            if "# crawlo:{project_name}:item:fingerprint (数据项去重)" not in settings_content:
                print("❌ 缺少数据项去重的Redis key命名规范注释")
                return False
            
            print("      ✅ settings.py符合新的Redis key命名规范")
            
            # 检查crawlo.cfg
            cfg_file = project_dir / "crawlo.cfg"
            if not cfg_file.exists():
                print("❌ crawlo.cfg文件未创建")
                return False
                
            with open(cfg_file, 'r', encoding='utf-8') as f:
                cfg_content = f.read()
                
            if "default = test_project.settings" not in cfg_content:
                print("❌ crawlo.cfg配置不正确")
                return False
                
            print("      ✅ crawlo.cfg配置正确")
            
            print("✅ 模板项目Redis key命名规范测试通过！")
            return True
            
        except Exception as e:
            print(f"❌ 测试过程中发生错误: {e}")
            return False
        finally:
            # 恢复原始工作目录
            os.chdir(original_cwd)


def main():
    """主测试函数"""
    print("🚀 开始模板项目Redis key命名规范测试...")
    print("=" * 50)
    
    try:
        success = test_template_project_redis_key()
        
        print("=" * 50)
        if success:
            print("🎉 所有测试通过！模板项目符合新的Redis key命名规范")
        else:
            print("❌ 测试失败，请检查模板文件")
            return 1
            
    except Exception as e:
        print("=" * 50)
        print(f"❌ 测试过程中发生异常: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)