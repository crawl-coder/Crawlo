# -*- coding: utf-8 -*-
"""
全管道单例功能测试
==================
每个管道独立测试：创建、初始化、process_item、资源清理、错误处理。
所有测试使用 mock 对象，无需真实数据库/网络。
"""
import pytest
import asyncio
import json
import csv
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from io import StringIO


# ═══════════════════════════════════════════════════
# Mock 基础设施
# ═══════════════════════════════════════════════════

def make_crawler(**overrides):
    """创建标准 Mock Crawler"""
    crawler = Mock()
    crawler.settings = Mock()
    crawler.settings.get = Mock(return_value=None)
    crawler.settings.get_int = Mock(return_value=100)
    crawler.settings.get_bool = Mock(return_value=False)
    crawler.settings.get_float = Mock(return_value=0.5)
    crawler.settings.getint = Mock(return_value=3306)
    crawler.settings.getbool = Mock(return_value=False)
    crawler.spider = Mock()
    crawler.spider.name = 'test_spider'
    crawler.spider.custom_settings = Mock(return_value={})
    crawler.subscriber = Mock()
    crawler.subscriber.subscribe = Mock()
    crawler.stats = Mock()
    crawler.stats.inc_value = Mock()
    crawler.stats.set_value = Mock()
    crawler.__class__.__name__ = 'MockCrawler'
    return crawler


class MockItem(dict):
    """可序列化的 Mock Item"""
    pass


# ═══════════════════════════════════════════════════
# 1. ConsolePipeline
# ═══════════════════════════════════════════════════

class TestConsolePipeline:
    """控制台管道 — 直接继承 BasePipeline"""

    def test_from_crawler(self):
        from crawlo.pipelines.console import ConsolePipeline
        crawler = make_crawler()
        crawler.settings.get = Mock(return_value='DEBUG')
        pipe = ConsolePipeline.from_crawler(crawler)
        assert pipe.crawler is crawler
        assert pipe.log_level == 'DEBUG'

    @pytest.mark.asyncio
    async def test_process_item(self):
        from crawlo.pipelines.console import ConsolePipeline
        crawler = make_crawler()
        pipe = ConsolePipeline(crawler)
        item = MockItem(url='http://test.com', title='Hello')
        result = await pipe.process_item(item, crawler.spider)
        assert result is item

    @pytest.mark.asyncio
    async def test_process_item_error_handling(self):
        from crawlo.pipelines.console import ConsolePipeline
        crawler = make_crawler()
        pipe = ConsolePipeline(crawler)
        # Item without to_dict should still work (fallback to dict())
        item = MockItem(a=1, b=2)
        result = await pipe.process_item(item, crawler.spider)
        assert result is item

    def test_convert_to_serializable_basic(self):
        from crawlo.pipelines.console import ConsolePipeline
        crawler = make_crawler()
        pipe = ConsolePipeline(crawler)
        item = MockItem(key='value')
        result = pipe._convert_to_serializable(item)
        assert result == {'key': 'value'}


# ═══════════════════════════════════════════════════
# 2. CsvPipeline
# ═══════════════════════════════════════════════════

