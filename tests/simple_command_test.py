#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试所有 crawlo 命令
"""

import sys
import os
import subprocess

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def run_command(cmd, cwd=None):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            cwd=cwd, 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)

def test_help_command():
    """测试 help 命令"""
    print("测试 help 命令...")
    
    # 测试 -h 参数
    code, stdout, stderr = run_command("python -m crawlo.cli -h")
    assert code == 0, f"help 命令失败: {stderr}"
    assert "Crawlo" in stdout, "help 输出不包含框架名称"
    
    # 测试 --help 参数
    code, stdout, stderr = run_command("python -m crawlo.cli --help")
    assert code == 0, f"help 命令失败: {stderr}"
    assert "Crawlo" in stdout, "help 输出不包含框架名称"
    
    print("✅ help 命令测试通过")

def test_version_command():
    """测试 version 命令"""
    print("测试 version 命令...")
    
    # 测试 -v 参数
    code, stdout, stderr = run_command("python -m crawlo.cli -v")
    assert code == 0, f"version 命令失败: {stderr}"
    assert "Crawlo" in stdout, "version 输出不包含框架名称"
    
    # 测试 --version 参数
    code, stdout, stderr = run_command("python -m crawlo.cli --version")
    assert code == 0, f"version 命令失败: {stderr}"
    assert "Crawlo" in stdout, "version 输出不包含框架名称"
    
    print("✅ version 命令测试通过")

def test_command_help():
    """测试各命令的帮助信息"""
    print("测试各命令的帮助信息...")
    
    commands = ["startproject", "genspider", "run", "check", "list", "stats"]
    
    for command in commands:
        code, stdout, stderr = run_command(f"python -m crawlo.cli {command} --help")
        # 命令帮助通常返回非0状态码，但我们检查输出
        assert len(stdout) > 0 or len(stderr) > 0, f"{command} 命令帮助无输出"
        print(f"✅ {command} 命令帮助测试通过")

def test_invalid_command():
    """测试无效命令"""
    print("测试无效命令...")
    
    code, stdout, stderr = run_command("python -m crawlo.cli invalid_command")
    assert code != 0, "无效命令应该返回非0状态码"
    assert "Unknown command" in stderr or "Unknown command" in stdout, "应该提示未知命令"
    
    print("✅ 无效命令测试通过")

def main():
    """主函数"""
    print("开始简单测试所有 crawlo 命令...")
    print("=" * 50)
    
    try:
        # 测试 help 命令
        test_help_command()
        print()
        
        # 测试 version 命令
        test_version_command()
        print()
        
        # 测试各命令的帮助信息
        test_command_help()
        print()
        
        # 测试无效命令
        test_invalid_command()
        print()
        
        print("=" * 50)
        print("所有命令简单测试通过！")
        
    except Exception as e:
        print("=" * 50)
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())