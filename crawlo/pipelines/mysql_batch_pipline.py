import asyncio
import logging
from crawlo.exceptions import NotConfiguredError

logger = logging.getLogger(__name__)


class AsyncmyMySQLPipeline:
    """
    异步 MySQL 管道，用于批量将爬取的数据存储到 MySQL 数据库
    """

    def __init__(self, host, port, user, password, db, batch_size, table_name):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db = db
        self.batch_size = batch_size
        self.table_name = table_name
        self.buffer = []
        self.pool = None
        self.flush_task = None
        self.insert_stmt = None

    @classmethod
    def from_crawler(cls, crawler):
        """从爬虫配置中获取数据库连接参数"""
        batch_size = crawler.settings.get_int('MYSQL_BATCH_SIZE', 100)

        return cls(
            host=crawler.settings.get('MYSQL_HOST'),
            port=crawler.settings.get('MYSQL_PORT'),
            user=crawler.settings.get('MYSQL_USER'),
            password=crawler.settings.get('MYSQL_PASSWORD'),
            db=crawler.settings.get('MYSQL_DB'),
            batch_size=batch_size,
            table_name=crawler.settings.get('MYSQL_TABLE'),
        )

    async def open_spider(self, spider):
        """爬虫启动时初始化数据库连接池"""
        try:
            import asyncmy
            self.pool = await asyncmy.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                db=self.db,
                autocommit=True,
                charset='utf8mb4',
                cursorclass=asyncmy.cursors.DictCursor
            )
            logger.info(f"MySQL 连接池已创建，主机: {self.host}, 数据库: {self.db}")

            # 创建自动刷新任务
            self.flush_task = asyncio.create_task(self._auto_flush())

        except Exception as e:
            logger.error(f"无法创建 MySQL 连接池: {e}")
            raise NotConfiguredError(f"MySQL 连接失败: {e}")

    async def process_item(self, item, spider):
        """处理爬取的每个项目，添加到缓冲区"""
        self.buffer.append(dict(item))

        # 当缓冲区达到批量大小时自动刷新
        if len(self.buffer) >= self.batch_size:
            await self._flush_buffer()

        return item

    async def _flush_buffer(self):
        """将缓冲区中的数据批量写入数据库"""
        if not self.buffer:
            return

        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 动态生成插入语句
                    if not self.insert_stmt:
                        columns = ', '.join(self.buffer[0].keys())
                        placeholders = ', '.join(['%s'] * len(self.buffer[0]))
                        self.insert_stmt = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"

                    # 准备批量插入的数据
                    values = [tuple(item.values()) for item in self.buffer]

                    # 执行批量插入
                    await cursor.executemany(self.insert_stmt, values)
                    logger.debug(f"已批量插入 {len(values)} 条记录到 {self.table_name}")

                    # 清空缓冲区
                    self.buffer.clear()

        except Exception as e:
            logger.error(f"批量插入失败: {e}")
            # 发生错误时保留数据，避免数据丢失
            # 实际生产环境中可能需要更复杂的错误处理策略

    async def _auto_flush(self):
        """定期自动刷新缓冲区，防止数据长时间停留在内存中"""
        try:
            while True:
                await asyncio.sleep(10)  # 每10秒检查一次
                if self.buffer:
                    await self._flush_buffer()
        except asyncio.CancelledError:
            logger.info("自动刷新任务已取消")

    async def spider_closed(self, spider):
        """爬虫关闭时执行清理工作"""
        try:
            # 取消自动刷新任务
            if self.flush_task:
                self.flush_task.cancel()
                await self.flush_task  # 等待任务完成取消

            # 确保缓冲区中的剩余数据被写入数据库
            if self.buffer:
                await self._flush_buffer()

        except asyncio.CancelledError:
            logger.info("爬虫关闭过程中自动刷新任务被取消")
        except Exception as e:
            logger.error(f"爬虫关闭时发生错误: {e}")
        finally:
            # 关闭数据库连接池
            if self.pool:
                self.pool.close()
                await self.pool.wait_closed()
                logger.info("MySQL 连接池已关闭")