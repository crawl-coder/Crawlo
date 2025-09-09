# -*- coding: UTF-8 -*-
"""
api_data_collection.redis_pipelines
===============================
基于 Redis 的分布式数据处理管道
"""

import hashlib
import redis
from crawlo.exceptions import DropItem


class RedisDeduplicationPipeline:
    """基于 Redis 的分布式数据项去重管道"""
    
    def __init__(self, redis_host='localhost', redis_port=6379, redis_db=2, redis_password=None):
        """
        初始化 Redis 连接
        
        注意：这个管道实现的是数据项级别的去重，而不是请求级别的去重。
        请求级别的去重由 Crawlo 框架内置机制处理。
        
        :param redis_host: Redis 主机地址
        :param redis_port: Redis 端口
        :param redis_db: Redis 数据库编号
        :param redis_password: Redis 密码
        """
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=True
        )
        # 使用专门的键来存储数据项指纹
        # 注意：这与框架内置的请求去重使用不同的 Redis 键
        self.redis_key = "api_data:item_fingerprints"
    
    @classmethod
    def from_settings(cls, settings):
        """
        从设置中创建管道实例
        :param settings: 设置对象
        :return: 管道实例
        """
        return cls(
            redis_host=settings.get('REDIS_HOST', 'localhost'),
            redis_port=settings.get('REDIS_PORT', 6379),
            redis_db=settings.get('REDIS_DB', 2),
            redis_password=settings.get('REDIS_PASSWORD') or None
        )
    
    def process_item(self, item, spider):
        """
        处理数据项，进行去重检查
        
        这个方法实现的是数据项级别的去重：
        1. 基于数据项的关键字段生成指纹
        2. 检查指纹是否已在 Redis 中存在
        3. 如果存在则丢弃数据项，否则保存指纹并继续处理
        
        注意：这与 Crawlo 框架内置的请求去重是不同的机制：
        - 框架内置去重：防止发送重复的网络请求
        - 管道去重：防止保存重复的数据结果
        
        :param item: 数据项
        :param spider: 爬虫实例
        :return: 处理后的数据项或抛出 DropItem 异常
        """
        # 基于关键字段生成数据项指纹
        fingerprint = self._generate_item_fingerprint(item)
        
        # 使用 Redis 的 SADD 命令检查并添加指纹
        # 如果指纹已存在，SADD 返回 0；如果指纹是新的，SADD 返回 1
        is_new = self.redis_client.sadd(self.redis_key, fingerprint)
        
        if not is_new:
            # 如果指纹已存在，丢弃这个数据项
            raise DropItem(f"重复的数据项: {fingerprint}")
        else:
            # 如果是新数据项，继续处理
            return item
    
    def _generate_item_fingerprint(self, item):
        """
        生成数据项指纹
        
        基于数据项的关键字段生成唯一指纹，用于去重判断。
        不同于请求去重（基于 URL 等），这里基于数据内容去重。
        
        :param item: 数据项
        :return: 指纹字符串
        """
        # 使用数据项的关键字段生成指纹
        key_fields = [
            str(item.get('id', '')),
            item.get('name', ''),
            item.get('category', '')
        ]
        fingerprint_string = '|'.join(key_fields)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()
    
    def close_spider(self, spider):
        """
        爬虫关闭时的清理工作
        :param spider: 爬虫实例
        """
        # 在生产环境中，可能需要保留指纹用于后续的去重
        # 如果需要清理，可以取消下面的注释
        # self.redis_client.delete(self.redis_key)
        pass