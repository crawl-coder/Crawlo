# -*- coding: utf-8 -*-
"""
Pipeline基类 - 提供统一的资源管理
====================================

Pipeline体系说明：
- BasePipeline: 基础抽象类，定义Pipeline接口规范
- ResourceManagedPipeline: 提供资源管理功能的基类（推荐）
- FileBasedPipeline: 文件操作专用基类
- DatabasePipeline: 数据库操作专用基类
- CacheBasedPipeline: 缓存操作专用基类

与 PipelineManager 的关系：
- base_pipeline.py: 定义单个Pipeline的实现规范（本文件）
- pipeline_manager.py: 协调多个Pipeline的执行流程
- 两者分工明确，互相配合，不是重复设计

使用方法:
    # 简单场景 - 直接继承BasePipeline
    class SimplePipeline(BasePipeline):
        @classmethod
        def from_crawler(cls, crawler):
            return cls()
        
        async def process_item(self, item, spider):
            return item
    
    # 复杂场景 - 使用ResourceManagedPipeline（推荐）
    class MyPipeline(ResourceManagedPipeline):
        async def _initialize_resources(self):
            # 初始化资源
            pass
            
        async def _cleanup_resources(self):
            # 清理资源
            pass
            
        async def process_item(self, item, spider):
            # 处理逻辑
            return item
"""

import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Any, Callable

from crawlo.items import Item
from crawlo.spider import Spider
from crawlo.logging import get_logger
from crawlo.utils.resource_manager import ResourceManager, ResourceType


class BasePipeline(ABC):
    """
    Pipeline基础抽象类
    
    所有Pipeline都应继承此基类，确保统一的接口规范。
    简单场景可直接使用，复杂场景建议使用ResourceManagedPipeline。
    """

    @classmethod
    @abstractmethod
    def from_crawler(cls, crawler):
        """从Crawler创建Pipeline实例"""
        raise NotImplementedError("子类必须实现from_crawler方法")
    
    @abstractmethod
    async def process_item(self, item: Item, spider: Spider, **kwargs) -> Optional[Item]:
        """处理Item的核心方法"""
        raise NotImplementedError("子类必须实现process_item方法")
    
    @classmethod
    def create_instance(cls, crawler):
        """兼容旧版本的创建方法，内部调用from_crawler"""
        return cls.from_crawler(crawler)


