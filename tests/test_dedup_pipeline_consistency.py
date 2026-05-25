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

from crawlo.pipelines.manager import remove_dedup_pipelines, get_dedup_pipeline_classes


class TestDedupPipelineConsistency(unittest.TestCase):
    """测试去重管道配置一致性"""

    def test_get_dedup_pipeline_classes(self):
        """测试获取所有去重管道类名"""
        dedup_classes = get_dedup_pipeline_classes()
        
        # 验证返回的是列表
        self.assertIsInstance(dedup_classes, list)
        
        # 验证包含所有已知的去重管道类
        expected_classes = [
            'crawlo.pipelines.dedup.memory.MemoryDedupPipeline',
            'crawlo.pipelines.dedup.redis.RedisDedupPipeline',
            'crawlo.pipelines.dedup.bloom.BloomDedupPipeline',
            'crawlo.pipelines.dedup.mysql.DatabaseDedupPipeline'
        ]
        
        for expected_class in expected_classes:
            self.assertIn(expected_class, dedup_classes, f"缺失去重管道类: {expected_class}")
        
        print("✅ 获取去重管道类名测试通过")

    def test_remove_dedup_pipelines_empty_list(self):
        """测试从空列表中移除去重管道"""
        pipelines = []
        result = remove_dedup_pipelines(pipelines)
        self.assertEqual(result, [], "空列表处理错误")
        print("✅ 空列表处理测试通过")

    def test_remove_dedup_pipelines_no_dedup(self):
        """测试从不包含去重管道的列表中移除去重管道"""
        pipelines = [
            'crawlo.pipelines.console.ConsolePipeline',
            'crawlo.pipelines.file.csv.CSVPipeline',
            'crawlo.pipelines.sql.mysql.MySQLPipeline'
        ]
        result = remove_dedup_pipelines(pipelines)
        self.assertEqual(result, pipelines, "不应该修改不包含去重管道的列表")
        print("✅ 不包含去重管道的列表处理测试通过")

    def test_remove_dedup_pipelines_with_dedup(self):
        """测试从包含去重管道的列表中移除去重管道"""
        pipelines = [
            'crawlo.pipelines.dedup.memory.MemoryDedupPipeline',
            'crawlo.pipelines.console.ConsolePipeline',
            'crawlo.pipelines.dedup.redis.RedisDedupPipeline',
            'crawlo.pipelines.file.csv.CSVPipeline',
            'crawlo.pipelines.dedup.bloom.BloomDedupPipeline'
        ]
        
        expected = [
            'crawlo.pipelines.console.ConsolePipeline',
            'crawlo.pipelines.file.csv.CSVPipeline'
        ]
        
        result = remove_dedup_pipelines(pipelines)
        self.assertEqual(result, expected, "去重管道移除错误")
        print("✅ 包含去重管道的列表处理测试通过")

    def test_remove_dedup_pipelines_all_dedup(self):
        """测试从只包含去重管道的列表中移除去重管道"""
        pipelines = [
            'crawlo.pipelines.dedup.memory.MemoryDedupPipeline',
            'crawlo.pipelines.dedup.redis.RedisDedupPipeline',
            'crawlo.pipelines.dedup.bloom.BloomDedupPipeline',
            'crawlo.pipelines.dedup.mysql.DatabaseDedupPipeline'
        ]
        
        result = remove_dedup_pipelines(pipelines)
        self.assertEqual(result, [], "应该返回空列表")
        print("✅ 只包含去重管道的列表处理测试通过")

    def test_remove_dedup_pipelines_mixed_order(self):
        """测试混合顺序的管道列表"""
        pipelines = [
            'crawlo.pipelines.file.csv.CSVPipeline',
            'crawlo.pipelines.dedup.memory.MemoryDedupPipeline',
            'crawlo.pipelines.console.ConsolePipeline',
            'crawlo.pipelines.dedup.bloom.BloomDedupPipeline',
            'crawlo.pipelines.sql.mysql.MySQLPipeline',
            'crawlo.pipelines.dedup.redis.RedisDedupPipeline'
        ]
        
        expected = [
            'crawlo.pipelines.file.csv.CSVPipeline',
            'crawlo.pipelines.console.ConsolePipeline',
            'crawlo.pipelines.sql.mysql.MySQLPipeline'
        ]
        
        result = remove_dedup_pipelines(pipelines)
        self.assertEqual(result, expected, "混合顺序处理错误")
        print("✅ 混合顺序的管道列表处理测试通过")


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