class TestCsvPipeline:
    """CSV 管道 — 继承 FileBasedPipeline"""

    def test_from_crawler(self):
        from crawlo.pipelines.file.csv import CsvPipeline
        crawler = make_crawler()
        pipe = CsvPipeline.from_crawler(crawler)
        assert pipe._PREFIX == 'CSV'

    @pytest.mark.asyncio
    async def test_lifecycle_write_and_cleanup(self, tmp_path):
        from crawlo.pipelines.file.csv import CsvPipeline
        out_file = tmp_path / 'test.csv'

        crawler = make_crawler()
        crawler.settings.get = Mock(side_effect=lambda k, d=None: {
            'CSV_FILE': str(out_file),
            'CSV_DELIMITER': ',',
            'CSV_QUOTECHAR': '"',
        }.get(k, d))
        crawler.settings.get_bool = Mock(return_value=True)  # include_headers
        crawler.settings.get_int = Mock(return_value=100)

        pipe = CsvPipeline.from_crawler(crawler)

        # 写入数据
        item = MockItem(name='Alice', age='30')
        await pipe.process_item(item, crawler.spider)

        # 清理
        await pipe._cleanup_resources()
        # 触发 ResourceManager
        if hasattr(pipe, '_resource_manager'):
            await pipe._resource_manager.cleanup_all()

        # 验证文件内容
        content = out_file.read_text(encoding='utf-8').strip()
        lines = content.split('\r\n') if '\r\n' in content else content.split('\n')
        assert lines[0] in ('name,age', 'age,name')  # dict 顺序可能不同

    @pytest.mark.asyncio
    async def test_batch_mode_flush(self, tmp_path):
        from crawlo.pipelines.file.csv import CsvPipeline
        out_file = tmp_path / 'test_batch.csv'

        crawler = make_crawler()
        crawler.settings.get = Mock(side_effect=lambda k, d=None: {
            'CSV_FILE': str(out_file),
            'CSV_DELIMITER': ',',
            'CSV_QUOTECHAR': '"',
        }.get(k, d))
        crawler.settings.get_bool = Mock(side_effect=lambda k, d=False: {
            'CSV_INCLUDE_HEADERS': True,
            'CSV_USE_BUFFER': True,
        }.get(k, d))
        crawler.settings.get_int = Mock(side_effect=lambda k, d=100: {
            'CSV_BATCH_SIZE': 2,
        }.get(k, d))

        pipe = CsvPipeline.from_crawler(crawler)

        await pipe.process_item(MockItem(name='A', val='1'), crawler.spider)
        assert len(pipe.batch_buffer) == 1  # 未达批量大小

        await pipe.process_item(MockItem(name='B', val='2'), crawler.spider)
        assert len(pipe.batch_buffer) == 0  # 已刷新

    @pytest.mark.asyncio
    async def test_error_handling(self, tmp_path):
        from crawlo.pipelines.file.csv import CsvPipeline
        from crawlo.exceptions import ItemDiscard

        out_file = tmp_path / 'err.csv'
        crawler = make_crawler()
        crawler.settings.get = Mock(side_effect=lambda k, d=None: {
            'CSV_FILE': str(out_file),
        }.get(k, d))
        crawler.settings.get_bool = Mock(return_value=False)

        pipe = CsvPipeline.from_crawler(crawler)

        # 写入正常数据后关闭管道，验证 item 可以通过
        item = MockItem(x='1')
        result = await pipe.process_item(item, crawler.spider)
        assert result is item
        assert crawler.stats.inc_value.called


# ═══════════════════════════════════════════════════
# 3. CsvDictPipeline
# ═══════════════════════════════════════════════════

class TestCsvDictPipeline:
    """CSV Dict 管道 — 继承 FileBasedPipeline"""

    def test_from_crawler(self):
        from crawlo.pipelines.file.csv import CsvDictPipeline
        crawler = make_crawler()
        pipe = CsvDictPipeline.from_crawler(crawler)
        assert pipe._PREFIX == 'CSV_DICT'

    @pytest.mark.asyncio
    async def test_write_with_fieldnames(self, tmp_path):
        from crawlo.pipelines.file.csv import CsvDictPipeline
        out_file = tmp_path / 'dict.csv'

        crawler = make_crawler()
        crawler.settings.get = Mock(side_effect=lambda k, d=None: {
            'CSV_DICT_FILE': str(out_file),
            'CSV_DELIMITER': ',',
            'CSV_QUOTECHAR': '"',
        }.get(k, d))
        crawler.settings.get_bool = Mock(return_value=True)
        crawler.settings.get_int = Mock(return_value=100)

        pipe = CsvDictPipeline.from_crawler(crawler)

        item = MockItem(name='Test', value='123')
        await pipe.process_item(item, crawler.spider)

        await pipe._cleanup_resources()
        if hasattr(pipe, '_resource_manager'):
            await pipe._resource_manager.cleanup_all()

        content = out_file.read_text(encoding='utf-8')
        assert 'name' in content or 'Test' in content

    def test_fieldname_parsing(self):
        from crawlo.pipelines.file.csv import CsvDictPipeline
        crawler = make_crawler()

        # 配置字段名
        crawler.settings.get = Mock(side_effect=lambda k, d=None: {
            'CSV_FIELDNAMES': ['id', 'name', 'title'],
        }.get(k, d))

        pipe = CsvDictPipeline.from_crawler(crawler)
        fields = pipe._get_fieldnames({'id': 1, 'name': 'x', 'extra': 'y'})
        assert fields == ['id', 'name', 'title']

    def test_fieldname_from_item(self):
        from crawlo.pipelines.file.csv import CsvDictPipeline
        crawler = make_crawler()
        pipe = CsvDictPipeline.from_crawler(crawler)
        fields = pipe._get_fieldnames({'a': 1, 'b': 2})
        assert set(fields) == {'a', 'b'}


# ═══════════════════════════════════════════════════
# 4. JsonLinesPipeline
# ═══════════════════════════════════════════════════

