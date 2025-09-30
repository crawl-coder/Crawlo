from abc import ABC, abstractmethod
from typing import List, Type, Protocol

from crawlo.spider import Spider
from crawlo.network.request import Request


class ISpiderLoader(Protocol):
    """Spider loader interface"""
    
    @abstractmethod
    def load(self, spider_name: str) -> Type[Spider]:
        """Load a spider by name"""
        pass
    
    @abstractmethod
    def list(self) -> List[str]:
        """List all available spider names"""
        pass
    
    @abstractmethod
    def find_by_request(self, request: Request) -> List[str]:
        """Find spider names that can handle the given request"""
        pass