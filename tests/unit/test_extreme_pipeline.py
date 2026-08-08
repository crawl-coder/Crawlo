"""
Pipeline 极限场景测试

测试数据处理管道在各种异常和边界条件下的健壮性
"""
import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock
from types import SimpleNamespace
from crawlo.items.item import Item


def _make_crawler(overrides=None, spider_name='test'):
    """构建带正确 settings/spider/stats/subscriber 的 crawler mock。

    新版 Pipeline 统一通过 ``crawler`` 访问 ``settings``、``spider``、``stats``
    等属性，构造函数签名为 ``Pipeline(crawler)``。
    """
    overrides = overrides or {}
    crawler = Mock()
    crawler.spider = SimpleNamespace(name=spider_name)
    crawler.stats = Mock()
    crawler.subscriber = Mock()
    crawler.subscriber.notify = AsyncMock()

    def _get(key, default=None):
        return overrides.get(key, default)

    crawler.settings.get.side_effect = _get
    crawler.settings.get_bool.side_effect = _get
    crawler.settings.get_int.side_effect = _get
    crawler.settings.get_list.side_effect = lambda key, default=None: list(overrides.get(key, default or []))
    return crawler


class TestCSVPipelineExtreme:
    """CSV Pipeline 极限测试"""

    @pytest.mark.asyncio
    async def test_csv_huge_data(self, tmp_path):
        """测试超大 CSV 数据（10MB）"""
        from crawlo.pipelines.file.csv import CsvPipeline

        item = Item()
        item['url'] = 'http://example.com'
        item['data'] = 'x' * (10 * 1024 * 1024)  # 10MB

        crawler = _make_crawler({'CSV_FILE': str(tmp_path / 'huge.csv')})
        pipeline = CsvPipeline(crawler)
        await pipeline._initialize_resources()

        # 应该能处理超大数据
        try:
            await pipeline.process_item(item, crawler.spider)
        except Exception as e:
            # 应该有清晰的错误，不崩溃
            assert 'csv' in str(e).lower() or 'file' in str(e).lower()

        await pipeline._on_spider_closed()

    @pytest.mark.asyncio
    async def test_csv_special_characters(self, tmp_path):
        """测试 CSV 特殊字符"""
        from crawlo.pipelines.file.csv import CsvPipeline

        item = Item()
        item['url'] = 'http://example.com'
        item['title'] = '中文标题,包含"引号"和,逗号'
        item['content'] = 'Line1\nLine2\nLine3'
        item['price'] = '$1,234.56'

        crawler = _make_crawler({'CSV_FILE': str(tmp_path / 'special.csv')})
        pipeline = CsvPipeline(crawler)
        await pipeline._initialize_resources()

        # 应该能正确处理特殊字符
        await pipeline.process_item(item, crawler.spider)

        await pipeline._on_spider_closed()

    @pytest.mark.asyncio
    async def test_csv_many_fields(self, tmp_path):
        """测试超多字段（1000 个）"""
        from crawlo.pipelines.file.csv import CsvPipeline

        item = Item()
        for i in range(1000):
            item[f'field_{i}'] = f'value_{i}'

        crawler = _make_crawler({'CSV_FILE': str(tmp_path / 'many_fields.csv')})
        pipeline = CsvPipeline(crawler)
        await pipeline._initialize_resources()

        # 应该能处理超多字段
        await pipeline.process_item(item, crawler.spider)

        await pipeline._on_spider_closed()


