#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
测试分布式运行命令
"""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class TestDistributedCommand(unittest.TestCase):
    """测试分布式运行命令"""

    def test_import_run_distributed_command(self):
        """测试能否正确导入run_distributed命令模块"""
        try:
            from crawlo.commands.run_distributed import main
            self.assertTrue(callable(main))
        except ImportError as e:
            self.fail(f"无法导入run_distributed命令模块: {e}")

    def test_command_registration(self):
        """测试命令是否正确注册"""
        from crawlo.commands import get_commands
        commands = get_commands()
        self.assertIn('run-distributed', commands)
        self.assertEqual(commands['run-distributed'], 'crawlo.commands.run_distributed')

    @patch('crawlo.commands.run_distributed.parse_args')
    @patch('crawlo.commands.run_distributed.get_project_root')
    def test_main_function_structure(self, mock_get_project_root, mock_parse_args):
        """测试主函数结构"""
        from crawlo.commands.run_distributed import main
        
        # 模拟参数和项目根目录
        mock_args = MagicMock()
        mock_args.spider = 'test_spider'
        mock_args.json = False
        mock_args.no_stats = False
        mock_parse_args.return_value = mock_args
        mock_get_project_root.return_value = None  # 模拟找不到项目根目录的情况
        
        # 调用主函数，应该返回错误码1
        result = main(['test_spider'])
        self.assertEqual(result, 1)

if __name__ == '__main__':
    unittest.main()