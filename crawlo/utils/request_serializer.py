#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Request 序列化工具类
负责处理 Request 对象的序列化前清理工作，解决 logger 等不可序列化对象的问题
"""
import logging
import pickle
import gc
from typing import Any, Dict

from crawlo.utils.log import get_logger


class RequestSerializer:
    """Request 序列化工具类"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    def prepare_for_serialization(self, request):
        """
        为序列化准备 Request 对象
        移除不可序列化的属性，保存必要信息用于恢复
        """
        try:
            # 处理 callback
            self._handle_callback(request)
            
            # 清理 meta 中的 logger
            if hasattr(request, 'meta') and request.meta:
                self._clean_dict_recursive(request.meta)
            
            # 清理 cb_kwargs 中的 logger
            if hasattr(request, 'cb_kwargs') and request.cb_kwargs:
                self._clean_dict_recursive(request.cb_kwargs)
            
            # 清理其他可能的 logger 引用
            for attr_name in ['headers', 'cookies']:
                if hasattr(request, attr_name):
                    attr_value = getattr(request, attr_name)
                    if isinstance(attr_value, dict):
                        self._clean_dict_recursive(attr_value)
            
            # 最终验证
            if not self._test_serialization(request):
                self.logger.warning("⚠️ 常规清理无效，使用深度清理")
                request = self._deep_clean_request(request)
                
            return request
            
        except Exception as e:
            self.logger.error(f"❌ Request 序列化准备失败: {e}")
            # 最后的保险：重建 Request
            return self._rebuild_clean_request(request)
    
    def restore_after_deserialization(self, request, spider=None):
        """
        反序列化后恢复 Request 对象
        恢复 callback 等必要信息
        """
        if not request:
            return request
            
        # 恢复 callback
        if hasattr(request, 'meta') and '_callback_info' in request.meta:
            callback_info = request.meta.pop('_callback_info')
            
            if spider:
                spider_class_name = callback_info.get('spider_class')
                method_name = callback_info.get('method_name')
                
                if (spider.__class__.__name__ == spider_class_name and 
                    hasattr(spider, method_name)):
                    request.callback = getattr(spider, method_name)
                    
                    # 确保 spider 有有效的 logger
                    if not hasattr(spider, 'logger') or spider.logger is None:
                        spider.logger = get_logger(spider.name or spider.__class__.__name__)
        
        return request
    
    def _handle_callback(self, request):
        """处理 callback 相关的清理"""
        if hasattr(request, 'callback') and request.callback is not None:
            callback = request.callback
            
            # 如果是绑定方法，保存信息并移除引用
            if hasattr(callback, '__self__') and hasattr(callback, '__name__'):
                spider_instance = callback.__self__
                
                # 保存 callback 信息
                if not hasattr(request, 'meta') or request.meta is None:
                    request.meta = {}
                request.meta['_callback_info'] = {
                    'spider_class': spider_instance.__class__.__name__,
                    'method_name': callback.__name__
                }
                
                # 移除 callback 引用
                request.callback = None
    
    def _clean_dict_recursive(self, data, depth=0):
        """递归清理字典中的 logger"""
        if depth > 5 or not isinstance(data, dict):
            return
        
        keys_to_remove = []
        for key, value in list(data.items()):
            if isinstance(value, logging.Logger):
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
            data.pop(key, None)
    
    def _test_serialization(self, request):
        """测试是否可以序列化"""
        try:
            pickle.dumps(request)
            return True
        except Exception:
            return False
    
    def _deep_clean_request(self, request):
        """深度清理 Request 对象"""
        import logging
        
        def recursive_clean(target, visited=None, depth=0):
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
                    if isinstance(attr_value, logging.Logger):
                        attrs_to_clean.append(attr_name)
                    elif isinstance(attr_name, str) and 'logger' in attr_name.lower():
                        attrs_to_clean.append(attr_name)
                    elif hasattr(attr_value, '__dict__'):
                        recursive_clean(attr_value, visited, depth + 1)
                
                for attr_name in attrs_to_clean:
                    try:
                        setattr(target, attr_name, None)
                    except (AttributeError, TypeError):
                        pass
            
            # 处理字典
            elif isinstance(target, dict):
                self._clean_dict_recursive(target, depth)
        
        recursive_clean(request)
        gc.collect()
        return request
    
    def _rebuild_clean_request(self, original_request):
        """重建一个干净的 Request 对象"""
        from crawlo.network.request import Request
        
        try:
            # 提取安全的属性
            safe_meta = {}
            if hasattr(original_request, 'meta') and original_request.meta:
                for key, value in original_request.meta.items():
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
                priority=-getattr(original_request, 'priority', 0),
                dont_filter=getattr(original_request, 'dont_filter', False),
                timeout=getattr(original_request, 'timeout', None),
                encoding=getattr(original_request, 'encoding', 'utf-8')
            )
            
            # 验证新 Request 可以序列化
            pickle.dumps(clean_request)
            return clean_request
            
        except Exception as e:
            self.logger.error(f"❌ 重建 Request 失败: {e}")
            # 最简单的 fallback
            from crawlo.network.request import Request
            return Request(url=str(original_request.url))