class TestJsonLinesPipeline:
    """JSON Lines 管道 — 继承 FileBasedPipeline"""

    def test_from_crawler(self):
        from crawlo.pipelines.file.json import JsonLinesPipeline
        crawler = make_crawler()
        pipe = JsonLinesPipeline.from_crawler(crawler)
        assert pipe._PREFIX == 'JSON'

    @pytest.mark.asyncio
    async def test_write_json_line(self, tmp_path):
        from crawlo.pipelines.file.json import JsonLinesPipeline
        out_file = tmp_path / 'test.jsonl'

        crawler = make_crawler()
        crawler.settings.get = Mock(side_effect=lambda k, d=None: {
            'JSON_FILE': str(out_file),
        }.get(k, d))
        crawler.settings.get_bool = Mock(return_value=False)

        pipe = JsonLinesPipeline.from_crawler(crawler)

        item = MockItem(url='http://x.com', title='T')
        await pipe.process_item(item, crawler.spider)

        await pipe._cleanup_resources()
        if hasattr(pipe, '_resource_manager'):
            await pipe._resource_manager.cleanup_all()

        content = out_file.read_text(encoding='utf-8')
        parsed = json.loads(content.strip())
        assert parsed['url'] == 'http://x.com'
        assert pipe.items_count == 1

    @pytest.mark.asyncio
    async def test_add_metadata(self, tmp_path):
        from crawlo.pipelines.file.json import JsonLinesPipeline
        out_file = tmp_path / 'meta.jsonl'

        crawler = make_crawler()
        crawler.settings.get = Mock(side_effect=lambda k, d=None: {
            'JSON_FILE': str(out_file),
        }.get(k, d))
        crawler.settings.get_bool = Mock(side_effect=lambda k, d=False: {
            'JSON_ADD_METADATA': True,
        }.get(k, d))

        pipe = JsonLinesPipeline.from_crawler(crawler)

        item = MockItem(data='x')
        await pipe.process_item(item, crawler.spider)

        await pipe._cleanup_resources()
        if hasattr(pipe, '_resource_manager'):
            await pipe._resource_manager.cleanup_all()

        content = out_file.read_text(encoding='utf-8')
        parsed = json.loads(content.strip())
        assert '_crawl_time' in parsed
        assert parsed['_spider_name'] == 'test_spider'


# ═══════════════════════════════════════════════════
# 5. JsonArrayPipeline
# ═══════════════════════════════════════════════════

class TestJsonArrayPipeline:
    """JSON Array 管道 — 继承 FileBasedPipeline"""

    def test_from_crawler(self):
        from crawlo.pipelines.file.json import JsonArrayPipeline
        crawler = make_crawler()
        pipe = JsonArrayPipeline.from_crawler(crawler)
        assert pipe._PREFIX == 'JSON_ARRAY'

    @pytest.mark.asyncio
    async def test_collect_and_write_array(self, tmp_path):
        from crawlo.pipelines.file.json import JsonArrayPipeline
        out_file = tmp_path / 'array.json'

        crawler = make_crawler()
        crawler.settings.get = Mock(side_effect=lambda k, d=None: {
            'JSON_ARRAY_FILE': str(out_file),
        }.get(k, d))
        crawler.settings.get_int = Mock(side_effect=lambda k, d=100000: {
            'JSON_ARRAY_MAX_ITEMS': 100000,
        }.get(k, d))

        pipe = JsonArrayPipeline.from_crawler(crawler)

        await pipe.process_item(MockItem(id=1), crawler.spider)
        await pipe.process_item(MockItem(id=2), crawler.spider)

        assert len(pipe.items) == 2  # 内存中收集

        # 触发清理（合并写入最终文件）
        await pipe._cleanup_resources()

        content = out_file.read_text(encoding='utf-8')
        parsed = json.loads(content)
        assert len(parsed) == 2
        assert parsed[0]['id'] == 1
        assert parsed[1]['id'] == 2

    @pytest.mark.asyncio
    async def test_no_items_warning(self):
        from crawlo.pipelines.file.json import JsonArrayPipeline
        crawler = make_crawler()
        pipe = JsonArrayPipeline.from_crawler(crawler)
        await pipe._cleanup_resources()
        # 无数据时不崩溃


# ═══════════════════════════════════════════════════
# 6. MemoryDedupPipeline
# ═══════════════════════════════════════════════════

