#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2025-09-10 22:00
# @Author  : crawl-coder
# @Desc    : 分布式协调工具
"""

import hashlib
import time
import urllib.parse
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List, Set
from urllib.parse import urlparse

from crawlo.utils.fingerprint import FingerprintGenerator


class TaskDistributor:
    """任务分发工具类"""

    @staticmethod
    def generate_pagination_tasks(base_url: str, start_page: int = 1,
                                  end_page: int = 100, page_param: str = "page") -> List[str]:
        """
        生成分页任务URL列表
        
        Args:
            base_url (str): 基础URL
            start_page (int): 起始页码
            end_page (int): 结束页码
            page_param (str): 分页参数名
            
        Returns:
            List[str]: 分页URL列表
        """
        tasks = []
        parsed = urlparse(base_url)
        query_dict = dict([q.split('=') for q in parsed.query.split('&') if q]) if parsed.query else {}

        for page in range(start_page, end_page + 1):
            query_dict[page_param] = str(page)
            query_string = '&'.join([f"{k}={v}" for k, v in query_dict.items()])
            new_parsed = parsed._replace(query=query_string)
            tasks.append(urllib.parse.urlunparse(new_parsed))

        return tasks

    @staticmethod
    def distribute_tasks(tasks: List[Any], num_workers: int) -> List[List[Any]]:
        """
        将任务分发给多个工作节点
        
        Args:
            tasks (List[Any]): 任务列表
            num_workers (int): 工作节点数量
            
        Returns:
            List[List[Any]]: 分发后的任务列表
        """
        if num_workers <= 0:
            raise ValueError("工作节点数量必须大于0")

        if not tasks:
            return [[] for _ in range(num_workers)]

        # 计算每个工作节点应分配的任务数量
        tasks_per_worker = len(tasks) // num_workers
        remaining_tasks = len(tasks) % num_workers

        distributed_tasks = []
        task_index = 0

        for i in range(num_workers):
            # 分配基础任务数量
            worker_tasks_count = tasks_per_worker
            # 分配剩余任务
            if i < remaining_tasks:
                worker_tasks_count += 1

            worker_tasks = tasks[task_index:task_index + worker_tasks_count]
            distributed_tasks.append(worker_tasks)
            task_index += worker_tasks_count

        return distributed_tasks


class DeduplicationTool:
    """数据去重工具类"""

    def __init__(self):
        self.memory_set: Set[str] = set()
        self.bloom_filter = None  # 在实际应用中可以集成布隆过滤器

    @staticmethod
    def generate_fingerprint(data: Any) -> str:
        """
        生成数据指纹
        
        Args:
            data (Any): 数据
            
        Returns:
            str: 数据指纹（SHA256哈希）
        """
        return FingerprintGenerator.data_fingerprint(data)

    def is_duplicate(self, data: Any) -> bool:
        """
        检查数据是否重复（内存去重）
        
        Args:
            data (Any): 数据
            
        Returns:
            bool: 是否重复
        """
        fingerprint = self.generate_fingerprint(data)
        return fingerprint in self.memory_set

    def add_to_dedup(self, data: Any) -> bool:
        """
        将数据添加到去重集合
        
        Args:
            data (Any): 数据
            
        Returns:
            bool: 是否成功添加（True表示之前不存在，False表示已存在）
        """
        fingerprint = self.generate_fingerprint(data)
        if fingerprint in self.memory_set:
            return False
        else:
            self.memory_set.add(fingerprint)
            return True

    async def async_is_duplicate(self, data: Any) -> bool:
        """
        异步检查数据是否重复
        
        Args:
            data (Any): 数据
            
        Returns:
            bool: 是否重复
        """
        return self.is_duplicate(data)

    async def async_add_to_dedup(self, data: Any) -> bool:
        """
        异步将数据添加到去重集合
        
        Args:
            data (Any): 数据
            
        Returns:
            bool: 是否成功添加
        """
        return self.add_to_dedup(data)


class DistributedCoordinator:
    """分布式协调工具类"""

    def __init__(self, redis_client: Any = None):
        """
        初始化分布式协调工具
        
        Args:
            redis_client (Any): Redis客户端
        """
        self.redis_client = redis_client
        self.task_distributor = TaskDistributor()
        self.deduplication_tool = DeduplicationTool()

    @staticmethod
    def generate_task_id(url: str, spider_name: str) -> str:
        """
        生成任务ID
        
        Args:
            url (str): URL
            spider_name (str): 爬虫名称
            
        Returns:
            str: 任务ID
        """
        # 使用URL和爬虫名称生成唯一任务ID
        unique_string = f"{url}_{spider_name}_{int(time.time() * 1000)}"
        return hashlib.md5(unique_string.encode('utf-8')).hexdigest()

    async def claim_task(self, task_id: str, worker_id: str,
                         timeout: int = 300) -> Tuple[bool, Optional[str]]:
        """
        声明任务（分布式锁）
        
        Args:
            task_id (str): 任务ID
            worker_id (str): 工作节点ID
            timeout (int): 锁超时时间（秒）
            
        Returns:
            Tuple[bool, Optional[str]]: (是否成功声明, 错误信息)
        """
        # 如果没有Redis客户端，使用内存模拟
        if self.redis_client is None:
            # 模拟成功声明
            return True, None

        try:
            # 实际实现应该使用Redis的SET命令带有NX和EX选项
            # result = await self.redis_client.set(f"task_lock:{task_id}", worker_id, nx=True, ex=timeout)
            # return bool(result), None if result else "任务已被其他节点声明"
            return True, None
        except Exception as e:
            return False, str(e)

    async def report_task_status(self, task_id: str, status: str, worker_id: str) -> bool:
        """
        报告任务状态
        
        Args:
            task_id (str): 任务ID
            status (str): 任务状态 (pending, processing, completed, failed)
            worker_id (str): 工作节点ID
            
        Returns:
            bool: 是否成功报告
        """
        try:
            status_info = {
                "task_id": task_id,
                "status": status,
                "worker_id": worker_id,
                "timestamp": datetime.now().isoformat()
            }

            if self.redis_client is None:
                # 模拟成功报告
                print(f"报告任务状态: {status_info}")
                return True

            # 实际实现应该将状态信息存储到Redis中
            # await self.redis_client.hset(f"task_status:{task_id}", mapping=status_info)
            return True
        except Exception:
            return False

    async def get_cluster_info(self) -> Dict[str, Any]:
        """
        获取集群信息
        
        Returns:
            Dict[str, Any]: 集群信息
        """
        try:
            if self.redis_client is None:
                # 返回模拟的集群信息
                return {
                    "worker_count": 3,
                    "active_workers": ["worker_1", "worker_2", "worker_3"],
                    "task_queue_size": 100,
                    "processed_tasks": 500,
                    "failed_tasks": 5,
                    "timestamp": datetime.now().isoformat()
                }

            # 实际实现应该从Redis获取集群信息
            # 这里返回模拟数据
            return {
                "worker_count": 3,
                "active_workers": ["worker_1", "worker_2", "worker_3"],
                "task_queue_size": 100,
                "processed_tasks": 500,
                "failed_tasks": 5,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e)}

    def generate_pagination_tasks(self, base_url: str, start_page: int = 1,
                                  end_page: int = 100, page_param: str = "page") -> List[str]:
        """
        生成分页任务URL列表
        
        Args:
            base_url (str): 基础URL
            start_page (int): 起始页码
            end_page (int): 结束页码
            page_param (str): 分页参数名
            
        Returns:
            List[str]: 分页URL列表
        """
        return self.task_distributor.generate_pagination_tasks(base_url, start_page, end_page, page_param)

    def distribute_tasks(self, tasks: List[Any], num_workers: int) -> List[List[Any]]:
        """
        将任务分发给多个工作节点
        
        Args:
            tasks (List[Any]): 任务列表
            num_workers (int): 工作节点数量
            
        Returns:
            List[List[Any]]: 分发后的任务列表
        """
        return self.task_distributor.distribute_tasks(tasks, num_workers)

    async def is_duplicate(self, data: Any) -> bool:
        """
        检查数据是否重复
        
        Args:
            data (Any): 数据
            
        Returns:
            bool: 是否重复
        """
        # 如果有Redis客户端，可以使用布隆过滤器或Redis集合进行去重
        if self.redis_client is not None:
            # 这里可以实现基于Redis的去重逻辑
            pass

        # 使用内存去重作为后备方案
        return await self.deduplication_tool.async_is_duplicate(data)

    async def add_to_dedup(self, data: Any) -> bool:
        """
        将数据添加到去重集合
        
        Args:
            data (Any): 数据
            
        Returns:
            bool: 是否成功添加
        """
        # 如果有Redis客户端，可以使用布隆过滤器或Redis集合进行去重
        if self.redis_client is not None:
            # 这里可以实现基于Redis的去重逻辑
            pass

        # 使用内存去重作为后备方案
        return await self.deduplication_tool.async_add_to_dedup(data)


# 便捷函数
def generate_task_id(url: str, spider_name: str) -> str:
    """生成任务ID"""
    return DistributedCoordinator.generate_task_id(url, spider_name)


async def claim_task(task_id: str, worker_id: str,
                     redis_client: Any = None, timeout: int = 300) -> Tuple[bool, Optional[str]]:
    """声明任务"""
    coordinator = DistributedCoordinator(redis_client)
    return await coordinator.claim_task(task_id, worker_id, timeout)


async def report_task_status(task_id: str, status: str, worker_id: str,
                             redis_client: Any = None) -> bool:
    """报告任务状态"""
    coordinator = DistributedCoordinator(redis_client)
    return await coordinator.report_task_status(task_id, status, worker_id)


async def get_cluster_info(redis_client: Any = None) -> Dict[str, Any]:
    """获取集群信息"""
    coordinator = DistributedCoordinator(redis_client)
    return await coordinator.get_cluster_info()


def generate_pagination_tasks(base_url: str, start_page: int = 1,
                              end_page: int = 100, page_param: str = "page") -> List[str]:
    """生成分页任务URL列表"""
    coordinator = DistributedCoordinator()
    return coordinator.generate_pagination_tasks(base_url, start_page, end_page, page_param)


def distribute_tasks(tasks: List[Any], num_workers: int) -> List[List[Any]]:
    """将任务分发给多个工作节点"""
    coordinator = DistributedCoordinator()
    return coordinator.distribute_tasks(tasks, num_workers)
