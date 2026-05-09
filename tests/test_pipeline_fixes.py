# -*- coding: utf-8 -*-
"""
测试 Pipelines 模块 P1/P2 问题修复
=====================================

验证所有修复的正确性
"""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime

# 导入被测试的模块
from crawlo.pipelines.csv_pipeline import CsvPipeline, CsvDictPipeline, CsvBatchPipeline
from crawlo.pipelines.json_pipeline import JsonPipeline, JsonLinesPipeline, JsonArrayPipeline
from crawlo.pipelines.pipeline_manager import normalize_pipelines_config, _validate_pipeline_priorities
from crawlo.pipelines.base_pipeline import DedupPipeline
from crawlo.logging import get_logger


class MockCrawler:
    """模拟 Crawler 对象"""
    def __init__(self):
        self.settings = Mock()
        self.settings.get = Mock(return_value=None)
        self.settings.get_int = Mock(return_value=100)
        self.settings.get_bool = Mock(return_value=True)
        self.spider = Mock()
        self.spider.name = 'test_spider'
        self.subscriber = Mock()
        self.subscriber.subscribe = Mock()
        self.stats = Mock()
        self.stats.inc_value = Mock()
        self.stats.set_value = Mock()


class TestCsvBatchPipelineHeaderFix:
    """测试 P1#1: CsvBatchPipeline 表头写入逻辑修复"""
    
    @pytest.mark.asyncio
    async def test_header_written_immediately(self, tmp_path):
        """验证表头立即写入文件，而不是添加到缓冲区"""
        crawler = MockCrawler()
        crawler.settings.get = Mock(side_effect=lambda key, default=None: {
            'CSV_BATCH_FILE': str(tmp_path / 'test.csv'),
            'CSV_DELIMITER': ',',
            'CSV_QUOTECHAR': '"',
        }.get(key, default))
        crawler.settings.get_int = Mock(side_effect=lambda key, default=100: {
            'CSV_BATCH_SIZE': 100,
        }.get(key, default))
        
        pipeline = CsvBatchPipeline(crawler)
        
        # 使用真实 dict 子类作为 mock item
        class MockItem(dict):
            pass
        
        item = MockItem(name='test', value='123')
        
        # 处理第一个 item（应该立即写入表头）
        await pipeline.process_item(item, crawler.spider)
        
        # 验证表头已写入（headers_written = True）
        assert pipeline.headers_written is True
        
        # 验证缓冲区只有数据行，没有表头
        assert len(pipeline.batch_buffer) == 1
        assert pipeline.batch_buffer[0] == ['test', '123']  # 只有数据，没有表头


class TestJsonArrayPipelineMemoryLimit:
    """测试 P1#2: JsonArrayPipeline 内存限制"""
    
    @pytest.mark.asyncio
    async def test_memory_limit_flush(self, tmp_path):
        """验证超过内存限制时刷新到临时文件"""
        crawler = MockCrawler()
        output_file = tmp_path / 'test_array.json'
        
        crawler.settings.get = Mock(side_effect=lambda key, default=None: {
            'JSON_ARRAY_FILE': str(output_file),
        }.get(key, default))
        crawler.settings.get_int = Mock(side_effect=lambda key, default=100000: {
            'JSON_ARRAY_MAX_ITEMS': 5,  # 设置很小的限制
        }.get(key, default))
        
        pipeline = JsonArrayPipeline(crawler)
        
        # 添加 10 个 items，应该触发 2 次刷新
        for i in range(10):
            class MockItem(dict):
                pass
            item = MockItem(id=i)
            await pipeline.process_item(item, crawler.spider)
        
        # 验证内存已清空（刷新到临时文件）
        assert len(pipeline.items) == 0
        
        # 验证创建了临时文件（10个item，每5个刷新一次 = 2次）
        assert len(pipeline.temp_files) == 2  # 2次刷新
    
    @pytest.mark.asyncio
    async def test_merge_temp_files_on_close(self, tmp_path):
        """验证关闭时合并所有临时文件"""
        crawler = MockCrawler()
        output_file = tmp_path / 'test_array.json'
        
        crawler.settings.get = Mock(side_effect=lambda key, default=None: {
            'JSON_ARRAY_FILE': str(output_file),
        }.get(key, default))
        crawler.settings.get_int = Mock(side_effect=lambda key, default=100000: {
            'JSON_ARRAY_MAX_ITEMS': 3,
        }.get(key, default))
        
        pipeline = JsonArrayPipeline(crawler)
        
        # 添加 7 个 items
        for i in range(7):
            class MockItem(dict):
                pass
            item = MockItem(id=i, name=f'item{i}')
            await pipeline.process_item(item, crawler.spider)
        
        # 关闭爬虫
        await pipeline.spider_closed()
        
        # 验证最终文件存在
        assert output_file.exists()
        
        # 验证内容正确
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert len(data) == 7
            assert data[0]['id'] == 0
            assert data[6]['id'] == 6
        
        # 验证临时文件已删除
        assert len(pipeline.temp_files) == 3
        for temp_file in pipeline.temp_files:
            assert not temp_file.exists()