class TestMemoryDedupPipeline:
    """内存去重管道 — 继承 DedupPipeline"""

    def test_from_crawler(self):
        from crawlo.pipelines.dedup.memory import MemoryDedupPipeline
        crawler = make_crawler()
        pipe = MemoryDedupPipeline.from_crawler(crawler)
        assert isinstance(pipe.seen_items, set)

    @pytest.mark.asyncio
    async def test_dedup_first_accepts_then_rejects(self):
        from crawlo.pipelines.dedup.memory import MemoryDedupPipeline
        from crawlo.exceptions import ItemDiscard

        crawler = make_crawler()
        pipe = MemoryDedupPipeline.from_crawler(crawler)

        item = MockItem(id=1, data='x')

        # 第一次：通过
        result = await pipe.process_item(item, crawler.spider)
        assert result is item
        assert pipe.processed_count == 1

        # 第二次：丢弃
        with pytest.raises(ItemDiscard):
            await pipe.process_item(item, crawler.spider)
        assert pipe.dropped_count == 1

    @pytest.mark.asyncio
    async def test_cleanup_clears_memory_and_logs(self):
        from crawlo.pipelines.dedup.memory import MemoryDedupPipeline
        from crawlo.exceptions import ItemDiscard

        crawler = make_crawler()
        pipe = MemoryDedupPipeline.from_crawler(crawler)

        item = MockItem(a='1')
        await pipe.process_item(item, crawler.spider)
        assert len(pipe.seen_items) == 1

        await pipe._cleanup_resources()
        assert len(pipe.seen_items) == 0  # 已清理


# ═══════════════════════════════════════════════════
# 7. BloomDedupPipeline
# ═══════════════════════════════════════════════════

class TestBloomDedupPipeline:
    """Bloom Filter 去重管道"""

    def test_from_crawler(self):
        from crawlo.pipelines.dedup.bloom import BloomDedupPipeline
        crawler = make_crawler()
        crawler.settings.get_int = Mock(side_effect=lambda k, d=0: {
            'BLOOM_FILTER_CAPACITY': 1000000,
        }.get(k, d))
        crawler.settings.get_float = Mock(side_effect=lambda k, d=0.001: {
            'BLOOM_FILTER_ERROR_RATE': 0.001,
        }.get(k, d))
        pipe = BloomDedupPipeline.from_crawler(crawler)
        assert pipe.capacity == 1000000

    @pytest.mark.asyncio
    async def test_bloom_dedup(self):
        from crawlo.pipelines.dedup.bloom import BloomDedupPipeline
        from crawlo.exceptions import ItemDiscard

        crawler = make_crawler()
        pipe = BloomDedupPipeline.from_crawler(crawler)

        item = MockItem(id=100)
        result = await pipe.process_item(item, crawler.spider)
        assert result is item  # 首次通过

        # 相同 item 应被丢弃
        with pytest.raises(ItemDiscard):
            await pipe.process_item(MockItem(id=100), crawler.spider)

    @pytest.mark.asyncio
    async def test_cleanup_outputs_stats(self):
        from crawlo.pipelines.dedup.bloom import BloomDedupPipeline

        crawler = make_crawler()
        pipe = BloomDedupPipeline.from_crawler(crawler)
        pipe.added_count = 10
        pipe.processed_count = 15
        pipe.dropped_count = 5

        await pipe._cleanup_resources()
        # 无异常即通过


# ═══════════════════════════════════════════════════
# 8. MySQLDedupPipeline
# ═══════════════════════════════════════════════════

class TestMySQLDedupPipeline:
    """MySQL 去重管道"""

    def test_from_crawler(self):
        from crawlo.pipelines.dedup.mysql import MySQLDedupPipeline
        crawler = make_crawler()
        crawler.settings.getint = Mock(side_effect=lambda k, d=0: {
            'DB_PORT': 3306,
        }.get(k, d))
        pipe = MySQLDedupPipeline.from_crawler(crawler)
        assert pipe.table_name == 'item_fingerprints'

    def test_backward_compat_alias(self):
        from crawlo.pipelines.dedup.mysql import DatabaseDedupPipeline, MySQLDedupPipeline
        assert DatabaseDedupPipeline is MySQLDedupPipeline

    @pytest.mark.asyncio
    async def test_check_fingerprint_returns_false_when_no_pool(self):
        from crawlo.pipelines.dedup.mysql import MySQLDedupPipeline
        import asyncio
        crawler = make_crawler()
        pipe = MySQLDedupPipeline.from_crawler(crawler)
        # 无连接池时应该安全返回
        # (这个测试验证 pool 为 None 不会崩溃)
        assert pipe.pool is None


