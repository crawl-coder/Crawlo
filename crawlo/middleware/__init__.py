#!/usr/bin/python
# -*- coding:UTF-8 -*-
from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    from crawlo import Request, Response


class BaseMiddleware:
    """中间件基类
    
    定义了中间件的标准接口，所有自定义中间件都应该继承此类。
    
    中间件处理流程：
    1. process_request: 请求发送前处理
    2. process_response: 响应接收后处理
    3. process_exception: 异常发生时处理
    """
    
    def process_request(
        self, 
        request: 'Request', 
        spider
    ) -> Optional[Union['Request', 'Response']]:
        """处理请求
        
        Args:
            request: 待处理的请求对象
            spider: 当前爬虫实例
            
        Returns:
            None: 继续处理
            Request: 替换原请求
            Response: 跳过下载，直接返回响应
        """
        pass

    def process_response(
        self, 
        request: 'Request', 
        response: 'Response', 
        spider
    ) -> Union['Request', 'Response']:
        """处理响应
        
        Args:
            request: 原始请求对象
            response: 接收到的响应对象
            spider: 当前爬虫实例
            
        Returns:
            Request: 重新发起请求
            Response: 返回响应（可能是修改后的）
        """
        return response

    def process_exception(
        self, 
        request: 'Request', 
        exp: Exception, 
        spider
    ) -> Optional[Union['Request', 'Response']]:
        """处理异常
        
        Args:
            request: 发生异常的请求
            exp: 捕获的异常对象
            spider: 当前爬虫实例
            
        Returns:
            None: 继续传递异常
            Request: 重新发起请求
            Response: 返回响应
        """
        pass

    @classmethod
    def create_instance(cls, crawler):
        """创建中间件实例
        
        Args:
            crawler: Crawler实例，包含settings等配置
            
        Returns:
            中间件实例
        """
        return cls()
