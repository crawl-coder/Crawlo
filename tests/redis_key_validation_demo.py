#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis Key 验证演示脚本
演示如何使用Redis Key验证工具
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils.redis_manager import (
    RedisKeyValidator, 
    validate_redis_key_naming, 
    validate_multiple_redis_keys,
    get_redis_key_info,
    print_validation_report
)


def demonstrate_redis_key_validation():
    """演示Redis Key验证功能"""
    print("=== Redis Key 验证功能演示 ===\n")
    
    # 1. 验证单个有效的Redis Key
    print("1. 验证单个有效的Redis Key:")
    valid_keys = [
        "crawlo:books_distributed:filter:fingerprint",
        "crawlo:books_distributed:queue:requests",
        "crawlo:books_distributed:queue:processing",
        "crawlo:books_distributed:queue:failed",
        "crawlo:books_distributed:item:fingerprint"
    ]
    
    for key in valid_keys:
        is_valid = validate_redis_key_naming(key, "books_distributed")
        print(f"  {key} - {'通过' if is_valid else '失败'}")
    
    print()
    
    # 2. 验证无效的Redis Key
    print("2. 验证无效的Redis Key:")
    invalid_keys = [
        "invalid_format",  # 不以crawlo开头
        "crawlo:books_distributed",  # 部分缺失
        "crawlo:books_distributed:invalid_component:fingerprint",  # 无效组件
        "crawlo:books_distributed:queue:invalid_subcomponent",  # 无效子组件
        "crawlo:wrong_project:filter:fingerprint"  # 项目名称不匹配
    ]
    
    for key in invalid_keys:
        is_valid = validate_redis_key_naming(key, "books_distributed")
        print(f"  {key} - {'通过' if is_valid else '失败'}")
    
    print()
    
    # 3. 批量验证Redis Key
    print("3. 批量验证Redis Key:")
    all_keys = valid_keys + invalid_keys
    is_valid, invalid_keys_list = validate_multiple_redis_keys(all_keys, "books_distributed")
    
    print(f"  批量验证结果: {'全部通过' if is_valid else '存在无效Key'}")
    if not is_valid:
        print("  无效的Key:")
        for key in invalid_keys_list:
            print(f"    - {key}")
    
    print()
    
    # 4. 获取Redis Key信息
    print("4. 获取Redis Key信息:")
    sample_keys = [
        "crawlo:api_data_collection:filter:fingerprint",
        "crawlo:api_data_collection:queue:requests",
        "crawlo:api_data_collection:item:fingerprint"
    ]
    
    for key in sample_keys:
        info = get_redis_key_info(key)
        print(f"  Key: {key}")
        if info['valid']:
            print(f"    框架: {info['framework']}")
            print(f"    项目: {info['project']}")
            print(f"    组件: {info['component']}")
            if 'sub_component' in info:
                print(f"    子组件: {info['sub_component']}")
        else:
            print(f"    错误: {info.get('error', '无效')}")
        print()
    
    # 5. 打印验证报告
    print("5. 打印验证报告:")
    print_validation_report(all_keys, "books_distributed")


def demonstrate_advanced_validation():
    """演示高级验证功能"""
    print("\n=== 高级验证功能演示 ===\n")
    
    validator = RedisKeyValidator()
    
    # 1. 不指定项目名称的验证
    print("1. 不指定项目名称的验证:")
    key = "crawlo:any_project:filter:fingerprint"
    is_valid = validator.validate_key_naming(key)  # 不指定项目名称
    print(f"  {key} - {'通过' if is_valid else '失败'}")
    
    # 2. 验证不同项目的Key
    print("\n2. 验证不同项目的Key:")
    project_keys = {
        "books_distributed": [
            "crawlo:books_distributed:filter:fingerprint",
            "crawlo:books_distributed:queue:requests"
        ],
        "api_data_collection": [
            "crawlo:api_data_collection:filter:fingerprint",
            "crawlo:api_data_collection:queue:requests"
        ]
    }
    
    for project_name, keys in project_keys.items():
        print(f"  项目: {project_name}")
        for key in keys:
            is_valid = validator.validate_key_naming(key, project_name)
            print(f"    {key} - {'通过' if is_valid else '失败'}")


if __name__ == "__main__":
    demonstrate_redis_key_validation()
    demonstrate_advanced_validation()