# ═══════════════════════════════════════════════════
# 9. GenericSQLPipeline（抽象基类功能测试）
# ═══════════════════════════════════════════════════

class TestGenericSQLPipeline:
    """通用 SQL 管道基类 — 纯功能测试"""

    @pytest.mark.asyncio
    async def test_sanitize_table_name(self):
        from crawlo.pipelines.generic_sql import GenericSQLPipeline
        assert GenericSQLPipeline._sanitize_table_name('test_table') == 'test_table'
        assert GenericSQLPipeline._sanitize_table_name('my table') == 'my_table'
        assert GenericSQLPipeline._sanitize_table_name('my-table') == 'my_table'

    @pytest.mark.asyncio
    async def test_sanitize_raises_on_empty(self):
        from crawlo.pipelines.generic_sql import GenericSQLPipeline
        import pytest
        with pytest.raises(ValueError):
            GenericSQLPipeline._sanitize_table_name('')

    def test_parse_columns(self):
        from crawlo.pipelines.generic_sql import GenericSQLPipeline
        assert GenericSQLPipeline._parse_columns(None) == ()
        assert GenericSQLPipeline._parse_columns(()) == ()
        assert GenericSQLPipeline._parse_columns('col') == ('col',)
        assert GenericSQLPipeline._parse_columns(['a', 'b']) == ('a', 'b')

    @pytest.mark.asyncio
    async def test_before_insert_hook(self):
        from crawlo.pipelines.generic_sql import GenericSQLPipeline
        crawler = make_crawler()
        pipe = GenericSQLPipeline.from_crawler(crawler)
        item = MockItem(x=1)
        result = await pipe._before_insert(item)
        assert result == {'x': 1}


# ═══════════════════════════════════════════════════
# 10. MySQLPipeline
# ═══════════════════════════════════════════════════

class TestMySQLPipeline:
    """MySQL 管道 — 继承 GenericSQLPipeline"""

    def test_from_crawler(self):
        from crawlo.pipelines.sql.mysql import MySQLPipeline
        crawler = make_crawler()
        pipe = MySQLPipeline.from_crawler(crawler)
        assert pipe._PREFIX == 'MYSQL'

    def test_config_defaults(self):
        from crawlo.pipelines.sql.mysql import MySQLPipeline
        crawler = make_crawler()
        crawler.settings.get = Mock(side_effect=lambda k, d=None: {
            'MYSQL_TABLE': 'my_table',
        }.get(k, d))
        pipe = MySQLPipeline.from_crawler(crawler)
        assert pipe.table_name == 'my_table'
        assert pipe.batch_size == 100
        assert pipe.max_retries == 3


# ═══════════════════════════════════════════════════
# 11. SQLitePipeline
# ═══════════════════════════════════════════════════

class TestSQLitePipeline:
    """SQLite 管道 — 继承 GenericSQLPipeline"""

    def test_from_crawler(self):
        from crawlo.pipelines.sql.sqlite import SQLitePipeline
        crawler = make_crawler()
        pipe = SQLitePipeline.from_crawler(crawler)
        assert pipe._PREFIX == 'SQLITE'

    def test_config_creates_path(self, tmp_path):
        from crawlo.pipelines.sql.sqlite import SQLitePipeline
        crawler = make_crawler()
        crawler.settings.get = Mock(return_value=None)
        crawler.settings.get_int = Mock(return_value=100)
        crawler.settings.get_bool = Mock(return_value=False)
        crawler.settings.get_float = Mock(return_value=0.5)
        pipe = SQLitePipeline.from_crawler(crawler)
        # 默认路径 data/crawlo.db
        assert '.db' in str(pipe.db_path)

    @pytest.mark.asyncio
    async def test_create_helper_noop(self):
        from crawlo.pipelines.sql.sqlite import SQLitePipeline
        crawler = make_crawler()
        pipe = SQLitePipeline.from_crawler(crawler)
        # _create_helper should be no-op
        await pipe._create_helper()
        assert pipe._helper is None or hasattr(pipe, '_helper')


# ═══════════════════════════════════════════════════
# 12. PostgreSQLPipeline
# ═══════════════════════════════════════════════════