class ResourceManagedPipeline(BasePipeline):
    """
    资源管理Pipeline基类
    
    提供统一的资源管理功能，自动注册到ResourceManager
    
    特性：
    - 自动资源清理
    - LIFO清理顺序
    - 异常容错
    - 批量数据刷新
    """
    
    def __init__(self, crawler):
        """
        初始化Pipeline
        
        Args:
            crawler: Crawler实例
        """
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(
            self.__class__.__name__, 
            self.settings.get('LOG_LEVEL')
        )
        
        # 资源管理器
        self._resource_manager = ResourceManager(
            name=f"pipeline.{self.__class__.__name__}"
        )
        
        # 初始化标志
        self._initialized = False
        self._init_lock = asyncio.Lock()
        
        # 批量缓冲区（子类可选使用）
        self.batch_buffer = []
        self.batch_size = self.settings.get_int('PIPELINE_BATCH_SIZE', 100)
        self.use_batch = self.settings.get_bool('PIPELINE_USE_BATCH', False)
        
        # 注册关闭事件
        crawler.subscriber.subscribe(self._on_spider_closed, event='spider_closed')
        
        self.logger.debug(f"{self.__class__.__name__} 已初始化")
    
    async def _ensure_initialized(self):
        """确保资源已初始化（线程安全）"""
        if self._initialized:
            return
        
        async with self._init_lock:
            if not self._initialized:
                try:
                    await self._initialize_resources()
                    self._initialized = True
                    self.logger.info(f"{self.__class__.__name__} 资源初始化完成")
                except Exception as e:
                    self.logger.error(f"资源初始化失败: {e}")
                    raise
    
    @abstractmethod
    async def _initialize_resources(self):
        """
        初始化资源（子类实现）
        
        示例：
            # 初始化数据库连接池
            self.pool = await create_pool(...)
            
            # 注册到资源管理器
            self._resource_manager.register(
                resource=self.pool,
                cleanup_func=self._close_pool,
                resource_type=ResourceType.DATABASE,
                name="db_pool"
            )
        """
        pass
    
    @abstractmethod
    async def _cleanup_resources(self):
        """
        清理资源（子类实现）
        
        通常由ResourceManager自动调用，但也可以手动实现额外清理逻辑
        """
        pass
    
    async def _flush_batch(self, spider: Spider):
        """
        刷新批量缓冲区（子类可重写）
        
        Args:
            spider: Spider实例
        """
        if not self.batch_buffer:
            return
        
        self.logger.warning(
            f"批量缓冲区还有 {len(self.batch_buffer)} 条数据，"
            f"但未实现 _flush_batch 方法"
        )
    
    async def _on_spider_closed(self):
        """
        爬虫关闭事件处理
        
        自动执行：
        1. 刷新批量数据
        2. 清理所有注册的资源
        3. 生成统计报告
        """
        self.logger.info(f"{self.__class__.__name__} 开始清理资源...")
        
        try:
            # 1. 刷新批量数据
            if self.use_batch and self.batch_buffer:
                spider = self.crawler.spider
                await self._flush_batch(spider)
                self.logger.info(f"批量数据已刷新，共 {len(self.batch_buffer)} 条")
            
            # 2. 调用子类的清理方法
            await self._cleanup_resources()
            
            # 3. 使用资源管理器统一清理
            cleanup_result = await self._resource_manager.cleanup_all()
            
            # 4. 记录清理结果
            if cleanup_result['success_count'] > 0:
                self.logger.info(
                    f"资源清理完成: 成功 {cleanup_result['success_count']} 个, "
                    f"失败 {cleanup_result['failed_count']} 个"
                )
            
            if cleanup_result['errors']:
                self.logger.warning(f"清理时出现错误: {cleanup_result['errors']}")
            
        except Exception as e:
            self.logger.error(f"资源清理失败: {e}", exc_info=True)
    
    def register_resource(
        self,
        resource: Any,
        cleanup_func: Callable,
        resource_type: ResourceType = ResourceType.OTHER,
        name: Optional[str] = None
    ):
        """
        注册需要清理的资源
        
        Args:
            resource: 资源对象
            cleanup_func: 清理函数
            resource_type: 资源类型
            name: 资源名称
        """
        self._resource_manager.register(
            resource=resource,
            cleanup_func=cleanup_func,
            resource_type=resource_type,
            name=name or str(id(resource))
        )
        self.logger.debug(f"注册资源: {name} ({resource_type})")


class FileBasedPipeline(ResourceManagedPipeline):
    """
    文件型Pipeline基类
    
    提供文件操作的通用功能：
    - 自动创建目录
    - 文件句柄管理
    - 自动刷新缓冲区
    """
    
    def __init__(self, crawler):
        super().__init__(crawler)
        self.file_handle: Optional[Any] = None
        self.file_path: Optional[Path] = None
        self._file_lock = asyncio.Lock()
    
    def _get_file_path(self, config_key: str, default_prefix: str, extension: str) -> Path:
        """
        获取输出文件路径
        
        Args:
            config_key: 配置键名
            default_prefix: 默认前缀
            extension: 文件扩展名
        
        Returns:
            Path对象
        """
        from datetime import datetime
        
        file_path = (
            self.settings.get(config_key) or
            getattr(self.crawler.spider, config_key.lower(), None) or
            f"output/{self.crawler.spider.name}_{default_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{extension}"
        )
        
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    
    async def _open_file(self, mode: str = 'w', **kwargs):
        """
        打开文件并注册到资源管理器
        
        Args:
            mode: 文件打开模式
            **kwargs: 传递给open()的其他参数
        """
        if self.file_handle is not None:
            return
        
        async with self._file_lock:
            if self.file_handle is None:
                if self.file_path is None:
                    raise ValueError("文件路径未设置")
                
                self.file_handle = open(
                    self.file_path, 
                    mode, 
                    encoding=kwargs.get('encoding', 'utf-8'),
                    **{k: v for k, v in kwargs.items() if k != 'encoding'}
                )
                
                # 注册文件句柄到资源管理器
                self.register_resource(
                    resource=self.file_handle,
                    cleanup_func=self._close_file,
                    resource_type=ResourceType.OTHER,  # 使用OTHER类型
                    name=str(self.file_path)
                )
                
                self.logger.info(f"文件已打开: {self.file_path}")
    
    async def _close_file(self, file_handle):
        """关闭文件句柄"""
        if file_handle and not file_handle.closed:
            file_handle.close()
            self.logger.info(f"文件已关闭: {self.file_path}")
    
    async def _initialize_resources(self):
        """初始化文件资源"""
        # 子类应该调用 _open_file() 来打开文件
        pass
    
    async def _cleanup_resources(self):
        """清理由ResourceManager管理的资源"""
        # 文件句柄由ResourceManager自动清理
        pass


