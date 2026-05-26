#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试去重管道配置一致性
验证在不同模式下，去重管道配置的正确性
"""

import sys
import os
import unittest

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.pipelines.manager import get_builtin_dedup_pipeline_classes, get_manual_dedup_pipeline_classes, get_all_dedup_pipeline_classes


class TestDedupPipelineConsistency(unittest.TestCase):
    """测试去重管道配置一致性"""

    def test_get_builtin_dedup_pipeline_classes(self):
        """测试获取内置型去重管道类名"""
        builtin_classes = get_builtin_dedup_pipeline_classes()
        
        # 验证返回的是列表
        self.assertIsInstance(builtin_classes, list)
        
        # 验证只包含内置型短路径
        expected_builtin = [
            'crawlo.pipelines.MemoryDedupPipeline',
            'crawlo.pipelines.RedisDedupPipeline',
        ]
        self.assertEqual(builtin_classes, expected_builtin)
        
        print("✅ 获取内置型去重管道类名测试通过")

    def test_get_manual_dedup_pipeline_classes(self):
        """测试获取手动型去重管道类名"""
        manual_classes = get_manual_dedup_pipeline_classes()
        
        self.assertIsInstance(manual_classes, list)
        
        # 验证只包含手动型短路径
        expected_manual = [
            'crawlo.pipelines.BloomDedupPipeline',
            'crawlo.pipelines.MySQLDedupPipeline',
            'crawlo.pipelines.DatabaseDedupPipeline',
        ]
        self.assertEqual(manual_classes, expected_manual)
        
        print("✅ 获取手动型去重管道类名测试通过")

    def test_get_all_dedup_pipeline_classes(self):
        """测试获取所有去重管道类名"""
        all_classes = get_all_dedup_pipeline_classes()
        builtin_classes = get_builtin_dedup_pipeline_classes()
        manual_classes = get_manual_dedup_pipeline_classes()
        
        # 全部 = 内置 + 手动
        self.assertEqual(len(all_classes), len(builtin_classes) + len(manual_classes))
        for cls in builtin_classes:
            self.assertIn(cls, all_classes)
        for cls in manual_classes:
            self.assertIn(cls, all_classes)
        
        print("✅ 获取所有去重管道类名测试通过")

    def test_builtin_only_removed_when_default_set(self):
        """测试 DEFAULT_DEDUP_PIPELINE 有值时只移除内置型，保留手动型"""
        from crawlo.pipelines.manager import normalize_pipelines_config, get_builtin_dedup_pipeline_classes
        
        pipelines_config = {
            'crawlo.pipelines.MemoryDedupPipeline': 100,      # 内置型，应被移除
            'crawlo.pipelines.ConsolePipeline': 500,          # 非去重，保留
            'crawlo.pipelines.BloomDedupPipeline': 200,       # 手动型，保留
            'crawlo.pipelines.MySQLPipeline': 800,            # 非去重，保留
        }
        
        pipelines = normalize_pipelines_config(pipelines_config)
        
        # 模拟 _initialize 中的移除逻辑
        builtin_dedup_classes = get_builtin_dedup_pipeline_classes()
        remaining = [(p, pri) for p, pri in pipelines if p not in builtin_dedup_classes]
        
        remaining_paths = [p for p, _ in remaining]
        
        # 内置型被移除
        self.assertNotIn('crawlo.pipelines.MemoryDedupPipeline', remaining_paths)
        # 手动型保留
        self.assertIn('crawlo.pipelines.BloomDedupPipeline', remaining_paths)
        # 非去重保留
        self.assertIn('crawlo.pipelines.ConsolePipeline', remaining_paths)
        self.assertIn('crawlo.pipelines.MySQLPipeline', remaining_paths)
        
        print("✅ 内置型移除 / 手动型保留测试通过")


if __name__ == "__main__":
    print("开始测试去重管道配置一致性...")
    
    try:
        # 运行测试
        unittest.main(verbosity=2)
        
        print("\n🎉 所有测试通过！去重管道配置一致性已正确实现。")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()