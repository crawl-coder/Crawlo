#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis Key 验证工具测试脚本
用于验证Redis Key验证工具的功能
"""
import sys
import os
import unittest

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils.redis_manager import (
    RedisKeyValidator, 
    validate_redis_key_naming, 
    validate_multiple_redis_keys,
    get_redis_key_info,
    print_validation_report
)


class TestRedisKeyValidator(unittest.TestCase):
    """Redis Key 验证器测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.validator = RedisKeyValidator()
    
    def test_valid_filter_key(self):
        """测试有效的过滤器Key"""
        key = "crawlo:test_project:filter:fingerprint"
        self.assertTrue(self.validator.validate_key_naming(key, "test_project"))
    
    def test_valid_queue_keys(self):
        """测试有效的队列Key"""
        keys = [
            "crawlo:test_project:queue:requests",
            "crawlo:test_project:queue:processing",
            "crawlo:test_project:queue:failed"
        ]
        
        for key in keys:
            self.assertTrue(self.validator.validate_key_naming(key, "test_project"))
    
    def test_valid_item_key(self):
        """测试有效的数据项Key"""
        key = "crawlo:test_project:item:fingerprint"
        self.assertTrue(self.validator.validate_key_naming(key, "test_project"))
    
    def test_invalid_key_format(self):
        """测试无效的Key格式"""
        invalid_keys = [
            "invalid_format",  # 不以crawlo开头
            "crawlo:test_project",  # 部分缺失
            "crawlo:test_project:invalid_component:fingerprint",  # 无效组件
            "crawlo:test_project:queue:invalid_subcomponent",  # 无效子组件
            "",  # 空字符串
            None  # None值
        ]
        
        for key in invalid_keys:
            self.assertFalse(self.validator.validate_key_naming(key, "test_project"))
    
    def test_project_name_mismatch(self):
        """测试项目名称不匹配"""
        key = "crawlo:wrong_project:filter:fingerprint"
        self.assertFalse(self.validator.validate_key_naming(key, "test_project"))
    
    def test_convenience_functions(self):
        """测试便利函数"""
        # 测试单个Key验证
        key = "crawlo:test_project:filter:fingerprint"
        self.assertTrue(validate_redis_key_naming(key, "test_project"))
        
        # 测试多个Key验证
        keys = [
            "crawlo:test_project:filter:fingerprint",
            "crawlo:test_project:queue:requests"
        ]
        is_valid, invalid_keys = validate_multiple_redis_keys(keys, "test_project")
        self.assertTrue(is_valid)
        self.assertEqual(len(invalid_keys), 0)
        
        # 测试Key信息获取
        key = "crawlo:test_project:queue:requests"
        info = get_redis_key_info(key)
        self.assertTrue(info['valid'])
        self.assertEqual(info['framework'], 'crawlo')
        self.assertEqual(info['project'], 'test_project')
        self.assertEqual(info['component'], 'queue')
        self.assertEqual(info['sub_component'], 'requests')
    
    def test_multiple_key_validation(self):
        """测试多个Key验证"""
        keys = [
            "crawlo:test_project:filter:fingerprint",  # 有效
            "crawlo:test_project:queue:requests",      # 有效
            "crawlo:test_project:queue:processing",    # 有效
            "crawlo:test_project:queue:failed",        # 有效
            "crawlo:test_project:item:fingerprint",    # 有效
            "invalid_key_format"                       # 无效
        ]
        
        is_valid, invalid_keys = self.validator.validate_multiple_keys(keys, "test_project")
        self.assertFalse(is_valid)
        self.assertEqual(len(invalid_keys), 1)
        self.assertEqual(invalid_keys[0], "invalid_key_format")


def main():
    """主测试函数"""
    print("开始Redis Key验证工具测试...")
    print("=" * 50)
    
    # 运行测试
    unittest.main(argv=['first-arg-is-ignored'], exit=False, verbosity=2)
    
    print("=" * 50)
    print("Redis Key验证工具测试完成")


if __name__ == "__main__":
    main()