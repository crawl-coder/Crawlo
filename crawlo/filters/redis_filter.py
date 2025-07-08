#!/usr/bin/python
# -*- coding:UTF-8 -*-
import redis

from crawlo import Request
from crawlo.filters import BaseFilter
from crawlo.utils.log import get_logger
from crawlo.utils.request import request_fingerprint


class RedisFilter(BaseFilter):
    """使用Redis集合实现的同步请求去重过滤器"""

    def __init__(
            self,
            redis_key: str,
            client: redis.Redis,
            stats: dict,
            debug: bool,
            log_level: str,
            save_fp: bool
    ):
        """
        初始化过滤器

        :param redis_key: Redis存储键名
        :param client: redis客户端实例
        :param stats: 统计字典
        :param debug: 是否启用调试模式
        :param log_level: 日志级别
        :param save_fp: 是否保留指纹数据
        """
        self.logger = get_logger(self.__class__.__name__, log_level)
        super().__init__(self.logger, stats, debug)

        self.redis_key = redis_key
        self.redis = client
        self.save_fp = save_fp

    @classmethod
    def create_instance(cls, crawler) -> 'BaseFilter':
        """工厂方法创建实例"""
        redis_url = crawler.settings.get('REDIS_URL', 'redis://localhost:6379')
        decode_responses = crawler.settings.get_bool('DECODE_RESPONSES', True)

        try:
            # 添加连接池配置
            redis_client = redis.from_url(
                redis_url,
                decode_responses=decode_responses,
                socket_timeout=5,  # 超时设置
                socket_connect_timeout=5,
                max_connections=20  # 连接池大小
            )
            # 测试连接是否有效
            redis_client.ping()
        except redis.RedisError as e:
            raise RuntimeError(f"Redis连接失败: {str(e)}")

        return cls(
            redis_key=f"{crawler.settings.get('PROJECT_NAME')}:{crawler.settings.get('REDIS_KEY', 'request_fingerprints')}",
            client=redis_client,
            stats=crawler.stats,
            save_fp=crawler.settings.get_bool('SAVE_FP', False),
            debug=crawler.settings.get_bool('FILTER_DEBUG', False),
            log_level=crawler.settings.get('LOG_LEVEL', 'INFO')
        )

    def requested(self, request: Request) -> bool:
        """
        检查请求是否已存在

        :param request: 请求对象
        :return: 是否重复
        """
        fp = request_fingerprint(request)
        try:
            if self.redis.sismember(self.redis_key, fp):
                self.logger.debug(f"重复请求: {fp}")
                return True

            self.add_fingerprint(fp)
            return False
        except redis.RedisError as e:
            self.logger.error(f"Redis操作失败: {str(e)}")
            raise

    def add_fingerprint(self, fp: str) -> None:
        """添加指纹到Redis集合"""
        try:
            self.redis.sadd(self.redis_key, fp)
            self.logger.debug(f"新增指纹: {fp}")
        except redis.RedisError as e:
            self.logger.error(f"指纹添加失败: {str(e)}")
            raise

    def __contains__(self, item) -> bool:
        """支持 in 操作符检查 (必须返回bool类型)"""
        try:
            # 显式将redis返回的0/1转换为bool
            return bool(self.redis.sismember(self.redis_key, item))
        except redis.RedisError as e:
            self.logger.error(f"Redis查询失败: {str(e)}")
            raise

    def close(self) -> None:
        """同步清理方法（注意不是异步的closed）"""
        if not self.save_fp:
            try:
                count = self.redis.delete(self.redis_key)
                self.logger.info(f"已清理Redis键 {self.redis_key}, 删除数量: {count}")
            except redis.RedisError as e:
                self.logger.error(f"清理失败: {str(e)}")
            finally:
                # 同步客户端需要手动关闭连接池
                self.redis.close()

    async def closed(self):
        """兼容异步接口的同步实现"""
        self.close()