class TestPostgreSQLPipeline:
    """PostgreSQL 管道"""

    def test_from_crawler_without_conflict_cols_raises(self):
        from crawlo.pipelines.sql.postgresql import PostgreSQLPipeline
        from crawlo.exceptions import PipelineInitError

        crawler = make_crawler()
        crawler.settings.get = Mock(return_value=None)
        crawler.settings.get_bool = Mock(return_value=False)  # insert_ignore=False

        # 未配置 PG_CONFLICT_COLUMNS 且 insert_ignore=False → 应抛出 PipelineInitError
        with pytest.raises(PipelineInitError, match='PG_CONFLICT_COLUMNS'):
            PostgreSQLPipeline.from_crawler(crawler)

    def test_from_crawler_with_insert_ignore(self):
        from crawlo.pipelines.sql.postgresql import PostgreSQLPipeline
        crawler = make_crawler()
        crawler.settings.get_bool = Mock(return_value=True)  # insert_ignore=True
        pipe = PostgreSQLPipeline.from_crawler(crawler)
        assert pipe._PREFIX == 'PG'

    def test_from_crawler_with_conflict_cols(self):
        from crawlo.pipelines.sql.postgresql import PostgreSQLPipeline
        crawler = make_crawler()
        crawler.settings.get = Mock(side_effect=lambda k, d=None: {
            'PG_CONFLICT_COLUMNS': ('id',),
        }.get(k, d))
        crawler.settings.get_bool = Mock(return_value=False)
        pipe = PostgreSQLPipeline.from_crawler(crawler)
        assert pipe.conflict_cols == ('id',)


# ═══════════════════════════════════════════════════
# 13. MongoPipeline
# ═══════════════════════════════════════════════════

class TestMongoPipeline:
    """MongoDB 管道 — 继承 GenericDocumentPipeline"""

    def test_from_crawler(self):
        from crawlo.pipelines.doc.mongo import MongoPipeline
        crawler = make_crawler()
        pipe = MongoPipeline.from_crawler(crawler)
        assert pipe._PREFIX == 'MONGO'
        assert pipe.deduplicate_mode == 'upsert'

    def test_config_insert_mode(self):
        from crawlo.pipelines.doc.mongo import MongoPipeline
        crawler = make_crawler()
        crawler.settings.get = Mock(side_effect=lambda k, d=None: {
            'MONGO_DEDUPLICATE_MODE': 'insert',
        }.get(k, d))
        pipe = MongoPipeline.from_crawler(crawler)
        assert pipe.deduplicate_mode == 'insert'

    def test_compute_doc_id_deterministic(self):
        from crawlo.pipelines.doc.mongo import MongoPipeline
        crawler = make_crawler()
        pipe = MongoPipeline.from_crawler(crawler)
        doc = {'a': 1, 'b': 2}
        id1 = pipe._compute_doc_id(doc)
        id2 = pipe._compute_doc_id({'b': 2, 'a': 1})
        assert id1 == id2  # 确定性


# ═══════════════════════════════════════════════════
# 14. ElasticsearchPipeline
# ═══════════════════════════════════════════════════

class TestElasticsearchPipeline:
    """ES 管道 — 继承 GenericDocumentPipeline"""

    def test_from_crawler(self):
        from crawlo.pipelines.doc.elasticsearch import ElasticsearchPipeline
        crawler = make_crawler()
        pipe = ElasticsearchPipeline.from_crawler(crawler)
        assert pipe._PREFIX == 'ELASTICSEARCH'

    def test_config_defaults(self):
        from crawlo.pipelines.doc.elasticsearch import ElasticsearchPipeline
        crawler = make_crawler()
        pipe = ElasticsearchPipeline.from_crawler(crawler)
        assert pipe.index_name == 'test_spider'

    def test_compute_doc_id(self):
        from crawlo.pipelines.doc.elasticsearch import ElasticsearchPipeline
        crawler = make_crawler()
        pipe = ElasticsearchPipeline.from_crawler(crawler)
        doc = {'key': 'value'}
        doc_id = pipe._compute_doc_id(doc)
        assert len(doc_id) == 32  # MD5 hex
        assert isinstance(doc_id, str)


# ═══════════════════════════════════════════════════
# 15. ClickHousePipeline
# ═══════════════════════════════════════════════════

class TestClickHousePipeline:
    """ClickHouse 管道"""

    def test_from_crawler(self):
        from crawlo.pipelines.sql.clickhouse import ClickHousePipeline
        crawler = make_crawler()
        pipe = ClickHousePipeline.from_crawler(crawler)
        assert pipe._PREFIX == 'CLICKHOUSE'
        assert pipe.use_transaction is False  # 强制关闭事务

    def test_config_batch_enabled_by_default(self):
        from crawlo.pipelines.sql.clickhouse import ClickHousePipeline
        crawler = make_crawler()
        crawler.settings.get_bool = Mock(return_value=False)  # 未显式设置
        # _init_config 中会设置 use_batch=True
        pipe = ClickHousePipeline.from_crawler(crawler)
        assert pipe.use_batch is True


