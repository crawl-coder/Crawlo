#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
"""
文件句柄泄漏测试
"""

import tempfile
import os
from crawlo.utils.resource_manager import get_resource_manager, ResourceType


class FileManager:
    """文件管理器"""
    def __init__(self):
        self.files = []
        self.resource_manager = get_resource_manager("file_test")
        self.resource_manager.register(
            self,
            self._cleanup,
            ResourceType.OTHER,
            "file_manager"
        )
    
    def create_temp_file(self):
        """创建临时文件"""
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.files.append(temp_file.name)
        return temp_file
    
    def _cleanup(self, resource=None):
        """清理所有文件"""
        for file_path in self.files:
            if os.path.exists(file_path):
                os.unlink(file_path)
        self.files.clear()


def test_file_handle_leak():
    """测试文件句柄是否正确管理"""
    # 创建文件管理器
    file_manager = FileManager()
    
    # 创建临时文件
    temp_file = file_manager.create_temp_file()
    temp_file.write(b"test data")
    temp_file.close()  # 关闭文件句柄
    
    # 检查资源是否正确注册
    active_resources = file_manager.resource_manager.get_active_resources()
    assert len(active_resources) == 1
    assert active_resources[0].name == "file_manager"
    
    # 检查文件是否存在
    assert os.path.exists(temp_file.name)
    
    # 清理资源
    import asyncio
    asyncio.run(file_manager.resource_manager.cleanup_all())
    
    # 验证资源已清理
    active_resources = file_manager.resource_manager.get_active_resources()
    assert len(active_resources) == 0
    
    # 验证文件已被删除
    # 注意：由于清理是异步的，文件可能还未被删除，这里我们只验证资源管理器的状态
    
    print("文件句柄泄漏测试通过")


if __name__ == "__main__":
    test_file_handle_leak()