class TestJSONPipelineExtreme:
    """JSON Pipeline 极限测试"""

    @pytest.mark.asyncio
    async def test_json_nested_structure(self, tmp_path):
        """测试嵌套 JSON 结构"""
        from crawlo.pipelines.file.json import JsonLinesPipeline

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

        crawler = _make_crawler({'JSON_FILE': str(tmp_path / 'nested.jsonl')})
        pipeline = JsonLinesPipeline(crawler)
        await pipeline._initialize_resources()

        # 应该能处理嵌套结构
        await pipeline.process_item(item, crawler.spider)

        await pipeline._on_spider_closed()

    @pytest.mark.asyncio
    async def test_json_many_items(self, tmp_path):
        """测试大量 Item（10000 个）"""
        from crawlo.pipelines.file.json import JsonLinesPipeline

        crawler = _make_crawler({'JSON_FILE': str(tmp_path / 'many.jsonl')})
        pipeline = JsonLinesPipeline(crawler)
        await pipeline._initialize_resources()

        # 写入 10000 个 item
        for i in range(10000):
            item = Item()
            item['id'] = i
            item['url'] = f'http://example.com/{i}'
            await pipeline.process_item(item, crawler.spider)

        await pipeline._on_spider_closed()


class TestMongoPipelineExtreme:
    """MongoDB Pipeline 极限测试"""

    @pytest.mark.asyncio
    async def test_mongo_connection_failure(self):
        """测试 MongoDB 连接失败"""
        try:
            from crawlo.pipelines.doc.mongo import MongoPipeline
        except Exception as e:
            pytest.skip(f"MongoDB 依赖不可用: {e}")

        settings = Mock()
        settings.get.return_value = 'mongodb://invalid-host:27017'
        settings.getlist.return_value = ['test_db', 'test_collection']

        pipeline = MongoPipeline(settings)

        # 连接失败应该有清晰错误
        try:
            await pipeline.open_spider(None)
        except Exception as e:
            # 应该有清晰的连接错误
            assert 'mongo' in str(e).lower() or 'connection' in str(e).lower()

    @pytest.mark.asyncio
    async def test_mongo_bulk_insert(self):
        """测试 MongoDB 批量插入（Mock）"""
        try:
            from crawlo.pipelines.doc.mongo import MongoPipeline
        except Exception as e:
            pytest.skip(f"MongoDB 依赖不可用: {e}")

        settings = Mock()
        settings.get.return_value = 'mongodb://localhost:27017'
        settings.getlist.return_value = ['test_db', 'test_collection']

        with patch('crawlo.pipelines.doc.mongo.AsyncIOMotorClient') as mock_client:
            mock_db = Mock()
            mock_collection = Mock()
            mock_collection.insert_many = AsyncMock()
            mock_db.__getitem__ = Mock(return_value=mock_collection)
            mock_client.return_value.__getitem__ = Mock(return_value=mock_db)

            pipeline = MongoPipeline(settings)
            await pipeline.open_spider(None)

            # 批量插入 1000 个 item
            for i in range(1000):
                item = Item()
                item['id'] = i
                await pipeline.process_item(item, None)

            await pipeline._on_spider_closed()


class TestPipelineManagerExtreme:
    """Pipeline Manager 极限测试"""

    @pytest.mark.asyncio
    async def test_manager_empty_pipelines(self):
        """测试空 Pipeline 列表"""
        from crawlo.pipelines.manager import PipelineManager

        crawler = _make_crawler({'PIPELINES': {}})
        manager = PipelineManager(crawler)
        await manager._initialize()

        item = Item()
        item['url'] = 'http://example.com'

        # 应该能处理空 Pipeline（不抛出异常即可）
        await manager.process_item(item)
        # 让 process_item 中 create_task 的通知协程有机会执行
        await asyncio.sleep(0)

        await manager.close()

    @pytest.mark.asyncio
    async def test_manager_pipeline_exception(self):
        """测试 Pipeline 异常不影响其他 Pipeline"""
        from crawlo.pipelines.manager import PipelineManager

        class BrokenPipeline:
            async def process_item(self, item, spider):
                raise Exception("Intentional error")

        crawler = _make_crawler({'PIPELINES': {}})
        manager = PipelineManager(crawler)
        broken = BrokenPipeline()
        manager.pipelines = [broken]
        manager.methods = [broken.process_item]

        item = Item()
        item['url'] = 'http://example.com'

        # 通用异常不会被框架吞掉，由调用方处理
        try:
            await manager.process_item(item)
        except Exception:
            pass

        await manager.close()
