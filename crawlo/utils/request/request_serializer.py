#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Request 序列化工具类
负责处理 Request 对象的序列化前清理工作，解决 logger 等不可序列化对象的问题
"""
import gc
import logging
import pickle
try:
    import msgpack
    MSGPACK_AVAILABLE = True
except ImportError:
    MSGPACK_AVAILABLE = False
from typing import Any, Dict, Optional, TYPE_CHECKING, Literal, Union

if TYPE_CHECKING:
    from crawlo.network.request import Request
    from crawlo.spider import Spider

from crawlo.logging import get_logger


class RequestSerializer:
    """Request 序列化工具类"""
    
    def __init__(self, serialization_format: Literal['pickle', 'msgpack'] = 'pickle') -> None:
        """初始化序列化工具类
        
        Args:
            serialization_format: 序列化格式，'pickle' 或 'msgpack'
        """
        # 延迟初始化logger避免循环依赖
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
        移除不可序列化的属性，保存必要信息用于恢复
        
        Args:
            request: 要序列化的请求对象
            
        Returns:
            Request: 清理后的请求对象
        """
        self.logger.debug(f"Preparing request for {self.serialization_format} serialization: {request.url}" if hasattr(request, 'url') else f"Preparing request for {self.serialization_format} serialization")
        try:
            # 处理 callback
            self._handle_callback(request)
            
            # 清理 meta 中的 logger
            if hasattr(request, '_meta') and request._meta:
                self._clean_dict_recursive(request._meta)
            
            # 清理 cb_kwargs 中的 logger
            if hasattr(request, 'cb_kwargs') and request.cb_kwargs:
                self._clean_dict_recursive(request.cb_kwargs)
            
            # 清理其他可能的 logger 引用
            for attr_name in ['headers', 'cookies']:
                if hasattr(request, attr_name):
                    attr_value = getattr(request, attr_name)
                    if isinstance(attr_value, dict):
                        self._clean_dict_recursive(attr_value)
            
            # 特别处理可能包含RLock的对象
            self._clean_rlock_objects(request)
            
            # 最终验证
            if not self._test_serialization(request):
                self.logger.warning("常规清理无效，使用深度清理")
                request = self._deep_clean_request(request)
                
            return request
            
        except Exception as e:
            self.logger.error(f"Request 序列化准备失败: {e}")
            # 最后的保险：重建 Request
            return self._rebuild_clean_request(request)
    
    def restore_after_deserialization(self, request: 'Request', spider: Optional['Spider'] = None) -> 'Request':
        """
        反序列化后恢复 Request 对象
        恢复 callback 等必要信息
        
        Args:
            request: 反序列化后的请求对象
            spider: 爬虫实例
            
        Returns:
            Request: 恢复后的请求对象
        """
        if not request:
            return request
            
        # 恢复 callback
        if hasattr(request, '_meta') and '_callback_info' in request._meta:
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
        处理 callback 相关的清理
        
        Args:
            request: 请求对象
        """
        if hasattr(request, 'callback') and request.callback is not None:
            callback = request.callback
            
            # 如果是绑定方法，保存信息并移除引用
            # 检查是否为绑定方法（有__self__属性）而不是普通函数
            if hasattr(callback, '__self__') and hasattr(callback, '__name__'):
                try:
                    # 安全地访问 __self__ 属性
                    spider_instance = getattr(callback, '__self__', None)
                    if spider_instance is not None:
                        # 保存 callback 信息
                        if not hasattr(request, '_meta') or request._meta is None:
                            request._meta = {}
                        request._meta['_callback_info'] = {
                            'spider_class': spider_instance.__class__.__name__,
                            'method_name': callback.__name__
                        }
                        
                        # 移除 callback 引用
                        request.callback = None
                except AttributeError:
                    # 如果无法访问 __self__，则跳过
                    pass
    
    def _clean_dict_recursive(self, data: Dict[str, Any], depth: int = 0) -> None:
        """
        递归清理字典中的 logger 和 RLock 对象
        
        Args:
            data: 要清理的数据字典
            depth: 递归深度
        """
        import threading
        
        if depth > 5 or not isinstance(data, dict):
            return
        
        keys_to_remove = []
        for key, value in list(data.items()):
            if isinstance(value, logging.Logger):
                keys_to_remove.append(key)
            elif isinstance(value, type(threading.RLock())) or \
                 (hasattr(value, '__class__') and value.__class__.__name__ and 'RLock' in value.__class__.__name__):
                keys_to_remove.append(key)
            elif isinstance(key, str) and 'logger' in key.lower():
                keys_to_remove.append(key)
            elif isinstance(value, dict):
                self._clean_dict_recursive(value, depth + 1)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    if isinstance(item, dict):
                        self._clean_dict_recursive(item, depth + 1)
        
        for key in keys_to_remove:
            data[key] = None  # 将RLock对象设置为None而不是删除键
    
    def _clean_rlock_objects(self, request: 'Request') -> None:
        """
        清理可能包含RLock的对象
        
        Args:
            request: 请求对象
        """
        import threading
        
        # 清理可能包含RLock的属性
        rlock_attrs = ['_cookies_lock', '_headers_lock', '__dict__', '__weakref__']
        
        # 遍历请求对象的所有属性
        for attr_name in dir(request):
            try:
                if attr_name.startswith('_') or attr_name in ['headers', 'cookies']:
                    attr_value = getattr(request, attr_name, None)
                    if attr_value is not None:
                        # 检查是否为RLock对象
                        if isinstance(attr_value, threading.RLock) or \
                           (hasattr(attr_value, '__class__') and attr_value.__class__.__name__ and 'RLock' in attr_value.__class__.__name__):
                            try:
                                setattr(request, attr_name, None)
                                self.logger.debug(f"清理RLock对象: {attr_name}")
                            except (AttributeError, TypeError):
                                pass
                        # 递归清理字典中的RLock对象
                        elif isinstance(attr_value, dict):
                            self._clean_dict_rlock(attr_value)
                        # 递归清理对象属性中的RLock
                        elif hasattr(attr_value, '__dict__'):
                            self._clean_object_rlock(attr_value)
            except Exception:
                # 忽略访问属性时的异常
                pass
    
    def _clean_dict_rlock(self, data: Dict[str, Any]) -> None:
        """
        清理字典中的RLock对象
        
        Args:
            data: 数据字典
        """
        import threading
        
        if not isinstance(data, dict):
            return
            
        keys_to_clean = []
        for key, value in data.items():
            if isinstance(value, threading.RLock) or \
               (hasattr(value, '__class__') and value.__class__.__name__ and 'RLock' in value.__class__.__name__):
                keys_to_clean.append(key)
            elif isinstance(value, dict):
                self._clean_dict_rlock(value)
            elif hasattr(value, '__dict__'):
                self._clean_object_rlock(value)
                
        for key in keys_to_clean:
            try:
                data[key] = None
                self.logger.debug(f"清理字典中的RLock对象: {key}")
            except (AttributeError, TypeError):
                pass

    def _clean_object_rlock(self, obj: Any) -> None:
        """
        清理对象属性中的RLock对象
        
        Args:
            obj: 对象实例
        """
        import threading
        
        if not hasattr(obj, '__dict__'):
            return
            
        attrs_to_clean = []
        for attr_name, attr_value in obj.__dict__.items():
            if isinstance(attr_value, threading.RLock) or \
               (hasattr(attr_value, '__class__') and attr_value.__class__.__name__ and 'RLock' in attr_value.__class__.__name__):
                attrs_to_clean.append(attr_name)
            elif isinstance(attr_value, dict):
                self._clean_dict_rlock(attr_value)
            elif hasattr(attr_value, '__dict__'):
                self._clean_object_rlock(attr_value)
                
        for attr_name in attrs_to_clean:
            try:
                setattr(obj, attr_name, None)
                self.logger.debug(f"清理对象属性中的RLock对象: {attr_name}")
            except (AttributeError, TypeError):
                pass

    def _test_serialization(self, request: 'Request') -> bool:
        """
        测试是否可以序列化
        
        Args:
            request: 请求对象
            
        Returns:
            bool: 是否可以序列化
        """
        try:
            if self.serialization_format == 'msgpack':
                if MSGPACK_AVAILABLE:
                    # msgpack不能序列化所有对象，所以先尝试pickle
                    pickle.dumps(request)
                    return True
            else:
                pickle.dumps(request)
                return True
        except Exception:
            return False
    
    def _deep_clean_request(self, request: 'Request') -> 'Request':
        """
        深度清理 Request 对象
        
        Args:
            request: 请求对象
            
        Returns:
            Request: 清理后的请求对象
        """
        import logging
        import threading
        
        def recursive_clean(target: Any, visited: Optional[set] = None, depth: int = 0) -> None:
            """递归清理对象"""
            if depth > 5 or not target:
                return
            if visited is None:
                visited = set()
                
            obj_id = id(target)
            if obj_id in visited:
                return
            visited.add(obj_id)
            
            # 处理对象属性
            if hasattr(target, '__dict__'):
                attrs_to_clean = []
                for attr_name, attr_value in list(target.__dict__.items()):
                    # 清理Logger对象
                    if isinstance(attr_value, logging.Logger):
                        attrs_to_clean.append(attr_name)
                    # 清理RLock对象
                    elif isinstance(attr_value, threading.RLock) or \
                         (hasattr(attr_value, '__class__') and 'RLock' in (attr_value.__class__.__name__ or '')):
                        attrs_to_clean.append(attr_name)
                    elif isinstance(attr_name, str) and 'logger' in attr_name.lower():
                        attrs_to_clean.append(attr_name)
                    elif hasattr(attr_value, '__dict__'):
                        recursive_clean(attr_value, visited, depth + 1)
                    elif isinstance(attr_value, dict):
                        recursive_clean(attr_value, visited, depth + 1)
                
                for attr_name in attrs_to_clean:
                    try:
                        setattr(target, attr_name, None)
                    except (AttributeError, TypeError):
                        pass
            
            # 处理字典
            elif isinstance(target, dict):
                keys_to_clean = []
                for key, value in list(target.items()):
                    # 清理Logger对象
                    if isinstance(value, logging.Logger):
                        keys_to_clean.append(key)
                    # 清理RLock对象
                    elif isinstance(value, threading.RLock) or \
                         (hasattr(value, '__class__') and 'RLock' in (value.__class__.__name__ or '')):
                        keys_to_clean.append(key)
                    elif isinstance(key, str) and 'logger' in key.lower():
                        keys_to_clean.append(key)
                    elif hasattr(value, '__dict__'):
                        recursive_clean(value, visited, depth + 1)
                    elif isinstance(value, dict):
                        recursive_clean(value, visited, depth + 1)
                    elif isinstance(value, (list, tuple)):
                        for item in value:
                            recursive_clean(item, visited, depth + 1)
                
                for key in keys_to_clean:
                    try:
                        target[key] = None
                    except (AttributeError, TypeError):
                        pass
        
        recursive_clean(request)
        gc.collect()
        return request
    
    def _rebuild_clean_request(self, original_request: 'Request') -> 'Request':
        """
        重建一个干净的 Request 对象
        
        Args:
            original_request: 原始请求对象
            
        Returns:
            Request: 重建后的请求对象
        """
        from crawlo.network.request import Request
        
        try:
            # 提取安全的属性
            safe_meta = {}
            if hasattr(original_request, '_meta') and original_request._meta:
                for key, value in original_request._meta.items():
                    if not isinstance(value, logging.Logger):
                        try:
                            pickle.dumps(value)
                            safe_meta[key] = value
                        except Exception:
                            try:
                                safe_meta[key] = str(value)
                            except Exception:
                                continue
            
            # 安全地获取其他属性
            safe_headers = {}
            if hasattr(original_request, 'headers') and original_request.headers:
                for k, v in original_request.headers.items():
                    try:
                        safe_headers[str(k)] = str(v)
                    except Exception:
                        continue
            
            # 创建干净的 Request
            clean_request = Request(
                url=str(original_request.url),
                method=getattr(original_request, 'method', 'GET'),
                headers=safe_headers,
                meta=safe_meta,
                priority=getattr(original_request, 'priority', 0),  # 修正优先级处理，不需要负号
                dont_filter=getattr(original_request, 'dont_filter', False),
                timeout=getattr(original_request, 'timeout', None),
                encoding=getattr(original_request, 'encoding', 'utf-8')
            )
            
            # 验证新 Request 可以序列化
            try:
                if self.serialization_format == 'msgpack':
                    if MSGPACK_AVAILABLE:
                        # msgpack不能直接序列化Request对象，所以先用pickle测试
                        pickle.dumps(clean_request)
                    else:
                        pickle.dumps(clean_request)
                else:
                    pickle.dumps(clean_request)
                return clean_request
            except Exception:
                # 如果仍然无法序列化，创建最简化的请求
                minimal_request = Request(url=str(original_request.url))
                return minimal_request
            
        except Exception as e:
            self.logger.error(f"重建 Request 失败: {e}")
            # 最简单的 fallback
            from crawlo.network.request import Request
            return Request(url=str(original_request.url))