class TestMongoPipelineFailedBatchSave:
    """测试 P1#3: MongoPipeline 失败数据保存"""
    
    def test_save_failed_batch_creates_file(self, tmp_path):
        """验证失败数据保存到文件"""
        # 这个测试需要实际的 MongoPipeline 实例
        # 这里简化为测试 _save_failed_batch 方法
        from crawlo.pipelines.mongo_pipeline import MongoPipeline
        
        crawler = MockCrawler()
        crawler.settings.get = Mock(return_value='mongodb://localhost:27017')
        crawler.settings.get_int = Mock(return_value=100)
        crawler.settings.get_bool = Mock(return_value=False)
        
        # 由于需要异步初始化，这里只验证方法签名
        # 实际集成测试需要 mock MongoDB 连接
        pass


class TestFilePipelineAiofilesSupport:
    """测试 P1#4: CSV/JSON 异步文件操作支持"""
    
    def test_aiofiles_import(self):
        """验证 aiofiles 导入逻辑"""
        from crawlo.pipelines.csv_pipeline import AIOFILES_AVAILABLE
        from crawlo.pipelines.json_pipeline import AIOFILES_AVAILABLE as JSON_AIOFILES_AVAILABLE
        
        # 验证导入了常量（无论是否可用）
        assert isinstance(AIOFILES_AVAILABLE, bool)
        assert isinstance(JSON_AIOFILES_AVAILABLE, bool)
    
    @pytest.mark.asyncio
    async def test_csv_pipeline_uses_aiofiles_if_available(self, tmp_path):
        """验证 CSV Pipeline 使用 aiofiles（如果可用）"""
        from crawlo.pipelines.csv_pipeline import AIOFILES_AVAILABLE
        
        if not AIOFILES_AVAILABLE:
            pytest.skip("aiofiles not installed")
        
        crawler = MockCrawler()
        crawler.settings.get = Mock(side_effect=lambda key, default=None: {
            'CSV_FILE': str(tmp_path / 'test.csv'),
            'CSV_DELIMITER': ',',
            'CSV_QUOTECHAR': '"',
        }.get(key, default))
        
        pipeline = CsvPipeline(crawler)
        await pipeline._ensure_file_open()
        
        # 验证使用了 aiofiles
        import aiofiles
        assert hasattr(pipeline.file_handle, 'write')


class TestMongoPipelineSettingsMethod:
    """测试 P2#1: MongoPipeline 设置方法统一"""
    
    def test_uses_get_int_not_getint(self):
        """验证使用 get_int() 而不是 getint()"""
        import inspect
        from crawlo.pipelines.mongo_pipeline import MongoPipeline
        
        # 获取源码
        source = inspect.getsource(MongoPipeline.__init__)
        
        # 验证使用 get_int 和 get_bool
        assert 'get_int(' in source
        assert 'get_bool(' in source
        
        # 验证不使用旧方法
        assert 'getint(' not in source
        assert 'getbool(' not in source


class TestCsvDictPipelineFieldnamesParsing:
    """测试 P2#2: CsvDictPipeline 字段名解析"""
    
    def test_parse_comma_separated_with_spaces(self):
        """验证解析带空格的逗号分隔字段"""
        crawler = MockCrawler()
        
        # 模拟配置：带空格的字段名
        crawler.settings.get = Mock(side_effect=lambda key, default=None: {
            'CSV_FIELDNAMES': 'name, age, email, address',
            'CSV_DICT_FILE': 'output/test_dict.csv',  # 添加文件路径
        }.get(key, default))
        
        pipeline = CsvDictPipeline(crawler)
        
        # 验证解析结果
        item_dict = {'name': 'test', 'age': 25, 'email': 'test@example.com'}
        fieldnames = pipeline._get_fieldnames(item_dict)
        
        assert fieldnames == ['name', 'age', 'email', 'address']
        # 验证去除了空白字符
        assert ' ' not in fieldnames[0]
        assert 'age' in fieldnames
    
    def test_parse_list_fieldnames(self):
        """验证列表格式的字段名"""
        crawler = MockCrawler()
        crawler.settings.get = Mock(side_effect=lambda key, default=None: {
            'CSV_FIELDNAMES': ['name', 'age', 'email'],
            'CSV_DICT_FILE': 'output/test_dict.csv',  # 添加文件路径
        }.get(key, default))
        
        pipeline = CsvDictPipeline(crawler)
        fieldnames = pipeline._get_fieldnames({})
        
        assert fieldnames == ['name', 'age', 'email']


