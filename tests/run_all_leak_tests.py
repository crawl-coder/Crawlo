#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
运行所有资源泄漏测试
"""

import asyncio
import subprocess
import sys
import os


def run_test_script(script_name):
    """运行单个测试脚本"""
    try:
        print(f"运行测试: {script_name}")
        # 设置PYTHONPATH以包含项目根目录
        env = os.environ.copy()
        env['PYTHONPATH'] = '/Users/oscar/projects/Crawlo:' + env.get('PYTHONPATH', '')
        
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=True, 
                              text=True, 
                              timeout=30,
                              env=env)
        if result.returncode == 0:
            print(f"✓ {script_name} 通过")
            if result.stdout:
                print(f"  输出: {result.stdout.strip()}")
        else:
            print(f"✗ {script_name} 失败")
            if result.stderr:
                print(f"  错误: {result.stderr.strip()}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"✗ {script_name} 超时")
        return False
    except Exception as e:
        print(f"✗ {script_name} 异常: {e}")
        return False


async def run_async_test_script(script_name):
    """运行异步测试脚本"""
    try:
        print(f"运行异步测试: {script_name}")
        # 设置PYTHONPATH以包含项目根目录
        env = os.environ.copy()
        env['PYTHONPATH'] = '/Users/oscar/projects/Crawlo:' + env.get('PYTHONPATH', '')
        
        process = await asyncio.create_subprocess_exec(
            sys.executable, script_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            print(f"✓ {script_name} 通过")
            if stdout:
                print(f"  输出: {stdout.decode().strip()}")
        else:
            print(f"✗ {script_name} 失败")
            if stderr:
                print(f"  错误: {stderr.decode().strip()}")
        return process.returncode == 0
    except Exception as e:
        print(f"✗ {script_name} 异常: {e}")
        return False


async def main():
    """主函数"""
    print("开始运行所有资源泄漏测试...\n")
    
    # 获取所有测试脚本
    test_scripts = [
        "test_http_connection_leak.py",
        "test_redis_connection_leak.py",
        "test_file_handle_leak.py",
        "test_database_connection_leak.py",
        "test_browser_leak.py",
        "test_circular_reference_leak.py",
        "test_cache_leak.py",
        "test_thread_leak.py",
        "test_coroutine_leak.py",
        "test_queue_leak.py"
    ]
    
    # 运行同步测试
    sync_tests = [
        "test_file_handle_leak.py",
        "test_circular_reference_leak.py",
        "test_thread_leak.py"
    ]
    
    # 运行异步测试
    async_tests = [
        "test_http_connection_leak.py",
        "test_redis_connection_leak.py",
        "test_database_connection_leak.py",
        "test_browser_leak.py",
        "test_cache_leak.py",
        "test_coroutine_leak.py",
        "test_queue_leak.py"
    ]
    
    passed = 0
    failed = 0
    
    # 运行同步测试
    for script in sync_tests:
        script_path = os.path.join(os.path.dirname(__file__), script)
        if os.path.exists(script_path):
            if run_test_script(script_path):
                passed += 1
            else:
                failed += 1
        else:
            print(f"跳过不存在的测试: {script}")
    
    # 运行异步测试
    for script in async_tests:
        script_path = os.path.join(os.path.dirname(__file__), script)
        if os.path.exists(script_path):
            if await run_async_test_script(script_path):
                passed += 1
            else:
                failed += 1
        else:
            print(f"跳过不存在的测试: {script}")
    
    # 输出总结
    print(f"\n测试完成:")
    print(f"  通过: {passed}")
    print(f"  失败: {failed}")
    print(f"  总计: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 所有资源泄漏测试通过!")
        return 0
    else:
        print(f"\n❌ {failed} 个测试失败!")
        return 1


if __name__ == "__main__":
    # 添加项目根目录到sys.path
    project_root = '/Users/oscar/projects/Crawlo'
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)