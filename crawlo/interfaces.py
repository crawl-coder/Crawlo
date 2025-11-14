from abc import ABC, abstractmethod
from typing import List, Type, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from crawlo.spider import Spider
    from crawlo.network.request import Request


class ISpiderLoader(Protocol):
    """Spider loader interface"""
    
    @abstractmethod
    def load(self, spider_name: str) -> Type['Spider']:
        """
        Load a spider by name
        
        Args:
            spider_name: 爬虫名称
            
        Returns:
            Type[Spider]: 爬虫类
        """
        pass
    
    @abstractmethod
    def list(self) -> List[str]:
        """
        List all available spider names
        
        Returns:
            List[str]: 爬虫名称列表
        """
        pass
    
    @abstractmethod
    def find_by_request(self, request: 'Request') -> List[str]:
        """
        Find spider names that can handle the given request
        
        Args:
            request: 请求对象
            
        Returns:
            List[str]: 能处理该请求的爬虫名称列表
        """
        pass