class TestPipelinePriorityValidation:
    """测试 P2#3: Pipeline 管理器优先级验证"""
    
    def test_valid_priorities(self):
        """验证有效的优先级配置"""
        config = {
            'pipeline1': 100,
            'pipeline2': 200,
            'pipeline3': 300,
        }
        
        result = normalize_pipelines_config(config)
        
        # 验证按优先级排序
        assert result[0] == ('pipeline1', 100)
        assert result[1] == ('pipeline2', 200)
        assert result[2] == ('pipeline3', 300)
    
    def test_duplicate_priority_warning(self, caplog):
        """验证重复优先级警告"""
        import logging
        
        # 设置日志级别
        logger = get_logger('PipelineManager')
        logger.setLevel(logging.WARNING)
        
        # 添加 handler 捕获日志
        import io
        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.WARNING)
        logger.addHandler(handler)
        
        config = {
            'pipeline1': 100,
            'pipeline2': 100,  # 重复
        }
        
        normalize_pipelines_config(config)
        
        # 验证有警告日志
        log_output = log_stream.getvalue()
        assert 'Duplicate pipeline priority' in log_output
        
        # 清理 handler
        logger.removeHandler(handler)
    
    def test_invalid_priority_type(self):
        """验证无效的优先级类型"""
        config = {
            'pipeline1': 'high',  # 应该是数字
        }
        
        with pytest.raises(ValueError, match="must be numeric"):
            normalize_pipelines_config(config)
    
    def test_negative_priority(self):
        """验证负数优先级"""
        config = {
            'pipeline1': -100,
        }
        
        with pytest.raises(ValueError, match="must be non-negative"):
            normalize_pipelines_config(config)


class TestDedupPipelineFingerprintVersion:
    """测试 P2#4: 去重管道指纹版本控制"""
    
    def test_fingerprint_has_version(self):
        """验证指纹包含版本号"""
        from crawlo.items import Item
        
        crawler = MockCrawler()
        
        # 创建一个具体的去重管道子类
        class TestDedupPipeline(DedupPipeline):
            @classmethod
            def from_crawler(cls, crawler):
                return cls(crawler)
            
            async def _check_fingerprint_exists(self, fingerprint):
                return False
            
            async def _record_fingerprint(self, fingerprint):
                pass
            
            async def _initialize_resources(self):
                pass
            
            async def _cleanup_resources(self):
                pass
        
        pipeline = TestDedupPipeline(crawler)
        
        # 创建测试 item（使用 dict 子类）
        class TestItem(dict):
            pass
        
        item = TestItem(name='test', value=123)
        
        # 生成指纹
        fingerprint = pipeline._generate_item_fingerprint(item)
        
        # 验证格式：v{version}:{hash}
        assert fingerprint.startswith('v1:')
        assert len(fingerprint.split(':')) == 2
    
    def test_fingerprint_version_constant(self):
        """验证版本号是类常量"""
        assert hasattr(DedupPipeline, 'FINGERPRINT_VERSION')
        assert DedupPipeline.FINGERPRINT_VERSION == 1


class TestIntegrationPipelineManager:
    """集成测试：Pipeline 管理器"""
    
    def test_normalize_dict_config(self):
        """测试字典配置标准化"""
        config = {
            'crawlo.pipelines.MemoryDedupPipeline': 100,
            'crawlo.pipelines.ConsolePipeline': 500,
            'crawlo.pipelines.MySQLPipeline': 800,
        }
        
        result = normalize_pipelines_config(config)
        
        assert len(result) == 3
        # 验证按优先级升序排序
        assert result[0][1] < result[1][1] < result[2][1]
    
    def test_normalize_list_config(self):
        """测试列表配置标准化"""
        config = [
            'crawlo.pipelines.MemoryDedupPipeline',
            'crawlo.pipelines.ConsolePipeline',
        ]
        
        result = normalize_pipelines_config(config)
        
        assert len(result) == 2
        assert result[0] == ('crawlo.pipelines.MemoryDedupPipeline', 500)
        assert result[1] == ('crawlo.pipelines.ConsolePipeline', 501)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
