# -*- coding: utf-8 -*-
"""
Pipeline资源管理改造示例
======================

展示如何将现有Pipeline改造为使用ResourceManager的版本

示例包括：
1. MongoDB Pipeline改造（数据库类）
2. CSV Pipeline改造（文件类）
3. Redis去重Pipeline改造（缓存类）
"""

# ================== 示例1: MongoDB Pipeline改造 ==================

# ❌ 原始版本 - 存在资源泄露风险
class OldMongoPipeline:
    """原始的MongoDB Pipeline"""
    
    def __init__(self, crawler):
        from motor.motor_asyncio import AsyncIOMotorClient
        
        self.crawler = crawler
        self.settings = crawler.settings
        
        # 直接创建客户端，未注册资源管理
        self.client = AsyncIOMotorClient(
            self.settings.get('MONGO_URI', 'mongodb://localhost:27017')
        )
        self.db = self.client[self.settings.get('MONGO_DATABASE', 'crawlo_db')]
        self.collection = self.db[self.settings.get('MONGO_COLLECTION', 'items')]
        
        # ⚠️ 问题：注册事件，但清理逻辑不完善
        crawler.subscriber.subscribe(self.spider_closed, event='spider_closed')
    
    async def process_item(self, item, spider):
        await self.collection.insert_one(dict(item))
        return item
    
    async def spider_closed(self):
        # ⚠️ 问题：只是close，没有wait，可能泄露
        if self.client:
            self.client.close()
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)


# ✅ 改进版本 - 使用ResourceManager
class ImprovedMongoPipeline:
    """改进的MongoDB Pipeline - 完整资源管理"""
    
    def __init__(self, crawler):
        from motor.motor_asyncio import AsyncIOMotorClient
        from crawlo.utils.resource_manager import ResourceManager, ResourceType
        from crawlo.utils.log import get_logger
        
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__, self.settings.get('LOG_LEVEL'))
        
        # ✅ 创建资源管理器
        self._resource_manager = ResourceManager(name="mongo_pipeline")
        
        # MongoDB配置
        self.mongo_uri = self.settings.get('MONGO_URI', 'mongodb://localhost:27017')
        self.db_name = self.settings.get('MONGO_DATABASE', 'crawlo_db')
        self.collection_name = self.settings.get('MONGO_COLLECTION', 'items')
        
        # 延迟初始化
        self.client = None
        self.db = None
        self.collection = None
        self._initialized = False
        
        # 注册关闭事件
        crawler.subscriber.subscribe(self._on_spider_closed, event='spider_closed')
    
    async def _ensure_initialized(self):
        """确保资源已初始化"""
        if self._initialized:
            return
        
        from motor.motor_asyncio import AsyncIOMotorClient
        
        # 创建MongoDB客户端
        self.client = AsyncIOMotorClient(
            self.mongo_uri,
            maxPoolSize=self.settings.get_int('MONGO_MAX_POOL_SIZE', 100),
            minPoolSize=self.settings.get_int('MONGO_MIN_POOL_SIZE', 10)
        )
        
        # ✅ 注册到资源管理器
        self._resource_manager.register(
            resource=self.client,
            cleanup_func=self._close_client,
            resource_type=ResourceType.DATABASE,
            name="mongo_client"
        )
        
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]
        self._initialized = True
        
        self.logger.info(f"MongoDB客户端已初始化: {self.collection_name}")
    
    async def _close_client(self, client):
        """关闭MongoDB客户端"""
        if client:
            try:
                client.close()
                # ✅ 可以添加等待逻辑确保完全关闭
                import asyncio
                await asyncio.sleep(0.1)
                self.logger.info("MongoDB客户端已关闭")
            except Exception as e:
                self.logger.error(f"关闭MongoDB客户端失败: {e}")
    
    async def process_item(self, item, spider):
        await self._ensure_initialized()
        
        try:
            result = await self.collection.insert_one(dict(item))
            self.crawler.stats.inc_value('mongodb/insert_success')
            return item
        except Exception as e:
            self.logger.error(f"MongoDB插入失败: {e}")
            self.crawler.stats.inc_value('mongodb/insert_failed')
            raise
    
    async def _on_spider_closed(self):
        """爬虫关闭时清理资源"""
        self.logger.info("开始清理MongoDB Pipeline资源...")
        
        # ✅ 使用ResourceManager统一清理
        cleanup_result = await self._resource_manager.cleanup_all()
        
        if cleanup_result['success_count'] > 0:
            self.logger.info(
                f"MongoDB资源清理完成: 成功 {cleanup_result['success_count']} 个"
            )
        
        if cleanup_result['errors']:
            self.logger.warning(f"清理时出现错误: {cleanup_result['errors']}")
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)


