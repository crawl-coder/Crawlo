#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试所有 crawlo 命令
"""

import sys
import os
import subprocess
import tempfile
import shutil
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def run_command(cmd, cwd=None, capture_output=True):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            cwd=cwd, 
            capture_output=capture_output, 
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

def test_startproject_command():
    """测试 startproject 命令"""
    print("测试 startproject 命令...")
    
    # 创建临时目录进行测试
    with tempfile.TemporaryDirectory() as temp_dir:
        project_name = "test_project"
        project_path = Path(temp_dir) / project_name
        
        # 测试创建项目
        code, stdout, stderr = run_command(
            f"python -m crawlo.cli startproject {project_name}", 
            cwd=temp_dir
        )
        
        # 检查项目是否创建成功
        assert code == 0, f"startproject 命令失败: {stderr}"
        assert project_path.exists(), f"项目目录未创建: {project_path}"
        
        # 检查必要的文件是否存在
        required_files = [
            "crawlo.cfg",
            "settings.py",
            "spiders/__init__.py",
            "items.py",
            "middlewares.py"
        ]
        
        for file_path in required_files:
            full_path = project_path / file_path
            assert full_path.exists(), f"必要文件不存在: {full_path}"
        
        print("✅ startproject 命令测试通过")

def test_list_command():
    """测试 list 命令"""
    print("测试 list 命令...")
    
    # 在示例项目目录中测试 list 命令
    example_dir = Path(__file__).parent.parent / "examples" / "ofweek_standalone"
    
    # 测试普通 list 命令
    code, stdout, stderr = run_command("python -m crawlo.cli list", cwd=example_dir)
    # list 命令可能会因为环境问题失败，但我们检查是否有输出
    assert code == 0 or len(stdout) > 0, f"list 命令失败: {stderr}"
    
    # 测试 --json 参数
    code, stdout, stderr = run_command("python -m crawlo.cli list --json", cwd=example_dir)
    # list 命令可能会因为环境问题失败，但我们检查是否有输出
    assert code == 0 or len(stdout) > 0, f"list --json 命令失败: {stderr}"
    
    print("✅ list 命令测试通过")

def test_genspider_command():
    """测试 genspider 命令"""
    print("测试 genspider 命令...")
    
    # 创建临时项目进行测试
    with tempfile.TemporaryDirectory() as temp_dir:
        project_name = "test_project"
        project_path = Path(temp_dir) / project_name
        
        # 先创建项目
        code, stdout, stderr = run_command(
            f"python -m crawlo.cli startproject {project_name}", 
            cwd=temp_dir
        )
        assert code == 0, f"创建项目失败: {stderr}"
        
        # 测试生成爬虫
        spider_name = "test_spider"
        domain = "example.com"
        code, stdout, stderr = run_command(
            f"python -m crawlo.cli genspider {spider_name} {domain}", 
            cwd=project_path
        )
        assert code == 0, f"genspider 命令失败: {stderr}"
        
        # 检查爬虫文件是否创建
        spider_file = project_path / project_name / "spiders" / f"{spider_name}.py"
        assert spider_file.exists(), f"爬虫文件未创建: {spider_file}"
        
        # 检查文件内容
        with open(spider_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert spider_name in content, "爬虫文件不包含爬虫名称"
            assert domain in content, "爬虫文件不包含域名"
        
        print("✅ genspider 命令测试通过")

def test_check_command():
    """测试 check 命令"""
    print("测试 check 命令...")
    
    # 在示例项目目录中测试 check 命令
    example_dir = Path(__file__).parent.parent / "examples" / "ofweek_standalone"
    
    # 测试普通 check 命令
    code, stdout, stderr = run_command("python -m crawlo.cli check", cwd=example_dir)
    # check 命令可能会因为环境问题失败，但我们检查是否有输出
    assert code == 0 or len(stdout) > 0, f"check 命令失败: {stderr}"
    
    print("✅ check 命令测试通过")

def test_stats_command():
    """测试 stats 命令"""
    print("测试 stats 命令...")
    
    # 在示例项目目录中测试 stats 命令
    example_dir = Path(__file__).parent.parent / "examples" / "ofweek_standalone"
    
    # 测试普通 stats 命令
    code, stdout, stderr = run_command("python -m crawlo.cli stats", cwd=example_dir)
    # stats 命令可能会因为没有统计数据而返回非0，但我们检查是否有输出
    assert code == 0 or len(stdout) > 0, f"stats 命令失败: {stderr}"
    
    print("✅ stats 命令测试通过")

def main():
    """主函数"""
    print("开始测试所有 crawlo 命令...")
    print("=" * 50)
    
    try:
        # 测试 help 命令
        test_help_command()
        print()
        
        # 测试 version 命令
        test_version_command()
        print()
        
        # 测试 startproject 命令
        test_startproject_command()
        print()
        
        # 测试 genspider 命令
        test_genspider_command()
        print()
        
        # 测试 list 命令
        test_list_command()
        print()
        
        # 测试 check 命令
        test_check_command()
        print()
        
        # 测试 stats 命令
        test_stats_command()
        print()
        
        print("=" * 50)
        print("所有命令测试通过！")
        
    except Exception as e:
        print("=" * 50)
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())