class DatabasePipeline(ResourceManagedPipeline):
    """
    数据库Pipeline基类
    
    提供数据库操作的通用功能：
    - 连接池管理
    - 自动重连
    - 批量写入优化
    - 事务支持
    """
    
    def __init__(self, crawler):
        super().__init__(crawler)
        self.pool = None
        self._pool_lock = asyncio.Lock()
        self._pool_initialized = False
    
    async def _ensure_pool_initialized(self):
        """确保连接池已初始化"""
        if self._pool_initialized and self.pool:
            return
        
        async with self._pool_lock:
            if not self._pool_initialized:
                await self._create_pool()
                self._pool_initialized = True
                self.logger.info(f"{self.__class__.__name__} 连接池已初始化")
    
    @abstractmethod
    async def _create_pool(self):
        """
        创建数据库连接池（子类实现）
        
        示例：
            self.pool = await create_pool(...)
            
            # 注册到资源管理器
            self.register_resource(
                resource=self.pool,
                cleanup_func=self._close_pool,
                resource_type=ResourceType.DATABASE,
                name="db_pool"
            )
        """
        raise NotImplementedError("子类必须实现 _create_pool 方法")
    
    @abstractmethod
    async def _close_pool(self, pool):
        """关闭连接池（子类实现）"""
        raise NotImplementedError("子类必须实现 _close_pool 方法")
    
    async def _initialize_resources(self):
        """初始化数据库资源"""
        await self._ensure_pool_initialized()
    
    async def _cleanup_resources(self):
        """清理由ResourceManager管理的资源"""
        # 连接池由ResourceManager自动清理
        pass


class CacheBasedPipeline(ResourceManagedPipeline):
    """
    缓存型Pipeline基类
    
    提供缓存操作的通用功能：
    - Redis/Memcached连接管理
    - 自动关闭连接
    """
    
    def __init__(self, crawler):
        super().__init__(crawler)
        self.client = None
        self._client_lock = asyncio.Lock()
        self._client_initialized = False
    
    async def _ensure_client_initialized(self):
        """确保缓存客户端已初始化"""
        if self._client_initialized and self.client:
            return
        
        async with self._client_lock:
            if not self._client_initialized:
                await self._create_client()
                self._client_initialized = True
                self.logger.info(f"{self.__class__.__name__} 缓存客户端已初始化")
    
    @abstractmethod
    async def _create_client(self):
        """
        创建缓存客户端（子类实现）
        
        示例：
            self.client = redis.Redis(...)
            
            # 注册到资源管理器
            self.register_resource(
                resource=self.client,
                cleanup_func=self._close_client,
                resource_type=ResourceType.NETWORK,
                name="cache_client"
            )
        """
        raise NotImplementedError("子类必须实现 _create_client 方法")
    
    @abstractmethod
    async def _close_client(self, client):
        """关闭缓存客户端（子类实现）"""
        raise NotImplementedError("子类必须实现 _close_client 方法")
    
    async def _initialize_resources(self):
        """初始化缓存资源"""
        await self._ensure_client_initialized()
    
    async def _cleanup_resources(self):
        """清理由ResourceManager管理的资源"""
        # 客户端由ResourceManager自动清理
        pass