# ================== 示例2: CSV Pipeline改造 ==================

# ❌ 原始版本 - 存在文件句柄泄露风险
class OldCsvPipeline:
    """原始的CSV Pipeline"""
    
    def __init__(self, crawler):
        import csv
        from pathlib import Path
        
        self.crawler = crawler
        self.settings = crawler.settings
        
        # 文件路径
        self.file_path = Path(f"output/{crawler.spider.name}.csv")
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # ⚠️ 问题：直接打开文件，未注册资源管理
        self.file_handle = open(self.file_path, 'w', newline='', encoding='utf-8')
        self.csv_writer = csv.writer(self.file_handle)
        
        # 批量缓冲区
        self.batch_buffer = []
        self.batch_size = 100
        
        crawler.subscriber.subscribe(self.spider_closed, event='spider_closed')
    
    async def process_item(self, item, spider):
        self.batch_buffer.append(list(dict(item).values()))
        
        if len(self.batch_buffer) >= self.batch_size:
            await self._flush_batch()
        
        return item
    
    async def _flush_batch(self):
        # ⚠️ 问题：缺少异常处理
        for row in self.batch_buffer:
            self.csv_writer.writerow(row)
        self.file_handle.flush()
        self.batch_buffer.clear()
    
    async def spider_closed(self):
        # 刷新剩余数据
        await self._flush_batch()
        
        # ⚠️ 问题：缺少异常处理和closed检查
        if self.file_handle:
            self.file_handle.close()
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)


# ✅ 改进版本 - 使用ResourceManager
class ImprovedCsvPipeline:
    """改进的CSV Pipeline - 完整资源管理"""
    
    def __init__(self, crawler):
        import asyncio
        from pathlib import Path
        from datetime import datetime
        from crawlo.utils.resource_manager import ResourceManager, ResourceType
        from crawlo.utils.log import get_logger
        
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__, self.settings.get('LOG_LEVEL'))
        
        # ✅ 创建资源管理器
        self._resource_manager = ResourceManager(name="csv_pipeline")
        
        # 文件路径
        spider_name = crawler.spider.name
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.file_path = Path(f"output/{spider_name}_{timestamp}.csv")
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 延迟初始化
        self.file_handle = None
        self.csv_writer = None
        self._file_lock = asyncio.Lock()
        self._initialized = False
        
        # 批量配置
        self.batch_buffer = []
        self.batch_size = self.settings.get_int('CSV_BATCH_SIZE', 100)
        
        # 注册关闭事件
        crawler.subscriber.subscribe(self._on_spider_closed, event='spider_closed')
    
    async def _ensure_initialized(self):
        """确保文件已打开"""
        if self._initialized:
            return
        
        async with self._file_lock:
            if not self._initialized:
                import csv
                
                # 打开文件
                self.file_handle = open(
                    self.file_path, 
                    'w', 
                    newline='', 
                    encoding='utf-8'
                )
                
                # ✅ 注册到资源管理器
                self._resource_manager.register(
                    resource=self.file_handle,
                    cleanup_func=self._close_file,
                    resource_type=ResourceType.OTHER,
                    name=str(self.file_path)
                )
                
                self.csv_writer = csv.writer(self.file_handle)
                self._initialized = True
                
                self.logger.info(f"CSV文件已打开: {self.file_path}")
    
    async def _close_file(self, file_handle):
        """关闭文件句柄"""
        if file_handle and not file_handle.closed:
            try:
                # ✅ 先刷新缓冲区
                file_handle.flush()
                file_handle.close()
                self.logger.info(f"CSV文件已关闭: {self.file_path}")
            except Exception as e:
                self.logger.error(f"关闭文件失败: {e}")
    
    async def process_item(self, item, spider):
        await self._ensure_initialized()
        
        item_dict = dict(item)
        row = list(item_dict.values())
        
        async with self._file_lock:
            self.batch_buffer.append(row)
            
            if len(self.batch_buffer) >= self.batch_size:
                await self._flush_batch()
        
        return item
    
    async def _flush_batch(self):
        """刷新批量缓冲区"""
        if not self.batch_buffer:
            return
        
        try:
            # ✅ 添加异常处理
            for row in self.batch_buffer:
                self.csv_writer.writerow(row)
            
            self.file_handle.flush()
            
            count = len(self.batch_buffer)
            self.batch_buffer.clear()
            
            self.logger.debug(f"批量写入 {count} 行到CSV文件")
            self.crawler.stats.inc_value('csv/batch_written', count=count)
            
        except Exception as e:
            self.logger.error(f"批量写入失败: {e}")
            # ✅ 不清空缓冲区，保留数据
            raise
    
    async def _on_spider_closed(self):
        """爬虫关闭时清理资源"""
        self.logger.info("开始清理CSV Pipeline资源...")
        
        try:
            # ✅ 先刷新剩余数据
            if self.batch_buffer:
                await self._flush_batch()
                self.logger.info(f"刷新剩余数据: {len(self.batch_buffer)} 行")
        except Exception as e:
            self.logger.error(f"刷新批量数据失败: {e}")
        
        # ✅ 使用ResourceManager统一清理
        cleanup_result = await self._resource_manager.cleanup_all()
        
        if cleanup_result['success_count'] > 0:
            self.logger.info(
                f"CSV资源清理完成: 成功 {cleanup_result['success_count']} 个"
            )
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)


