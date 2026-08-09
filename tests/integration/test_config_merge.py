#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置合并测试
测试 Crawlo 框架的配置合并功能
"""

import sys
import os
import unittest

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.settings.setting_manager import SettingManager


class TestConfigMerge(unittest.TestCase):
    """配置合并测试类"""

    def test_middleware_merge(self):
        """测试中间件配置合并"""
        # 用户自定义配置
        user_config = {
            'MIDDLEWARES': [
                'myproject.middlewares.CustomMiddleware',
            ]
        }
        
        settings = SettingManager(user_config)
        
        # 获取合并后的中间件配置（重构后为 dict {path: priority}）
        middlewares = settings.get('MIDDLEWARES')
        
        # 检查默认中间件是否存在
        self.assertIn('crawlo.middleware.RequestIgnoreMiddleware', middlewares)
        self.assertIn('crawlo.middleware.DownloadDelayMiddleware', middlewares)
        
        # 检查自定义中间件是否存在
        self.assertIn('myproject.middlewares.CustomMiddleware', middlewares)
        
        # 检查合并后的顺序是否正确（priority 越小越先执行）
        self.assertLess(
            middlewares['crawlo.middleware.RequestIgnoreMiddleware'],
            middlewares['myproject.middlewares.CustomMiddleware'],
        )

    def test_pipeline_merge(self):
        """测试管道配置合并"""
        # 用户自定义配置
        user_config = {
            'PIPELINES': [
                'myproject.pipelines.CustomPipeline',
            ]
        }
        
        settings = SettingManager(user_config)
        
        # 获取合并后的管道列表
        pipelines = settings.get('PIPELINES')
        
        # 检查默认管道是否存在
        self.assertIn('crawlo.pipelines.ConsolePipeline', pipelines)
        
        # 检查自定义管道是否存在
        self.assertIn('myproject.pipelines.CustomPipeline', pipelines)
        
        # 检查去重管道优先级最小（最先执行）
        dedup_pipeline = settings.get('DEFAULT_DEDUP_PIPELINE')
        self.assertEqual(dedup_pipeline, 'crawlo.pipelines.MemoryDedupPipeline')
        self.assertIn(dedup_pipeline, pipelines)
        self.assertEqual(
            pipelines[dedup_pipeline],
            min(pipelines.values()),
        )

    def test_extension_merge(self):
        """测试扩展配置合并"""
        # 用户自定义配置
        user_config = {
            'EXTENSIONS': [
                'myproject.extensions.CustomExtension',
            ]
        }
        
        settings = SettingManager(user_config)
        
        # 获取合并后的扩展列表
        extensions = settings.get('EXTENSIONS')
        
        # 检查默认扩展是否存在
        self.assertIn('crawlo.extensions.LogIntervalExtension', extensions)
        self.assertIn('crawlo.extensions.LogStats', extensions)
        self.assertIn('crawlo.extensions.CustomLoggerExtension', extensions)
        
        # 检查自定义扩展是否存在
        self.assertIn('myproject.extensions.CustomExtension', extensions)
        
        # 默认扩展与自定义扩展均为默认优先级（500），确保都存在即可
        self.assertIn('crawlo.extensions.LogIntervalExtension', extensions)
        self.assertIn('myproject.extensions.CustomExtension', extensions)

    def test_empty_custom_config(self):
        """测试空自定义配置"""
        # 空用户配置
        user_config = {}
        
        settings = SettingManager(user_config)
        
        # 获取合并后的中间件列表
        middlewares = settings.get('MIDDLEWARES')
        
        # 检查默认中间件是否存在
        self.assertIn('crawlo.middleware.RequestIgnoreMiddleware', middlewares)
        self.assertIn('crawlo.middleware.DownloadDelayMiddleware', middlewares)
        
        # 检查管道和扩展
        pipelines = settings.get('PIPELINES')
        self.assertIn('crawlo.pipelines.ConsolePipeline', pipelines)
        
        extensions = settings.get('EXTENSIONS')
        self.assertIn('crawlo.extensions.LogIntervalExtension', extensions)

    def test_no_custom_config(self):
        """测试无自定义配置"""
        # 无用户配置
        settings = SettingManager()
        
        # 获取合并后的中间件列表
        middlewares = settings.get('MIDDLEWARES')
        
        # 检查默认中间件是否存在
        self.assertIn('crawlo.middleware.RequestIgnoreMiddleware', middlewares)
        self.assertIn('crawlo.middleware.DownloadDelayMiddleware', middlewares)
        
        # 检查管道和扩展
        pipelines = settings.get('PIPELINES')
        self.assertIn('crawlo.pipelines.ConsolePipeline', pipelines)
        
        extensions = settings.get('EXTENSIONS')
        self.assertIn('crawlo.extensions.LogIntervalExtension', extensions)


def main():
    """主测试函数"""
    print("开始配置合并测试...")
    print("=" * 50)
    
    # 运行测试
    unittest.main(argv=['first-arg-is-ignored'], exit=False, verbosity=2)
    
    print("=" * 50)
    print("配置合并测试完成")


if __name__ == "__main__":
    main()