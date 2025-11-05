#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
测试增强后的 get_component_logger 函数
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crawlo.utils.log import get_component_logger


class MockComponent:
    """模拟组件类"""
    pass


class MockSettings:
    """模拟设置类"""
    def __init__(self):
        self.LOG_LEVEL = 'DEBUG'
        self.LOG_LEVEL_MockComponent = 'WARNING'
    
    def get(self, key, default=None):
        return getattr(self, key, default)


def test_get_component_logger():
    """测试 get_component_logger 函数"""
    print("=== 测试 get_component_logger 函数 ===")
    
    # 1. 测试基本用法
    print("1. 测试基本用法...")
    logger1 = get_component_logger(MockComponent)
    print(f"   Logger名称: {logger1.name}")
    print(f"   Logger级别: {logger1.level}")
    
    # 2. 测试带settings的用法
    print("2. 测试带settings的用法...")
    settings = MockSettings()
    logger2 = get_component_logger(MockComponent, settings)
    print(f"   Logger名称: {logger2.name}")
    print(f"   Logger级别: {logger2.level}")
    
    # 3. 测试带level参数的用法
    print("3. 测试带level参数的用法...")
    logger3 = get_component_logger(MockComponent, level='ERROR')
    print(f"   Logger名称: {logger3.name}")
    print(f"   Logger级别: {logger3.level}")
    
    # 4. 测试日志输出
    print("4. 测试日志输出...")
    logger1.info("这是info级别的测试消息")
    logger1.warning("这是warning级别的测试消息")
    logger1.error("这是error级别的测试消息")
    
    print("\n=== 测试完成 ===")


def main():
    """主函数"""
    print("开始测试增强后的 get_component_logger 函数...")
    
    try:
        test_get_component_logger()
        
        print("\n=== 所有测试完成 ===")
        
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())