# ================== 示例3: Redis去重Pipeline改造 ==================

# ❌ 原始版本 - 存在Redis连接泄露
class OldRedisDedupPipeline:
    """原始的Redis去重Pipeline"""
    
    def __init__(self, crawler):
        import redis
        
        self.crawler = crawler
        self.settings = crawler.settings
        
        # ⚠️ 问题：直接创建连接，未注册资源管理
        self.redis_client = redis.Redis(
            host=self.settings.get('REDIS_HOST', 'localhost'),
            port=self.settings.get_int('REDIS_PORT', 6379),
            decode_responses=True
        )
        
        self.redis_key = 'crawlo:item:fingerprint'
        self.dropped_count = 0
    
    def process_item(self, item, spider):
        from crawlo.utils.fingerprint import FingerprintGenerator
        
        fingerprint = FingerprintGenerator.item_fingerprint(item)
        is_new = self.redis_client.sadd(self.redis_key, fingerprint)
        
        if not is_new:
            self.dropped_count += 1
            from crawlo.exceptions import ItemDiscard
            raise ItemDiscard(f"重复item: {fingerprint}")
        
        return item
    
    def close_spider(self, spider):
        # ⚠️ 问题：未关闭Redis连接！
        print(f"Dropped {self.dropped_count} items")
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)


