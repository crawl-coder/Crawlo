#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Redis Key 验证工具
=================
提供 Redis Key 命名规范的验证功能
"""

import re
from typing import List, Tuple
from crawlo.utils.log import get_logger


class RedisKeyValidator:
    """Redis Key 验证器"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    def validate_key_naming(self, key: str, project_name: str = None) -> bool:
        """
        验证Redis Key是否符合命名规范
        
        Args:
            key: Redis Key
            project_name: 项目名称（可选）
            
        Returns:
            bool: 是否符合命名规范
        """
        if not isinstance(key, str) or not key:
            return False
        
        # 检查是否以 crawlo: 开头
        if not key.startswith('crawlo:'):
            return False
        
        # 分割Key部分
        parts = key.split(':')
        if len(parts) < 3:
            return False
        
        # 检查基本结构
        if parts[0] != 'crawlo':
            return False
        
        # 如果提供了项目名称，检查是否匹配
        if project_name and parts[1] != project_name:
            return False
        
        # 检查组件类型
        valid_components = ['filter', 'queue', 'item']
        if parts[2] not in valid_components:
            return False
        
        # 检查子组件（根据组件类型）
        if parts[2] == 'queue':
            valid_subcomponents = ['requests', 'processing', 'failed']
            if len(parts) < 4 or parts[3] not in valid_subcomponents:
                return False
        elif parts[2] == 'filter':
            if len(parts) < 4 or parts[3] != 'fingerprint':
                return False
        elif parts[2] == 'item':
            if len(parts) < 4 or parts[3] != 'fingerprint':
                return False
        
        return True
    
    def validate_multiple_keys(self, keys: List[str], project_name: str = None) -> Tuple[bool, List[str]]:
        """
        验证多个Redis Key
        
        Args:
            keys: Redis Key列表
            project_name: 项目名称（可选）
            
        Returns:
            Tuple[bool, List[str]]: (是否全部有效, 无效的Key列表)
        """
        invalid_keys = []
        for key in keys:
            if not self.validate_key_naming(key, project_name):
                invalid_keys.append(key)
        
        return len(invalid_keys) == 0, invalid_keys
    
    def get_key_info(self, key: str) -> dict:
        """
        获取Redis Key的信息
        
        Args:
            key: Redis Key
            
        Returns:
            dict: Key信息
        """
        if not self.validate_key_naming(key):
            return {
                'valid': False,
                'error': 'Key不符合命名规范'
            }
        
        parts = key.split(':')
        info = {
            'valid': True,
            'framework': parts[0],
            'project': parts[1],
            'component': parts[2]
        }
        
        if parts[2] == 'queue' and len(parts) >= 4:
            info['sub_component'] = parts[3]
        elif len(parts) >= 4:
            info['sub_component'] = parts[3]
        
        return info


# 便利函数
def validate_redis_key_naming(key: str, project_name: str = None) -> bool:
    """
    验证Redis Key是否符合命名规范（便利函数）
    
    Args:
        key: Redis Key
        project_name: 项目名称（可选）
        
    Returns:
        bool: 是否符合命名规范
    """
    validator = RedisKeyValidator()
    return validator.validate_key_naming(key, project_name)


def validate_multiple_redis_keys(keys: List[str], project_name: str = None) -> Tuple[bool, List[str]]:
    """
    验证多个Redis Key（便利函数）
    
    Args:
        keys: Redis Key列表
        project_name: 项目名称（可选）
        
    Returns:
        Tuple[bool, List[str]]: (是否全部有效, 无效的Key列表)
    """
    validator = RedisKeyValidator()
    return validator.validate_multiple_keys(keys, project_name)


def get_redis_key_info(key: str) -> dict:
    """
    获取Redis Key的信息（便利函数）
    
    Args:
        key: Redis Key
        
    Returns:
        dict: Key信息
    """
    validator = RedisKeyValidator()
    return validator.get_key_info(key)


def print_validation_report(keys: List[str], project_name: str = None):
    """
    打印Redis Key验证报告
    
    Args:
        keys: Redis Key列表
        project_name: 项目名称（可选）
    """
    validator = RedisKeyValidator()
    is_valid, invalid_keys = validator.validate_multiple_keys(keys, project_name)
    
    print("=" * 50)
    print("Redis Key 命名规范验证报告")
    print("=" * 50)
    
    if is_valid:
        print("✅ 所有Redis Key命名规范验证通过")
    else:
        print("❌ 发现不符合命名规范的Redis Key:")
        for key in invalid_keys:
            print(f"  - {key}")
    
    print("\nKey 详细信息:")
    for key in keys:
        info = validator.get_key_info(key)
        if info['valid']:
            print(f"  ✅ {key}")
            print(f"     框架: {info['framework']}")
            print(f"     项目: {info['project']}")
            print(f"     组件: {info['component']}")
            if 'sub_component' in info:
                print(f"     子组件: {info['sub_component']}")
        else:
            print(f"  ❌ {key} - {info.get('error', '无效')}")
    
    print("=" * 50)