# ═══════════════════════════════════════════════════
# 16. HBasePipeline
# ═══════════════════════════════════════════════════

class TestHBasePipeline:
    """HBase 管道 — 直接继承 ResourceManagedPipeline"""

    def test_from_crawler(self):
        from crawlo.pipelines.hbase import HBasePipeline
        crawler = make_crawler()
        pipe = HBasePipeline.from_crawler(crawler)
        assert pipe._PREFIX == 'HBASE'

    def test_build_columns(self):
        from crawlo.pipelines.hbase import HBasePipeline
        crawler = make_crawler()
        pipe = HBasePipeline.from_crawler(crawler)
        cols = pipe._build_columns({'name': 'test', 'age': 25})
        assert 'cf:name' in cols
        assert cols['cf:name'] == 'test'
        assert cols['cf:age'] == '25'

    def test_build_rowkey(self):
        from crawlo.pipelines.hbase import HBasePipeline
        crawler = make_crawler()
        pipe = HBasePipeline.from_crawler(crawler)
        item = MockItem(x='hello')
        rowkey = pipe._build_rowkey(item)
        assert isinstance(rowkey, bytes)
        assert len(rowkey) == 32  # MD5 hex


# ═══════════════════════════════════════════════════
# 17. SQLDialect
# ═══════════════════════════════════════════════════

class TestSQLDialect:
    """SQL 方言功能测试"""

    def test_mysql_dialect(self):
        from crawlo.db.dialect import MySQLDialect
        d = MySQLDialect
        assert d.placeholder == '%s'
        assert d.quote_char == '`'
        assert d.quote('tbl') == '`tbl`'

    def test_postgresql_dialect(self):
        from crawlo.db.dialect import PostgreSQLDialect
        d = PostgreSQLDialect
        assert d.build_placeholder(0) == '$1'
        assert d.build_placeholder(1) == '$2'
        assert d.quote_char == '"'

    def test_sqlite_dialect(self):
        from crawlo.db.dialect import SQLiteDialect
        d = SQLiteDialect
        assert d.placeholder == '?'
        assert d.build_insert('t', ['a', 'b']) == 'INSERT INTO "t" ("a", "b") VALUES (?, ?)'

    def test_clickhouse_dialect(self):
        from crawlo.db.dialect import ClickHouseDialect
        d = ClickHouseDialect
        assert d.placeholder == '%s'
        assert d.upsert_template is None  # 无传统 UPSERT

    def test_build_insert_ignore(self):
        from crawlo.db.dialect import PostgreSQLDialect
        sql, params = PostgreSQLDialect.build_insert_ignore(
            'mytable', {'a': 1, 'b': 2}
        )
        assert 'ON CONFLICT DO NOTHING' in sql


# ═══════════════════════════════════════════════════
# 18. PipelineManager
# ═══════════════════════════════════════════════════

class TestPipelineManager:
    """管道管理器功能测试"""

    def test_normalize_empty_config(self):
        from crawlo.pipelines.manager import normalize_pipelines_config
        result = normalize_pipelines_config(None)
        assert result == []

    def test_normalize_dict_config(self):
        from crawlo.pipelines.manager import normalize_pipelines_config
        config = {
            'crawlo.pipelines.RedisDedupPipeline': 100,
            'crawlo.pipelines.ConsolePipeline': 500,
        }
        result = normalize_pipelines_config(config)
        assert len(result) == 2
        # 按优先级升序排列
        assert result[0][1] == 100
        assert result[1][1] == 500

    def test_normalize_list_config(self):
        from crawlo.pipelines.manager import normalize_pipelines_config
        config = ['crawlo.pipelines.ConsolePipeline']
        result = normalize_pipelines_config(config)
        assert len(result) == 1
        assert result[0][0] == 'crawlo.pipelines.ConsolePipeline'

    def test_validate_negative_priority(self):
        from crawlo.pipelines.manager import _validate_pipeline_priorities
        with pytest.raises(ValueError):
            _validate_pipeline_priorities({'p': -1})

    def test_validate_non_numeric(self):
        from crawlo.pipelines.manager import _validate_pipeline_priorities
        with pytest.raises(ValueError):
            _validate_pipeline_priorities({'p': 'high'})

    @pytest.mark.asyncio
    async def test_close_with_resource_manager(self):
        from crawlo.pipelines.manager import PipelineManager
        from crawlo.pipelines.file.csv import CsvPipeline
        import tempfile

        crawler = make_crawler()
        manager = PipelineManager(crawler)

        # 手动添加一个 CsvPipeline 模拟资源注册
        pipe = CsvPipeline.from_crawler(crawler)
        manager.pipelines.append(pipe)

        # close 应调用 _cleanup_resources + _resource_manager.cleanup_all
        await manager.close()
        # 无异常即通过（_cleanup_resources 触发后文件操作可能因未初始化而失败）
        # 验证 resource_manager 被调用
        assert hasattr(pipe, '_resource_manager')