# ✅ 改进版本 - 使用ResourceManager
class ImprovedRedisDedupPipeline:
    """改进的Redis去重Pipeline - 完整资源管理"""
    
    def __init__(self, crawler):
        import redis
        from crawlo.utils.resource_manager import ResourceManager, ResourceType
        from crawlo.utils.log import get_logger
        
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__, self.settings.get('LOG_LEVEL'))
        
        # ✅ 创建资源管理器
        self._resource_manager = ResourceManager(name="redis_dedup_pipeline")
        
        # Redis配置
        self.redis_host = self.settings.get('REDIS_HOST', 'localhost')
        self.redis_port = self.settings.get_int('REDIS_PORT', 6379)
        self.redis_db = self.settings.get_int('REDIS_DB', 0)
        self.redis_password = self.settings.get('REDIS_PASSWORD') or None
        
        # Redis键名
        project_name = self.settings.get('PROJECT_NAME', 'default')
        self.redis_key = f"crawlo:{project_name}:item:fingerprint"
        
        # 延迟初始化
        self.redis_client = None
        self._initialized = False
        
        self.dropped_count = 0
        
        # 注册关闭事件
        crawler.subscriber.subscribe(self._on_spider_closed, event='spider_closed')
    
    def _ensure_initialized(self):
        """确保Redis客户端已初始化"""
        if self._initialized:
            return
        
        import redis
        
        # 创建Redis客户端
        self.redis_client = redis.Redis(
            host=self.redis_host,
            port=self.redis_port,
            db=self.redis_db,
            password=self.redis_password,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        
        # 测试连接
        self.redis_client.ping()
        
        # ✅ 注册到资源管理器
        self._resource_manager.register(
            resource=self.redis_client,
            cleanup_func=self._close_client,
            resource_type=ResourceType.NETWORK,
            name="redis_client"
        )
        
        self._initialized = True
        self.logger.info(f"Redis客户端已初始化: {self.redis_host}:{self.redis_port}")
    
    def _close_client(self, client):
        """关闭Redis客户端"""
        if client:
            try:
                # ✅ 显式关闭连接
                client.close()
                self.logger.info("Redis客户端已关闭")
            except Exception as e:
                self.logger.error(f"关闭Redis客户端失败: {e}")
    
    def process_item(self, item, spider):
        self._ensure_initialized()
        
        from crawlo.utils.fingerprint import FingerprintGenerator
        from crawlo.exceptions import ItemDiscard
        
        try:
            fingerprint = FingerprintGenerator.item_fingerprint(item)
            is_new = self.redis_client.sadd(self.redis_key, fingerprint)
            
            if not is_new:
                self.dropped_count += 1
                self.logger.debug(f"丢弃重复item: {fingerprint[:20]}...")
                raise ItemDiscard(f"重复item: {fingerprint}")
            
            return item
            
        except ItemDiscard:
            raise
        except Exception as e:
            # ✅ Redis错误时继续处理，避免丢失数据
            self.logger.error(f"Redis错误: {e}")
            return item
    
    async def _on_spider_closed(self):
        """爬虫关闭时清理资源"""
        self.logger.info("开始清理Redis去重Pipeline资源...")
        
        # 记录统计
        if self.redis_client:
            try:
                total_items = self.redis_client.scard(self.redis_key)
                self.logger.info(f"去重统计: 丢弃 {self.dropped_count} 条, 总计 {total_items} 条指纹")
            except Exception as e:
                self.logger.warning(f"获取统计信息失败: {e}")
        
        # ✅ 使用ResourceManager统一清理
        import asyncio
        cleanup_result = await asyncio.to_thread(self._resource_manager.cleanup_all)
        
        if cleanup_result['success_count'] > 0:
            self.logger.info(
                f"Redis资源清理完成: 成功 {cleanup_result['success_count']} 个"
            )
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)


# ================== 使用示例 ==================

if __name__ == '__main__':
    """
    使用示例：在settings.py中配置
    
    ITEM_PIPELINES = {
        'examples.pipeline_migration_example.ImprovedMongoPipeline': 100,
        'examples.pipeline_migration_example.ImprovedCsvPipeline': 200,
        'examples.pipeline_migration_example.ImprovedRedisDedupPipeline': 300,
    }
    
    运行后可以观察到：
    1. 所有资源都会正确清理
    2. 批量数据不会丢失
    3. 异常时也能保证资源释放
    4. 日志中会显示详细的清理信息
    """
    
    print("=" * 60)
    print("Pipeline资源管理改造示例")
    print("=" * 60)
    print()
    print("✅ 改进点：")
    print("  1. 使用ResourceManager统一管理资源")
    print("  2. LIFO清理顺序，确保依赖关系正确")
    print("  3. 异常容错，单个资源失败不影响其他")
    print("  4. 延迟初始化，避免不必要的资源占用")
    print("  5. 完善的日志记录，便于调试")
    print()
    print("📝 使用方法：")
    print("  1. 将改进的Pipeline类复制到你的项目")
    print("  2. 在settings.py中配置ITEM_PIPELINES")
    print("  3. 运行爬虫，观察资源清理日志")
    print()
    print("🧪 验证方法：")
    print("  1. 使用LeakDetector检测资源泄露")
    print("  2. 查看日志中的清理信息")
    print("  3. 使用psutil监控内存和文件描述符")
