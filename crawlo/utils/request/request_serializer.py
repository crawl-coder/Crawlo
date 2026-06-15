#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Request Serialization Utility
Serializes Request objects using to_dict() / from_dict() methods.

Serialization support for Request objects
"""
from typing import Any, Dict, Optional, TYPE_CHECKING, Literal

try:
    import msgpack
    MSGPACK_AVAILABLE = True
except ImportError:
    MSGPACK_AVAILABLE = False

if TYPE_CHECKING:
    from crawlo.spider import Spider

from crawlo.network.request import Request
from crawlo.logging import get_logger


class RequestSerializer:
    """Request serializer using Request.to_dict() / from_dict()"""
    
    def __init__(self, serialization_format: Literal['pickle', 'msgpack'] = 'pickle') -> None:
        """
        Initialize request serializer.
        
        Args:
            serialization_format: Serialization format ('pickle' or 'msgpack')
        """
        self._logger = None
        self.serialization_format = serialization_format
        
        # Validate msgpack support
        if serialization_format == 'msgpack' and not MSGPACK_AVAILABLE:
            self.logger.warning("msgpack not available, falling back to pickle")
            self.serialization_format = 'pickle'
    
    @property
    def logger(self):
        """Lazy initialize logger"""
        if self._logger is None:
            self._logger = get_logger(self.__class__.__name__)
        return self._logger
    
    def prepare_for_serialization(self, request: 'Request') -> Dict[str, Any]:
        """
        Serialize Request to dict.
        
        Args:
            request: Request object to serialize
            
        Returns:
            Dict[str, Any]: Serialized request dictionary
        """
        self.logger.debug(f"Serializing request: {request.url}")
        return request.to_dict()
    
    def restore_after_deserialization(
        self, 
        data: Any, 
        spider: Optional['Spider'] = None
    ) -> 'Request':
        """
        Restore Request from serialized data.
        
        Args:
            data: Serialized dict OR already-deserialized Request object
            spider: Spider instance (for callback restoration)
            
        Returns:
            Request: Restored request object
        """
        # Request 已在顶部导入
        
        # If data is already a Request object, just restore callback
        if isinstance(data, Request):
            request = data
        else:
            # Deserialize from dict
            request = Request.from_dict(data)
        
        # Restore callback if spider provided
        if spider and hasattr(request, '_meta') and '_callback_info' in request._meta:
            callback_info = request._meta.pop('_callback_info')
            method_name = callback_info.get('method_name')
            
            if method_name and hasattr(spider, method_name):
                request.callback = getattr(spider, method_name)
        
        return request