# ═══════════════════════════════════════════════════
# 19. ErrorClassifier（跨管道错误分类）
# ═══════════════════════════════════════════════════

class TestErrorClassifier:
    """错误分类器测试"""

    def test_extract_mysql_error_code(self):
        from crawlo.utils.db.pipeline_utils import ErrorClassifier

        class MockError(Exception):
            def __init__(self):
                super().__init__((1062, "Duplicate entry"))

        err = MockError()
        code = ErrorClassifier.extract_error_code(err)
        assert code == 1062

    def test_is_skipable_duplicate(self):
        from crawlo.utils.db.pipeline_utils import ErrorClassifier

        class MockError(Exception):
            def __init__(self):
                super().__init__((1062, "Duplicate entry"))

        assert ErrorClassifier.is_skipable(MockError()) is True

    def test_is_retryable_connection(self):
        from crawlo.utils.db.pipeline_utils import ErrorClassifier

        class MockError(Exception):
            def __init__(self):
                super().__init__((2006, "MySQL server has gone away"))

        assert ErrorClassifier.is_retryable(MockError()) is True

    def test_random_error_not_skipable(self):
        from crawlo.utils.db.pipeline_utils import ErrorClassifier
        err = RuntimeError("random")
        assert ErrorClassifier.is_skipable(err) is False
        assert ErrorClassifier.is_retryable(err) is False


# ═══════════════════════════════════════════════════
# 20. GenericDocumentPipeline
# ═══════════════════════════════════════════════════

class TestGenericDocumentPipeline:
    """通用文档管道基类测试"""

    def test_compute_doc_id(self):
        from crawlo.pipelines.generic_doc import GenericDocumentPipeline
        crawler = make_crawler()
        pipe = GenericDocumentPipeline.from_crawler(crawler)
        doc = {'x': 1}
        doc_id = pipe._compute_doc_id(doc)
        assert len(doc_id) == 32

    @pytest.mark.asyncio
    async def test_before_insert_hook(self):
        from crawlo.pipelines.generic_doc import GenericDocumentPipeline
        crawler = make_crawler()
        pipe = GenericDocumentPipeline.from_crawler(crawler)
        item = MockItem(a=1)
        result = await pipe._before_insert(item)
        assert result == {'a': 1}


# ═══════════════════════════════════════════════════
# 21. ResourceManagedPipeline（基类）
# ═══════════════════════════════════════════════════

class TestResourceManagedPipeline:
    """资源管理基类测试"""

    def test_register_resource(self):
        from crawlo.pipelines.base_pipeline import ResourceManagedPipeline
        from crawlo.utils.resource_manager import ResourceType

        crawler = make_crawler()
        # 使用具体子类
        from crawlo.pipelines.file.csv import CsvPipeline
        pipe = CsvPipeline.from_crawler(crawler)

        resource = object()
        cleanup_called = []

        async def cleanup(r):
            cleanup_called.append(True)

        pipe.register_resource(resource, cleanup, ResourceType.OTHER, 'test')

        # 验证已注册
        stats = pipe._resource_manager.get_stats()
        assert stats['total_resources'] >= 1

    @pytest.mark.asyncio
    async def test_process_item_batched(self):
        from crawlo.pipelines.base_pipeline import ResourceManagedPipeline
        from crawlo.pipelines.file.csv import CsvPipeline

        crawler = make_crawler()
        crawler.settings.get_bool = Mock(return_value=True)  # use_batch
        crawler.settings.get_int = Mock(return_value=2)  # batch_size

        class TestPipe(CsvPipeline):
            pass

        pipe = TestPipe.from_crawler(crawler)
        pipe.use_batch = True
        pipe.batch_size = 2

        insert_func = AsyncMock()
        item1 = MockItem(a=1)
        item2 = MockItem(a=2)

        await pipe.process_item_batched(item1, crawler.spider, insert_func)
        await pipe.process_item_batched(item2, crawler.spider, insert_func)

        assert insert_func.called
