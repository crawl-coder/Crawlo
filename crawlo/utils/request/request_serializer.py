#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Request 序列化工具类
负责处理 Request 对象的序列化前清理工作，解决 logger 等不可序列化对象的问题

设计参考：Scrapy 的 request_to_dict / request_from_dict 机制
"""
import gc
import logging
import pickle
import threading
from typing import Any, Dict, Optional, Set, TYPE_CHECKING, Literal

try:
    import msgpack
    MSGPACK_AVAILABLE = True
except ImportError:
    MSGPACK_AVAILABLE = False

if TYPE_CHECKING:
    from crawlo.network.request import Request
    from crawlo.spider import Spider

from crawlo.logging import get_logger


# 不可序列化的类型白名单
UNSERIALIZABLE_TYPES = (logging.Logger,)
RLockType = type(threading.RLock())


class RequestSerializer:
    """Request 序列化工具类"""
    
    def __init__(self, serialization_format: Literal['pickle', 'msgpack'] = 'pickle') -> None:
        """初始化序列化工具类
        
        Args:
            serialization_format: 序列化格式，'pickle' 或 'msgpack'
        """
        self._logger = None
        self.serialization_format = serialization_format
        
        # 验证序列化格式支持
        if serialization_format == 'msgpack' and not MSGPACK_AVAILABLE:
            self.logger.warning("msgpack not available, falling back to pickle")
            self.serialization_format = 'pickle'
    
    @property
    def logger(self):
        """延迟初始化logger"""
        if self._logger is None:
            self._logger = get_logger(self.__class__.__name__)
        return self._logger
    
    def prepare_for_serialization(self, request: 'Request') -> 'Request':
        """
        为序列化准备 Request 对象
        
        清理策略（三层防御）：
        1. 快速路径：清理 callback + meta 后直接测试
        2. 深度清理：递归清除所有不可序列化对象
        3. 重建兜底：从安全属性重建 Request
        
        Args:
            request: 要序列化的请求对象
            
        Returns:
            Request: 清理后的请求对象
        """
        self.logger.debug(f"Preparing request for serialization: {request.url}")
        try:
            # 第 1 层：常规清理
            self._handle_callback(request)
            self._clean_meta_and_kwargs(request)
            
            if self._can_serialize(request):
                return request
            
            # 第 2 层：深度清理
            self.logger.warning("常规清理无效，使用深度清理")
            request = self._deep_clean_request(request)
            
            if self._can_serialize(request):
                return request
            
            # 第 3 层：重建兜底
            self.logger.warning("深度清理无效，重建 Request")
            return self._rebuild_clean_request(request)
            
        except Exception as e:
            self.logger.error(f"Request 序列化准备失败: {e}")
            return self._rebuild_clean_request(request)
    
    def restore_after_deserialization(self, request: 'Request', spider: Optional['Spider'] = None) -> 'Request':
        """
        反序列化后恢复 Request 对象
        
        Args:
            request: 反序列化后的请求对象
            spider: 爬虫实例
            
        Returns:
            Request: 恢复后的请求对象
        """
        if not request:
            return request
            
        # 恢复 callback
        if hasattr(request, '_meta') and request._meta and '_callback_info' in request._meta:
            callback_info = request._meta.pop('_callback_info')
            
            if spider:
                spider_class_name = callback_info.get('spider_class')
                method_name = callback_info.get('method_name')
                
                if (spider.__class__.__name__ == spider_class_name and 
                    hasattr(spider, method_name)):
                    request.callback = getattr(spider, method_name)
                    
                    # 确保 spider 有有效的 logger
                    if not hasattr(spider, '_logger') or spider._logger is None:
                        spider._logger = get_logger(spider.name or spider.__class__.__name__)
        
        return request
    
    def _handle_callback(self, request: 'Request') -> None:
        """
        处理 callback：保存信息到 meta 并移除引用
        
        Args:
            request: 请求对象
        """
        if hasattr(request, 'callback') and request.callback is not None:
            callback = request.callback
            
            # 仅处理绑定方法（有 __self__ 和 __name__）
            if hasattr(callback, '__self__') and hasattr(callback, '__name__'):
                try:
                    spider_instance = getattr(callback, '__self__', None)
                    if spider_instance is not None:
                        if not hasattr(request, '_meta') or request._meta is None:
                            request._meta = {}
                        request._meta['_callback_info'] = {
                            'spider_class': spider_instance.__class__.__name__,
                            'method_name': callback.__name__
                        }
                        request.callback = None
                except AttributeError:
                    pass
    
    def _clean_meta_and_kwargs(self, request: 'Request') -> None:
        """
        清理 meta 和 cb_kwargs 中的不可序列化对象
        
        Args:
            request: 请求对象
        """
        for attr_name in ['_meta', 'cb_kwargs']:
            if hasattr(request, attr_name):
                attr_value = getattr(request, attr_name)
                if isinstance(attr_value, dict):
                    self._clean_dict(attr_value)
    
    def _can_serialize(self, request: 'Request') -> bool:
        """
        测试 Request 是否可以序列化
        
        Args:
            request: 请求对象
            
        Returns:
            bool: 是否可以序列化
        """
        try:
            if self.serialization_format == 'msgpack' and MSGPACK_AVAILABLE:
                pickle.dumps(request)
            else:
                pickle.dumps(request)
            return True
        except Exception:
            return False
    
    def _clean_dict(self, data: Dict[str, Any], depth: int = 0, visited: Optional[Set[int]] = None) -> None:
        """
        递归清理字典中的不可序列化对象
        
        Args:
            data: 要清理的数据字典
            depth: 递归深度
            visited: 已访问对象 ID 集合（防循环引用）
        """
        if depth > 5 or not isinstance(data, dict):
            return
        
        if visited is None:
            visited = set()
        
        obj_id = id(data)
        if obj_id in visited:
            return
        visited.add(obj_id)
        
        keys_to_clean = []
        for key, value in list(data.items()):
            if self._is_unserializable(value):
                keys_to_clean.append(key)
            elif isinstance(value, dict):
                self._clean_dict(value, depth + 1, visited)
            elif hasattr(value, '__dict__') or hasattr(value, '__slots__'):
                self._clean_object(value, visited, depth + 1)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    if isinstance(item, dict):
                        self._clean_dict(item, depth + 1, visited)
                    elif hasattr(item, '__dict__') or hasattr(item, '__slots__'):
                        self._clean_object(item, visited, depth + 1)
        
        for key in keys_to_clean:
            try:
                data[key] = None
            except (AttributeError, TypeError):
                pass
    
    def _clean_object(self, obj: Any, visited: Optional[Set[int]] = None, depth: int = 0) -> None:
        """
        递归清理对象中的不可序列化属性（支持 __dict__ 和 __slots__）
        
        Args:
            obj: 对象实例
            visited: 已访问对象 ID 集合
            depth: 递归深度
        """
        if depth > 5 or not obj:
            return
        
        if visited is None:
            visited = set()
        
        obj_id = id(obj)
        if obj_id in visited:
            return
        visited.add(obj_id)
        
        # 收集所有属性名（__dict__ + __slots__）
        attr_names = set()
        if hasattr(obj, '__dict__'):
            attr_names.update(obj.__dict__.keys())
        if hasattr(obj, '__slots__'):
            for slot in obj.__slots__:
                try:
                    if hasattr(obj, slot):
                        attr_names.add(slot)
                except AttributeError:
                    pass
        
        if not attr_names:
            return
        
        attrs_to_clean = []
        for attr_name in attr_names:
            try:
                attr_value = getattr(obj, attr_name)
            except AttributeError:
                continue
            
            if self._is_unserializable(attr_value):
                attrs_to_clean.append(attr_name)
            elif isinstance(attr_value, dict):
                self._clean_dict(attr_value, depth + 1, visited)
            elif hasattr(attr_value, '__dict__') or hasattr(attr_value, '__slots__'):
                self._clean_object(attr_value, visited, depth + 1)
        
        for attr_name in attrs_to_clean:
            try:
                setattr(obj, attr_name, None)
            except (AttributeError, TypeError):
                pass
    
    def _deep_clean_request(self, request: 'Request') -> 'Request':
        """
        深度清理 Request 对象（使用统一的 _clean_object）
        
        Args:
            request: 请求对象
            
        Returns:
            Request: 清理后的请求对象
        """
        self._clean_object(request)
        gc.collect()
        return request
    
    def _rebuild_clean_request(self, original_request: 'Request') -> 'Request':
        """
        重建一个干净的 Request 对象（保留更多属性）
        
        Args:
            original_request: 原始请求对象
            
        Returns:
            Request: 重建后的请求对象
        """
        from crawlo.network.request import Request
        
        try:
            # 提取安全的 meta
            safe_meta = {}
            if hasattr(original_request, '_meta') and original_request._meta:
                for key, value in original_request._meta.items():
                    if not self._is_unserializable(value):
                        try:
                            pickle.dumps(value)
                            safe_meta[key] = value
                        except Exception:
                            try:
                                safe_meta[key] = str(value)
                            except Exception:
                                continue
            
            # 安全地提取 headers
            safe_headers = {}
            if hasattr(original_request, 'headers') and original_request.headers:
                for k, v in original_request.headers.items():
                    try:
                        safe_headers[str(k)] = str(v)
                    except Exception:
                        continue
            
            # 提取其他安全属性
            safe_kwargs = {}
            if hasattr(original_request, 'cb_kwargs') and original_request.cb_kwargs:
                for k, v in original_request.cb_kwargs.items():
                    if not self._is_unserializable(v):
                        try:
                            pickle.dumps(v)
                            safe_kwargs[k] = v
                        except Exception:
                            pass
            
            # 创建干净的 Request
            clean_request = Request(
                url=str(original_request.url),
                method=getattr(original_request, 'method', 'GET'),
                headers=safe_headers,
                meta=safe_meta,
                cb_kwargs=safe_kwargs,
                priority=getattr(original_request, 'priority', 0),
                dont_filter=getattr(original_request, 'dont_filter', False),
                timeout=getattr(original_request, 'timeout', None),
                encoding=getattr(original_request, 'encoding', 'utf-8'),
                cookies=getattr(original_request, 'cookies', None),
                body=getattr(original_request, 'body', None),
            )
            
            # 验证新 Request 可以序列化
            if self._can_serialize(clean_request):
                return clean_request
            
            # 如果仍然无法序列化，创建最简化的请求
            return Request(url=str(original_request.url))
            
        except Exception as e:
            self.logger.error(f"重建 Request 失败: {e}")
            from crawlo.network.request import Request
            return Request(url=str(original_request.url))
    
    @staticmethod
    def _is_unserializable(obj: Any) -> bool:
        """
        检查对象是否不可序列化
        
        Args:
            obj: 要检查的对象
            
        Returns:
            bool: 是否不可序列化
        """
        if obj is None:
            return False
        
        # 检查类型
        if isinstance(obj, UNSERIALIZABLE_TYPES):
            return True
        if isinstance(obj, RLockType):
            return True
        
        # 检查类名（精确匹配，避免误伤）
        class_name = getattr(obj, '__class__', None)
        if class_name:
            name = class_name.__name__ or ''
            # 仅匹配明确的 RLock/Logger 类型
            if name in ('RLock', 'Logger') or name.endswith(('RLock', 'Logger')):
                return True
        
        return False
