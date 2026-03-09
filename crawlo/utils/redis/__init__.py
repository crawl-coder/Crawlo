"""
Redis 工具模块
================
统一管理 Redis 配置、连接池和 Key 管理
"""

# 配置管理
from .config import (
    RedisConfig,
    generate_redis_url,
    parse_redis_url,
    create_redis_config,
    redis_url_to_config,
    config_to_redis_url,
)

# 连接池管理
from .pool import (
    RedisConnectionPool,
    get_redis_pool,
    close_all_pools,
    CrawloRedisManager,
    get_isolated_redis_pool,
    get_redis_manager,
)

# Key 管理
from .keys import (
    RedisKeyManager,
    RedisKeyValidator,
    validate_redis_key_naming,
    validate_multiple_redis_keys,
    get_redis_key_info,
    print_validation_report,
    create_redis_key_manager,
    get_redis_key_manager_from_settings,
)

__all__ = [
    # 配置
    'RedisConfig',
    'generate_redis_url',
    'parse_redis_url',
    'create_redis_config',
    'redis_url_to_config',
    'config_to_redis_url',
    # 连接池
    'RedisConnectionPool',
    'get_redis_pool',
    'close_all_pools',
    'CrawloRedisManager',
    'get_isolated_redis_pool',
    'get_redis_manager',
    # Key 管理
    'RedisKeyManager',
    'RedisKeyValidator',
    'validate_redis_key_naming',
    'validate_multiple_redis_keys',
    'get_redis_key_info',
    'print_validation_report',
    'create_redis_key_manager',
    'get_redis_key_manager_from_settings',
]
