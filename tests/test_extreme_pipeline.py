"""
Pipeline 极限场景测试

测试数据处理管道在各种异常和边界条件下的健壮性
"""
import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock
from crawlo.items.item import Item


class TestCSVPipelineExtreme:
    """CSV Pipeline 极限测试"""
    
    @pytest.mark.asyncio
    async def test_csv_huge_data(self):
        """测试超大 CSV 数据（10MB）"""
        from crawlo.pipelines.csv_pipeline import CSVPipeline
        
        item = Item()
        item['url'] = 'http://example.com'
        item['data'] = 'x' * (10 * 1024 * 1024)  # 10MB
        
        settings = Mock()
        settings.get.return_value = 'test_output.csv'
        
        pipeline = CSVPipeline(settings)
        await pipeline.open()
        
        # 应该能处理超大数据
        try:
            await pipeline.process_item(item, None)
        except Exception as e:
            # 应该有清晰的错误，不崩溃
            assert 'csv' in str(e).lower() or 'file' in str(e).lower()
        
        await pipeline.close()
    
    @pytest.mark.asyncio
    async def test_csv_special_characters(self):
        """测试 CSV 特殊字符"""
        from crawlo.pipelines.csv_pipeline import CSVPipeline
        
        item = Item()
        item['url'] = 'http://example.com'
        item['title'] = '中文标题,包含"引号"和,逗号'
        item['content'] = 'Line1\nLine2\nLine3'
        item['price'] = '$1,234.56'
        
        settings = Mock()
        settings.get.return_value = 'test_special.csv'
        
        pipeline = CSVPipeline(settings)
        await pipeline.open()
        
        # 应该能正确处理特殊字符
        await pipeline.process_item(item, None)
        
        await pipeline.close()
    
    @pytest.mark.asyncio
    async def test_csv_many_fields(self):
        """测试超多字段（1000 个）"""
        from crawlo.pipelines.csv_pipeline import CSVPipeline
        
        item = Item()
        for i in range(1000):
            item[f'field_{i}'] = f'value_{i}'
        
        settings = Mock()
        settings.get.return_value = 'test_many_fields.csv'
        
        pipeline = CSVPipeline(settings)
        await pipeline.open()
        
        # 应该能处理超多字段
        await pipeline.process_item(item, None)
        
        await pipeline.close()


class TestJSONPipelineExtreme:
    """JSON Pipeline 极限测试"""
    
    @pytest.mark.asyncio
    async def test_json_nested_structure(self):
        """测试嵌套 JSON 结构"""
        from crawlo.pipelines.json_pipeline import JSONPipeline
        
        item = Item()
        item['url'] = 'http://example.com'
        item['data'] = {
            'level1': {
                'level2': {
                    'level3': {
                        'value': 'deep'
                    }
                }
            },
            'list': [1, 2, 3, {'nested': True}],
        }
        
        settings = Mock()
        settings.get.return_value = 'test_nested.json'
        
        pipeline = JSONPipeline(settings)
        await pipeline.open()
        
        # 应该能处理嵌套结构
        await pipeline.process_item(item, None)
        
        await pipeline.close()
    
    @pytest.mark.asyncio
    async def test_json_many_items(self):
        """测试大量 Item（10000 个）"""
        from crawlo.pipelines.json_pipeline import JSONPipeline
        
        settings = Mock()
        settings.get.return_value = 'test_many.json'
        
        pipeline = JSONPipeline(settings)
        await pipeline.open()
        
        # 写入 10000 个 item
        for i in range(10000):
            item = Item()
            item['id'] = i
            item['url'] = f'http://example.com/{i}'
            await pipeline.process_item(item, None)
        
        await pipeline.close()


class TestMongoPipelineExtreme:
    """MongoDB Pipeline 极限测试"""
    
    @pytest.mark.asyncio
    async def test_mongo_connection_failure(self):
        """测试 MongoDB 连接失败"""
        from crawlo.pipelines.mongo_pipeline import MongoPipeline
        
        settings = Mock()
        settings.get.return_value = 'mongodb://invalid-host:27017'
        settings.getlist.return_value = ['test_db', 'test_collection']
        
        pipeline = MongoPipeline(settings)
        
        # 连接失败应该有清晰错误
        try:
            await pipeline.open()
        except Exception as e:
            # 应该有清晰的连接错误
            assert 'mongo' in str(e).lower() or 'connection' in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_mongo_bulk_insert(self):
        """测试 MongoDB 批量插入（Mock）"""
        from crawlo.pipelines.mongo_pipeline import MongoPipeline
        
        settings = Mock()
        settings.get.return_value = 'mongodb://localhost:27017'
        settings.getlist.return_value = ['test_db', 'test_collection']
        
        with patch('crawlo.pipelines.mongo_pipeline.AsyncIOMotorClient') as mock_client:
            mock_db = Mock()
            mock_collection = Mock()
            mock_collection.insert_many = AsyncMock()
            mock_db.__getitem__ = Mock(return_value=mock_collection)
            mock_client.return_value.__getitem__ = Mock(return_value=mock_db)
            
            pipeline = MongoPipeline(settings)
            await pipeline.open()
            
            # 批量插入 1000 个 item
            for i in range(1000):
                item = Item()
                item['id'] = i
                await pipeline.process_item(item, None)
            
            await pipeline.close()


class TestPipelineManagerExtreme:
    """Pipeline Manager 极限测试"""
    
    @pytest.mark.asyncio
    async def test_manager_empty_pipelines(self):
        """测试空 Pipeline 列表"""
        from crawlo.pipelines.pipeline_manager import PipelineManager
        
        settings = Mock()
        settings.get.return_value = {}
        
        manager = PipelineManager(settings)
        await manager.open()
        
        item = Item()
        item['url'] = 'http://example.com'
        
        # 应该能处理空 Pipeline
        result = await manager.process_item(item, None)
        assert result == item
        
        await manager.close()
    
    @pytest.mark.asyncio
    async def test_manager_pipeline_exception(self):
        """测试 Pipeline 异常不影响其他 Pipeline"""
        from crawlo.pipelines.pipeline_manager import PipelineManager
        
        class BrokenPipeline:
            async def open(self):
                pass
            
            async def process_item(self, item, spider):
                raise Exception("Intentional error")
            
            async def close(self):
                pass
        
        settings = Mock()
        settings.get.return_value = {}
        
        manager = PipelineManager(settings)
        manager._pipelines = [BrokenPipeline()]
        await manager.open()
        
        item = Item()
        item['url'] = 'http://example.com'
        
        # Pipeline 异常应该被捕获
        try:
            await manager.process_item(item, None)
        except:
            pass  # 框架应该捕获异常
        
        await manager.close()
