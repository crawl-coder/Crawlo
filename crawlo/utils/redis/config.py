#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Redis 配置管理器
================
统一管理 Redis 连接配置、URL 生成和解析功能
"""
from typing import Dict, Any, Optional
from urllib.parse import urlparse, parse_qs


class RedisConfig:
    """统一的 Redis 配置类（支持单例模式）"""
    
    _instances: Dict[str, 'RedisConfig'] = {}
    _default_instance: Optional['RedisConfig'] = None
    
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 6379,
        password: Optional[str] = None,
        username: Optional[str] = None,
        db: int = 0,
        ssl: bool = False,
        **kwargs
    ):
        self.host = host
        self.port = port
        self.password = password
        self.username = username
        self.db = db
        self.ssl = ssl
        self.extra_params = kwargs
        # 创建唯一标识符用于单例管理
        self._instance_key = self._generate_key()
    
    def _generate_key(self) -> str:
        """生成配置的唯一标识符"""
        params = [
            self.host, 
            str(self.port), 
            self.username or '',
            self.password or '',
            str(self.db),
            str(self.ssl)
        ]
        return '|'.join(params)
    
    @classmethod
    def get_instance(
        cls,
        host: str = 'localhost',
        port: int = 6379,
        password: Optional[str] = None,
        username: Optional[str] = None,
        db: int = 0,
        ssl: bool = False,
        **kwargs
    ) -> 'RedisConfig':
        """
        获取 RedisConfig 单例实例
        
        Args:
            同 __init__ 参数
            
        Returns:
            RedisConfig: 配置实例
        """
        # 创建临时实例来生成key
        temp_config = cls(host, port, password, username, db, ssl, **kwargs)
        key = temp_config._instance_key
        
        # 检查是否已存在实例
        if key not in cls._instances:
            cls._instances[key] = temp_config
            # 如果是第一个实例，设为默认实例
            if cls._default_instance is None:
                cls._default_instance = temp_config
                
        return cls._instances[key]
    
    @classmethod
    def get_default(cls) -> Optional['RedisConfig']:
        """获取默认配置实例"""
        return cls._default_instance
    
    @classmethod
    def clear_instances(cls):
        """清理所有实例（主要用于测试）"""
        cls._instances.clear()
        cls._default_instance = None
    
    def to_url(self) -> str:
        """生成 Redis URL"""
        return generate_redis_url(
            host=self.host,
            port=self.port,
            password=self.password,
            username=self.username,
            db=self.db,
            ssl=self.ssl,
            **self.extra_params
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'host': self.host,
            'port': self.port,
            'password': self.password,
            'username': self.username,
            'db': self.db,
            'ssl': self.ssl,
            **self.extra_params
        }
    
    @classmethod
    def from_url(cls, url: str) -> 'RedisConfig':
        """从 Redis URL 解析配置"""
        parsed = urlparse(url)
        
        # 协议判断
        ssl = parsed.scheme == 'rediss'
        
        # 认证信息解析
        username = None
        password = None
        if parsed.username:
            username = parsed.username
        if parsed.password:
            password = parsed.password
        elif parsed.username and ':' in parsed.username:
            # 处理 user:pass@ 格式
            parts = parsed.username.split(':', 1)
            if len(parts) == 2:
                username, password = parts
        
        # 主机和端口
        host = parsed.hostname or 'localhost'
        port = parsed.port or 6379
        
        # 数据库
        db = 0
        if parsed.path and parsed.path.startswith('/'):
            try:
                db = int(parsed.path[1:]) if parsed.path[1:] else 0
            except ValueError:
                db = 0
        
        # 查询参数
        query_params = parse_qs(parsed.query)
        extra_params = {}
        for key, values in query_params.items():
            if values:
                # 只取第一个值，转换为适当类型
                value = values[0]
                if value.lower() in ('true', 'false'):
                    extra_params[key] = value.lower() == 'true'
                elif value.isdigit():
                    extra_params[key] = int(value)
                else:
                    try:
                        extra_params[key] = float(value)
                    except ValueError:
                        extra_params[key] = value
        
        return cls(
            host=host,
            port=port,
            password=password,
            username=username,
            db=db,
            ssl=ssl,
            **extra_params
        )


def generate_redis_url(
    host: str, 
    port: int, 
    password: Optional[str] = None,
    username: Optional[str] = None,
    db: int = 0,
    ssl: bool = False,
    **kwargs
) -> str:
    """
    生成完整的 Redis URL，支持用户名、SSL 等高级特性
    
    Args:
        host: Redis 主机地址
        port: Redis 端口
        password: Redis 密码（可选）
        username: Redis 用户名（可选）
        db: Redis 数据库编号
        ssl: 是否使用 SSL 连接
        **kwargs: 其他连接参数（如 socket_timeout 等）
        
    Returns:
        str: 完整的 Redis URL
    """
    # 构建认证部分
    auth_part = ""
    if username and password:
        auth_part = f"{username}:{password}@"
    elif password:
        auth_part = f":{password}@"
    elif username:
        auth_part = f"{username}@"
    
    # 协议部分
    protocol = "rediss" if ssl else "redis"
    
    # 基础 URL
    url = f"{protocol}://{auth_part}{host}:{port}/{db}"
    
    # 添加查询参数
    query_params = []
    for key, value in kwargs.items():
        if value is not None:
            query_params.append(f"{key}={value}")
    
    if query_params:
        url += "?" + "&".join(query_params)
    
    return url


def parse_redis_url(url: str) -> Dict[str, Any]:
    """
    解析 Redis URL 为配置字典
    
    Args:
        url: Redis URL
        
    Returns:
        Dict[str, Any]: 配置字典
    """
    return RedisConfig.from_url(url).to_dict()


# 便利函数
def create_redis_config(**kwargs) -> RedisConfig:
    """创建 Redis 配置对象的便利函数（支持单例）"""
    return RedisConfig.get_instance(**kwargs)


def redis_url_to_config(url: str) -> RedisConfig:
    """从 URL 创建 Redis 配置对象（支持单例）"""
    return RedisConfig.get_instance(**parse_redis_url(url))


def config_to_redis_url(config: RedisConfig) -> str:
    """从配置对象生成 Redis URL"""
    return config.to_url()