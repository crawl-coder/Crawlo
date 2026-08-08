#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
循环引用泄漏测试
"""

import weakref
import gc
from crawlo.utils.resource_manager import get_resource_manager, ResourceType


class Parent:
    """父对象"""
    def __init__(self, name):
        self.name = name
        self.children = []
        self.resource_manager = get_resource_manager(f"parent_{name}")
        self.resource_manager.register(
            self,
            self._cleanup,
            ResourceType.OTHER,
            f"parent_{name}"
        )
    
    def add_child(self, child):
        self.children.append(child)
        # 使用弱引用避免循环引用
        child.parent = weakref.ref(self)
    
    def _cleanup(self):
        """清理资源"""
        self.children.clear()


class Child:
    """子对象"""
    def __init__(self, name):
        self.name = name
        self.parent = None


def test_circular_reference_leak():
    """测试循环引用是否正确处理"""
    # 创建父对象和子对象
    parent = Parent("test_parent")
    child = Child("test_child")
    
    # 建立关系（使用弱引用避免循环引用）
    parent.add_child(child)
    
    # 检查资源是否正确注册
    active_resources = parent.resource_manager.get_active_resources()
    assert len(active_resources) == 1
    assert active_resources[0].name == "parent_test_parent"
    
    # 检查弱引用是否正确设置
    assert child.parent is not None
    parent_ref = child.parent()  # 获取弱引用指向的对象
    assert parent_ref is not None
    assert parent_ref.name == "test_parent"
    
    # 清理资源
    import asyncio
    asyncio.run(parent.resource_manager.cleanup_all())
    
    # 验证资源已清理
    active_resources = parent.resource_manager.get_active_resources()
    assert len(active_resources) == 0
    
    # 强制垃圾回收
    gc.collect()
    
    print("循环引用泄漏测试通过")


if __name__ == "__main__":
    test_circular_reference_leak()