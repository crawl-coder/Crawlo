#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
检查点管理器
负责爬取状态的保存与恢复，支持 Ctrl+C 优雅关闭后从断点续爬。

核心流程：
1. Ctrl+C 时：保存内存队列中的待处理请求 + 去重指纹 + 统计信息
2. 重启时：检测检查点文件，加载恢复队列和指纹，跳过已完成的请求

注意：Redis 队列模式下请求天然持久化（已在 Redis 中），
检查点主要解决单机模式（Memory 队列）的持久化问题。
"""
import json
import time
from typing import Any, Dict, List, Optional, Set

from crawlo.logging import get_logger
from crawlo.utils.misc import safe_get_config
from crawlo.checkpoint.storage import BaseStorage, JsonStorage, SqliteStorage


class CheckpointManager:
    """检查点管理器 - 负责爬取状态的保存与恢复"""

    def __init__(self, spider_name: str, settings: Any = None):
        """
        初始化检查点管理器

        Args:
            spider_name: 爬虫名称
            settings: 配置对象
        """
        self.spider_name = spider_name
        self.settings = settings
        self.logger = get_logger('CheckpointManager')

        # 读取配置
        storage_type = safe_get_config(settings, 'CHECKPOINT_STORAGE', 'json', str)
        checkpoint_dir = safe_get_config(settings, 'CHECKPOINT_DIR', None, str)
        project_name = safe_get_config(settings, 'PROJECT_NAME', 'default', str)

        # 创建存储后端
        self.storage: BaseStorage = self._create_storage(
            storage_type=storage_type,
            spider_name=spider_name,
            project_name=project_name,
            checkpoint_dir=checkpoint_dir,
        )

    def _create_storage(
        self,
        storage_type: str,
        spider_name: str,
        project_name: str,
        checkpoint_dir: Optional[str],
    ) -> BaseStorage:
        """根据配置创建存储后端"""
        if storage_type == 'sqlite':
            return SqliteStorage(
                spider_name=spider_name,
                project_name=project_name,
                checkpoint_dir=checkpoint_dir,
            )
        else:
            # 默认使用 JSON
            return JsonStorage(
                spider_name=spider_name,
                project_name=project_name,
                checkpoint_dir=checkpoint_dir,
            )

    @property
    def enabled(self) -> bool:
        """检查点是否启用（始终返回 True）"""
        return True

    async def save(self, scheduler: Any = None, stats: Any = None) -> bool:
        """保存检查点：队列请求 + 去重指纹 + 统计信息

        Args:
            scheduler: 调度器实例
            stats: 统计收集器实例

        Returns:
            bool: 是否保存成功
        """
        try:
            # 1. 提取待处理请求
            requests_data = await self._extract_pending_requests(scheduler)

            # 2. 提取去重指纹
            fingerprints = self._extract_fingerprints(scheduler)

            # 3. 收集统计信息
            stats_data = self._extract_stats(stats)

            # 4. 获取项目名称
            project_name = safe_get_config(self.settings, 'PROJECT_NAME', 'default', str)

            # 5. 写入存储
            data = {
                'project_name': project_name,
                'spider_name': self.spider_name,
                'pending_count': len(requests_data),
                'requests': requests_data,
                'fingerprints': fingerprints,
                'stats': stats_data,
            }

            success = self.storage.save(data)

            if success:
                self.logger.info(
                    f"Checkpoint saved: {len(requests_data)} pending requests, "
                    f"{len(fingerprints)} fingerprints"
                )
            return success

        except Exception as e:
            self.logger.error(f"Failed to save checkpoint: {e}")
            return False

    async def load(self) -> Optional[Dict[str, Any]]:
        """加载检查点

        Returns:
            dict: 包含 requests, fingerprints, stats 的字典，无检查点时返回 None
        """
        try:
            data = self.storage.load()
            if data:
                self.logger.info(
                    f"Checkpoint loaded: {len(data.get('requests', []))} pending requests, "
                    f"{len(data.get('fingerprints', set()))} fingerprints, "
                    f"saved at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data.get('saved_at', 0)))}"
                )
            return data
        except Exception as e:
            self.logger.error(f"Failed to load checkpoint: {e}")
            return None

    async def has_checkpoint(self) -> bool:
        """是否存在有效检查点"""
        return self.storage.exists()

    async def clear(self) -> bool:
        """清除检查点（爬取正常完成后调用）

        Returns:
            bool: 是否清除成功
        """
        try:
            success = self.storage.clear()
            if success:
                self.logger.debug("Checkpoint cleared")
            return success
        except Exception as e:
            self.logger.error(f"Failed to clear checkpoint: {e}")
            return False

    # ==================== 内部方法 ====================

    async def _extract_pending_requests(self, scheduler: Any) -> List[Dict[str, Any]]:
        """从调度器中提取所有待处理请求

        Args:
            scheduler: 调度器实例

        Returns:
            list: 序列化后的请求字典列表
        """
        if scheduler is None:
            return []

        requests_data = []

        try:
            queue_manager = getattr(scheduler, 'queue_manager', None)
            if queue_manager is None:
                return []

            # 获取队列大小
            queue_size = await queue_manager.size()
            if queue_size == 0:
                return []

            # 从队列中逐个取出请求并序列化
            extracted = []
            for _ in range(queue_size):
                try:
                    request = await queue_manager.get()
                    if request is None:
                        break
                    extracted.append(request)
                except Exception:
                    break

            # 序列化请求
            serializer = getattr(scheduler, 'request_serializer', None)
            for request in extracted:
                try:
                    # 清理请求以便序列化
                    if serializer:
                        serializer.prepare_for_serialization(request)

                    # 序列化为字典
                    req_dict = self._serialize_request(request)
                    if req_dict:
                        requests_data.append(req_dict)
                except Exception as e:
                    self.logger.debug(f"Failed to serialize request {getattr(request, 'url', '?')}: {e}")
                    # 尝试最简序列化
                    try:
                        requests_data.append({'url': str(getattr(request, 'url', ''))})
                    except Exception:
                        pass

            # 将取出的请求放回队列
            for request in extracted:
                try:
                    await queue_manager.put(request, priority=getattr(request, 'priority', 0))
                except Exception:
                    pass

        except Exception as e:
            self.logger.error(f"Failed to extract pending requests: {e}")

        return requests_data

    def _serialize_request(self, request: Any) -> Optional[Dict[str, Any]]:
        """将 Request 对象序列化为字典

        Args:
            request: Request 对象

        Returns:
            dict: 序列化后的字典
        """
        try:
            from crawlo.utils.request.request import request_to_dict
            return request_to_dict(request)
        except ImportError:
            pass

        # 手动序列化
        try:
            d = {
                'url': str(getattr(request, 'url', '')),
                'method': getattr(request, 'method', 'GET'),
                'headers': dict(getattr(request, 'headers', {})),
                'meta': dict(getattr(request, 'meta', {})),
                'priority': getattr(request, 'priority', 0),
                'dont_filter': getattr(request, 'dont_filter', False),
                'encoding': getattr(request, 'encoding', 'utf-8'),
            }

            # 可选字段
            for attr in ('body', 'cookies', 'timeout', 'proxy', 'callback', 'err_back'):
                val = getattr(request, attr, None)
                if val is not None:
                    if callable(val):
                        # callback/err_back 只保存函数路径
                        if hasattr(val, '__self__') and hasattr(val, '__name__'):
                            d[attr] = f"{val.__self__.__class__.__name__}.{val.__name__}"
                        elif hasattr(val, '__name__'):
                            d[attr] = val.__name__
                    else:
                        try:
                            json.dumps(val)  # 测试是否可序列化
                            d[attr] = val
                        except (TypeError, ValueError):
                            d[attr] = str(val)

            return d

        except Exception as e:
            self.logger.debug(f"Manual serialization failed: {e}")
            return None

    def _extract_fingerprints(self, scheduler: Any) -> Set[str]:
        """从去重过滤器中提取指纹集合

        Args:
            scheduler: 调度器实例

        Returns:
            set: 指纹字符串集合
        """
        if scheduler is None:
            return set()

        try:
            dupe_filter = getattr(scheduler, 'dupe_filter', None)
            if dupe_filter is None:
                return set()

            # MemoryFilter：直接获取 fingerprints 属性
            if hasattr(dupe_filter, 'fingerprints'):
                fps = dupe_filter.fingerprints
                if isinstance(fps, set):
                    return fps.copy()

            # Redis 过滤器：无法直接提取（数据在 Redis 中），返回空集
            # Redis 过滤器天然持久化，不需要检查点保存指纹
            return set()

        except Exception as e:
            self.logger.debug(f"Failed to extract fingerprints: {e}")
            return set()

    def _extract_stats(self, stats: Any) -> Dict[str, Any]:
        """提取统计信息

        Args:
            stats: 统计收集器实例

        Returns:
            dict: 统计信息字典
        """
        if stats is None:
            return {}

        try:
            if hasattr(stats, 'get_stats'):
                return stats.get_stats()
            elif hasattr(stats, '_stats'):
                return dict(stats._stats)
            else:
                return {}
        except Exception as e:
            self.logger.debug(f"Failed to extract stats: {e}")
            return {}

    def restore_request(self, request_data: Dict[str, Any], spider: Any = None) -> Any:
        """从序列化数据恢复 Request 对象

        Args:
            request_data: 序列化的请求字典
            spider: 爬虫实例（用于恢复 callback）

        Returns:
            Request: 恢复后的请求对象
        """
        try:
            # 优先使用框架的 request_from_dict
            from crawlo.utils.request.request import request_from_dict
            request = request_from_dict(request_data, spider)

            # request_from_dict 不处理的部分，手动恢复
            for attr in ('dont_filter', 'timeout', 'proxy', 'priority'):
                if attr in request_data:
                    setattr(request, attr, request_data[attr])

            # 恢复 cookies（request_from_dict 不处理）
            if 'cookies' in request_data and request_data['cookies']:
                request.cookies = request_data['cookies']

            return request
        except ImportError:
            pass
        except Exception as e:
            self.logger.debug(f"request_from_dict failed: {e}, falling back to manual restore")

        # 手动恢复
        try:
            from crawlo.network.request import Request

            url = request_data.get('url', '')
            if not url:
                raise ValueError("No URL in request data")

            # 构建参数，过滤掉非 Request 构造参数
            request_kwargs = {
                'method': request_data.get('method', 'GET'),
                'headers': request_data.get('headers'),
                'meta': request_data.get('meta'),
                'priority': request_data.get('priority', 0),
                'dont_filter': request_data.get('dont_filter', False),
                'encoding': request_data.get('encoding', 'utf-8'),
            }

            # 可选字段
            if 'body' in request_data:
                request_kwargs['body'] = request_data['body']
            if 'cookies' in request_data:
                request_kwargs['cookies'] = request_data['cookies']
            if 'timeout' in request_data:
                request_kwargs['timeout'] = request_data['timeout']
            if 'proxy' in request_data:
                request_kwargs['proxy'] = request_data['proxy']

            # 移除 None 值
            request_kwargs = {k: v for k, v in request_kwargs.items() if v is not None}

            return Request(url=url, **request_kwargs)

        except Exception as e:
            self.logger.error(f"Failed to restore request: {e}")
            # 最后降级：只带 URL
            try:
                from crawlo.network.request import Request
                return Request(url=request_data.get('url', ''))
            except Exception:
                return None

    def restore_fingerprints(self, fingerprints: Set[str], scheduler: Any) -> bool:
        """恢复去重指纹到过滤器

        Args:
            fingerprints: 指纹集合
            scheduler: 调度器实例

        Returns:
            bool: 是否恢复成功
        """
        if not fingerprints or scheduler is None:
            return False

        try:
            dupe_filter = getattr(scheduler, 'dupe_filter', None)
            if dupe_filter is None:
                return False

            # MemoryFilter：直接添加指纹
            if hasattr(dupe_filter, 'fingerprints'):
                dupe_filter.fingerprints.update(fingerprints)
                self.logger.debug(f"Restored {len(fingerprints)} fingerprints")
                return True

            # Redis 过滤器不需要恢复（数据在 Redis 中）
            return False

        except Exception as e:
            self.logger.debug(f"Failed to restore fingerprints: {e}")
            return False
