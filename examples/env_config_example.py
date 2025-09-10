#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境变量配置工具使用示例
展示如何在 Crawlo 项目中正确使用环境变量配置工具
"""
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils.env_config import get_env_var, get_redis_config, get_runtime_config
from crawlo.settings.setting_manager import SettingManager
from crawlo.settings import default_settings


def example_basic_usage():
    """基本使用示例"""
    print("=== 基本环境变量使用示例 ===")
    
    # 获取字符串环境变量
    project_name = get_env_var('PROJECT_NAME', 'my_crawler', str)
    print(f"项目名称: {project_name}")
    
    # 获取整数环境变量
    concurrency = get_env_var('CONCURRENCY', 8, int)
    print(f"并发数: {concurrency}")
    
    # 获取布尔环境变量
    debug_mode = get_env_var('DEBUG_MODE', False, bool)
    print(f"调试模式: {debug_mode}")


def example_redis_config():
    """Redis配置示例"""
    print("\n=== Redis配置示例 ===")
    
    # 获取Redis配置
    redis_config = get_redis_config()
    print(f"Redis主机: {redis_config['REDIS_HOST']}")
    print(f"Redis端口: {redis_config['REDIS_PORT']}")
    print(f"Redis密码: {'*' * len(redis_config['REDIS_PASSWORD']) if redis_config['REDIS_PASSWORD'] else '无'}")
    print(f"Redis数据库: {redis_config['REDIS_DB']}")
    
    # 生成Redis URL
    if redis_config['REDIS_PASSWORD']:
        redis_url = f"redis://:{redis_config['REDIS_PASSWORD']}@{redis_config['REDIS_HOST']}:{redis_config['REDIS_PORT']}/{redis_config['REDIS_DB']}"
    else:
        redis_url = f"redis://{redis_config['REDIS_HOST']}:{redis_config['REDIS_PORT']}/{redis_config['REDIS_DB']}"
    
    print(f"Redis URL: {redis_url}")


def example_runtime_config():
    """运行时配置示例"""
    print("\n=== 运行时配置示例 ===")
    
    # 获取运行时配置
    runtime_config = get_runtime_config()
    print(f"运行模式: {runtime_config['CRAWLO_MODE']}")
    print(f"项目名称: {runtime_config['PROJECT_NAME']}")
    print(f"并发数: {runtime_config['CONCURRENCY']}")


def example_settings_integration():
    """与Settings集成示例"""
    print("\n=== 与Settings集成示例 ===")
    
    # 创建设置管理器
    settings = SettingManager()
    
    # 更新Redis相关设置
    redis_config = get_redis_config()
    settings.set('REDIS_HOST', redis_config['REDIS_HOST'])
    settings.set('REDIS_PORT', redis_config['REDIS_PORT'])
    settings.set('REDIS_PASSWORD', redis_config['REDIS_PASSWORD'])
    settings.set('REDIS_DB', redis_config['REDIS_DB'])
    
    # 更新运行时设置
    runtime_config = get_runtime_config()
    settings.set('PROJECT_NAME', runtime_config['PROJECT_NAME'])
    settings.set('RUN_MODE', runtime_config['CRAWLO_MODE'])
    settings.set('CONCURRENCY', runtime_config['CONCURRENCY'])
    
    # 显示一些关键设置
    print(f"项目名称: {settings.get('PROJECT_NAME')}")
    print(f"运行模式: {settings.get('RUN_MODE')}")
    print(f"并发数: {settings.get_int('CONCURRENCY')}")
    print(f"Redis主机: {settings.get('REDIS_HOST')}")
    print(f"Redis端口: {settings.get_int('REDIS_PORT')}")


def example_env_setup():
    """环境变量设置示例"""
    print("\n=== 环境变量设置示例 ===")
    print("在命令行中设置环境变量的示例:")
    print("  Windows (PowerShell):")
    print("    $env:PROJECT_NAME = \"my_distributed_crawler\"")
    print("    $env:REDIS_HOST = \"redis.example.com\"")
    print("    $env:REDIS_PORT = \"6380\"")
    print("    $env:CONCURRENCY = \"16\"")
    print("    $env:CRAWLO_MODE = \"distributed\"")
    print()
    print("  Linux/macOS:")
    print("    export PROJECT_NAME=\"my_distributed_crawler\"")
    print("    export REDIS_HOST=\"redis.example.com\"")
    print("    export REDIS_PORT=\"6380\"")
    print("    export CONCURRENCY=\"16\"")
    print("    export CRAWLO_MODE=\"distributed\"")


if __name__ == '__main__':
    # 设置一些测试环境变量
    os.environ['PROJECT_NAME'] = 'test_crawler'
    os.environ['CONCURRENCY'] = '12'
    os.environ['DEBUG_MODE'] = 'true'
    os.environ['REDIS_HOST'] = 'redis.test.com'
    os.environ['REDIS_PORT'] = '6380'
    os.environ['REDIS_PASSWORD'] = 'test_password'
    os.environ['CRAWLO_MODE'] = 'distributed'
    
    # 运行示例
    example_basic_usage()
    example_redis_config()
    example_runtime_config()
    example_settings_integration()
    example_env_setup()
    
    # 清理测试环境变量
    for var in ['PROJECT_NAME', 'CONCURRENCY', 'DEBUG_MODE', 'REDIS_HOST', 
                'REDIS_PORT', 'REDIS_PASSWORD', 'CRAWLO_MODE']:
        if var in os.environ:
            del os.environ[var]