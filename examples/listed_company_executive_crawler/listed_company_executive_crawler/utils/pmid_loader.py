#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
PMID 预加载工具
提供爬虫启动时一次性加载所有已存在PMID到内存的功能
避免逐条或批量查询数据库，提升去重检查性能
使用 asyncmy 异步 MySQL 驱动
"""
import asyncio
import asyncmy
import warnings
from crawlo.logging import get_logger

# 禁用aiomysql连接的ResourceWarning
warnings.filterwarnings('ignore', category=ResourceWarning, module='asyncmy')

logger = get_logger(__name__)


def get_db_config():
    """
    获取数据库配置
    """
    # 动态导入以避免循环导入
    import importlib
    try:
        settings_module = importlib.import_module('listed_company_executive_crawler.settings')
    except ModuleNotFoundError:
        raise ImportError("Settings module not found. Please create a settings.py file in the project root directory.")
    return {
        'host': settings_module.MYSQL_HOST,
        'port': settings_module.MYSQL_PORT,
        'user': settings_module.MYSQL_USER,
        'password': settings_module.MYSQL_PASSWORD,
        'db': settings_module.MYSQL_DB,
        'charset': 'utf8mb4'
    }


async def load_all_pmids(table_name):
    """
    异步加载指定表中所有已存在的PMID到内存集合
    
    Args:
        table_name (str): 表名
    
    Returns:
        set: 包含所有已存在PMID的集合
    
    Example:
        >>> pmids = await load_all_pmids('listed_executive_changes')
        >>> if some_pmid in pmids:
        ...     print("记录已存在")
    """
    db_config = get_db_config()
    conn = None
    cursor = None
    
    try:
        logger.info(f"开始从表 {table_name} 加载已存在的PMID...")
        
        # 创建数据库连接
        conn = await asyncmy.connect(**db_config)
        # cursor()是同步方法，不需要await
        cursor = conn.cursor()
        
        # 查询所有已存在的PMID
        sql = f"SELECT pmid FROM {table_name} WHERE pmid IS NOT NULL"
        await cursor.execute(sql)
        rows = await cursor.fetchall()
        
        # 将PMID存入集合
        pmid_set = {row[0] for row in rows}
        
        logger.info(f"✓ 成功加载 {len(pmid_set)} 个PMID到内存（表: {table_name}）")
        
        return pmid_set
        
    except Exception as e:
        logger.error(f"加载PMID失败: 表={table_name}, 错误={e}")
        return set()
    finally:
        # 确保资源被正确释放
        if cursor:
            try:
                await cursor.close()
            except Exception as e:
                logger.warning(f"关闭游标时出现异常: {e}")
        if conn:
            try:
                conn.close()
            except Exception as e:
                logger.warning(f"关闭连接时出现异常: {e}")


class PmidCache:
    """
    PMID 缓存管理器
    提供懒加载、自动刷新等功能
    
    Example:
        >>> cache = PmidCache('listed_executive_changes')
        >>> # 第一次调用时自动加载
        >>> if await cache.exists('some_pmid'):
        ...     print("记录已存在")
        >>> # 插入新记录后添加到缓存
        >>> cache.add('new_pmid')
    """
    
    def __init__(self, table_name):
        """
        初始化PMID缓存
        
        Args:
            table_name (str): 数据库表名
        """
        self.table_name = table_name
        self._pmid_set = None
        self._load_lock = asyncio.Lock()  # 防止并发加载
    
    async def _ensure_loaded(self):
        """确保PMID已加载（懒加载，线程安全）"""
        if self._pmid_set is None:
            async with self._load_lock:
                # 双重检查，防止并发竞态
                if self._pmid_set is None:
                    self._pmid_set = await load_all_pmids(self.table_name)
    
    async def exists(self, pmid):
        """
        检查PMID是否已存在
        
        Args:
            pmid (str): 要检查的PMID
        
        Returns:
            bool: True表示存在，False表示不存在
        """
        await self._ensure_loaded()
        return pmid in self._pmid_set
    
    def add(self, pmid):
        """
        添加PMID到缓存（插入新记录后调用）
        
        Args:
            pmid (str): 要添加的PMID
        """
        if self._pmid_set is not None:
            self._pmid_set.add(pmid)
    
    def add_many(self, pmid_list):
        """
        批量添加PMID到缓存
        
        Args:
            pmid_list (list): PMID列表
        """
        if self._pmid_set is not None:
            self._pmid_set.update(pmid_list)
    
    def count(self):
        """
        获取缓存中的PMID数量
        
        Returns:
            int: PMID数量
        """
        if self._pmid_set is None:
            return 0
        return len(self._pmid_set)
    
    def clear(self):
        """清空缓存"""
        if self._pmid_set is not None:
            self._pmid_set.clear()
            self._pmid_set = None
            logger.info(f"已清空PMID缓存（表: {self.table_name}）")
    
    async def refresh(self):
        """重新从数据库加载PMID"""
        self._pmid_set = await load_all_pmids(self.table_name)
