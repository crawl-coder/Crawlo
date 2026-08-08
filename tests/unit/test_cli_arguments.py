#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试CLI参数解析
验证crawlo run命令是否正确解析--log-level、--config和--concurrency参数
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.commands.run import main as run_main


class TestCLIArguments(unittest.TestCase):
    
    def setUp(self):
        """测试前准备"""
        # 保存原始的sys.path
        self.original_path = sys.path[:]
        
    def tearDown(self):
        """测试后清理"""
        # 恢复原始的sys.path
        sys.path = self.original_path[:]
    
    @patch('crawlo.commands.run._find_project_root')
    @patch('crawlo.commands.run.initialize_framework')
    @patch('crawlo.commands.run.CrawlerProcess')
    def test_log_level_argument(self, mock_crawler_process, mock_initialize, mock_find_project):
        """测试--log-level参数解析"""
        # 模拟项目环境
        mock_find_project.return_value = os.path.join(os.path.dirname(__file__), '..')
        mock_initialize.return_value = {}
        mock_process_instance = MagicMock()
        mock_crawler_process.return_value = mock_process_instance
        mock_process_instance.get_spider_names.return_value = ['test_spider']
        mock_process_instance.is_spider_registered.return_value = True
        mock_process_instance.get_spider_class.return_value = MagicMock(__name__='TestSpider')
        
        # 测试参数解析
        args = ['test_spider', '--log-level', 'DEBUG']
        result = run_main(args)
        
        # 验证initialize_framework被调用时传入了正确的日志级别
        mock_initialize.assert_called_once()
        call_args = mock_initialize.call_args
        if call_args and call_args[0]:  # 检查位置参数
            settings = call_args[0][0]
            self.assertEqual(settings.get('LOG_LEVEL'), 'DEBUG')
        elif call_args and call_args[1]:  # 检查关键字参数
            settings = call_args[1].get('custom_settings', {})
            self.assertEqual(settings.get('LOG_LEVEL'), 'DEBUG')
    
    @patch('crawlo.commands.run._find_project_root')
    @patch('crawlo.commands.run.initialize_framework')
    @patch('crawlo.commands.run.CrawlerProcess')
    def test_concurrency_argument(self, mock_crawler_process, mock_initialize, mock_find_project):
        """测试--concurrency参数解析"""
        # 模拟项目环境
        mock_find_project.return_value = os.path.join(os.path.dirname(__file__), '..')
        mock_initialize.return_value = {}
        mock_process_instance = MagicMock()
        mock_crawler_process.return_value = mock_process_instance
        mock_process_instance.get_spider_names.return_value = ['test_spider']
        mock_process_instance.is_spider_registered.return_value = True
        mock_process_instance.get_spider_class.return_value = MagicMock(__name__='TestSpider')
        
        # 测试参数解析
        args = ['test_spider', '--concurrency', '32']
        result = run_main(args)
        
        # 验证initialize_framework被调用时传入了正确的并发数
        mock_initialize.assert_called_once()
        call_args = mock_initialize.call_args
        if call_args and call_args[0]:  # 检查位置参数
            settings = call_args[0][0]
            self.assertEqual(settings.get('CONCURRENCY'), 32)
        elif call_args and call_args[1]:  # 检查关键字参数
            settings = call_args[1].get('custom_settings', {})
            self.assertEqual(settings.get('CONCURRENCY'), 32)
    
    @patch('crawlo.commands.run._find_project_root')
    @patch('crawlo.commands.run.initialize_framework')
    @patch('crawlo.commands.run.CrawlerProcess')
    def test_combined_arguments(self, mock_crawler_process, mock_initialize, mock_find_project):
        """测试组合参数解析"""
        # 模拟项目环境
        mock_find_project.return_value = os.path.join(os.path.dirname(__file__), '..')
        mock_initialize.return_value = {}
        mock_process_instance = MagicMock()
        mock_crawler_process.return_value = mock_process_instance
        mock_process_instance.get_spider_names.return_value = ['test_spider']
        mock_process_instance.is_spider_registered.return_value = True
        mock_process_instance.get_spider_class.return_value = MagicMock(__name__='TestSpider')
        
        # 测试参数解析
        args = ['test_spider', '--log-level', 'DEBUG', '--concurrency', '16']
        result = run_main(args)
        
        # 验证initialize_framework被调用时传入了正确的参数
        mock_initialize.assert_called_once()
        call_args = mock_initialize.call_args
        if call_args and call_args[0]:  # 检查位置参数
            settings = call_args[0][0]
            self.assertEqual(settings.get('LOG_LEVEL'), 'DEBUG')
            self.assertEqual(settings.get('CONCURRENCY'), 16)
        elif call_args and call_args[1]:  # 检查关键字参数
            settings = call_args[1].get('custom_settings', {})
            self.assertEqual(settings.get('LOG_LEVEL'), 'DEBUG')
            self.assertEqual(settings.get('CONCURRENCY'), 16)


if __name__ == '__main__':
    unittest.main()