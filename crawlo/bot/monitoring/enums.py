# -*- coding: utf-8 -*-
"""
===================================
资源监控模板枚举
===================================

为资源监控模板提供枚举支持，方便用户通过 IDE 自动补全使用。
"""

from enum import Enum


class ResourceTemplate(Enum):
    """
    资源监控模板枚举
    
    提供所有资源监控相关模板的枚举值，便于 IDE 自动补全。
    """
    
    # MySQL 相关模板
    MYSQL_CONNECTION_POOL_MONITOR = "mysql_connection_pool_monitor"
    MYSQL_RESOURCE_LEAK_ALERT = "mysql_resource_leak_alert"
    MYSQL_SLOW_QUERY_ALERT = "mysql_slow_query_alert"
    MYSQL_DEADLOCK_ALERT = "mysql_deadlock_alert"
    
    # Redis 相关模板
    REDIS_MEMORY_MONITOR = "redis_memory_monitor"
    REDIS_CONNECTION_MONITOR = "redis_connection_monitor"
    REDIS_RESOURCE_LEAK_ALERT = "redis_resource_leak_alert"
    REDIS_KEY_TTL_MONITOR = "redis_key_ttl_monitor"
    
    # MongoDB 相关模板
    MONGODB_CONNECTION_MONITOR = "mongodb_connection_monitor"
    MONGODB_RESOURCE_LEAK_ALERT = "mongodb_resource_leak_alert"
    MONGODB_SLOW_OPERATION_ALERT = "mongodb_slow_operation_alert"
    MONGODB_INDEX_MISS_ALERT = "mongodb_index_miss_alert"
    
    # 通用资源监控模板
    GENERAL_RESOURCE_MONITOR = "general_resource_monitor"
    GENERAL_RESOURCE_LEAK_ALERT = "general_resource_leak_alert"


class ResourceMonitorVariable(Enum):
    """
    资源监控模板变量枚举
    
    提供资源监控相关模板变量的枚举值，便于 IDE 自动补全。
    """
    
    # MySQL 相关变量
    POOL_STATUS = "pool_status"
    ACTIVE_CONNECTIONS = "active_connections"
    IDLE_CONNECTIONS = "idle_connections"
    MAX_CONNECTIONS = "max_connections"
    WAITING_CONNECTIONS = "waiting_connections"
    CURRENT_CONNECTIONS = "current_connections"
    LEAK_TYPE = "leak_type"
    LEAK_TAG = "leak_tag"
    DISCOVERY_TIME = "discovery_time"
    IMPACT_SCOPE = "impact_scope"
    SQL_STATEMENT = "sql_statement"
    EXECUTION_TIME = "execution_time"
    AFFECTED_ROWS = "affected_rows"
    TARGET_TABLE = "target_table"
    QUERY_SOURCE = "query_source"
    TRANSACTION_ID = "transaction_id"
    WAIT_TIME = "wait_time"
    INVOLVED_TRANSACTIONS = "involved_transactions"
    LOCK_TYPE = "lock_type"
    AFFECTED_TABLE = "affected_table"
    
    # Redis 相关变量
    USED_MEMORY = "used_memory"
    MAX_MEMORY = "max_memory"
    MEMORY_USAGE_PERCENT = "memory_usage_percent"
    MEMORY_FRAGMENTATION_RATIO = "memory_fragmentation_ratio"
    HIT_RATE = "hit_rate"
    CONNECTED_CLIENTS = "connected_clients"
    MAX_CLIENTS = "max_clients"
    INPUT_KBPS = "input_kbps"
    OUTPUT_KBPS = "output_kbps"
    CURRENT_MEMORY_MB = "current_memory_mb"
    LEAK_TREND = "leak_trend"
    LEAK_IDENTIFIER = "leak_identifier"
    KEY_NAME = "key_name"
    TTL_SECONDS = "ttl_seconds"
    BUSINESS_TYPE = "business_type"
    KEY_SIZE_BYTES = "key_size_bytes"
    STORAGE_LOCATION = "storage_location"
    
    # MongoDB 相关变量
    CONNECTION_STATUS = "connection_status"
    AVAILABLE_CONNECTIONS = "available_connections"
    PENDING_REQUESTS = "pending_requests"
    MEMORY_USAGE_MB = "memory_usage_mb"
    OPERATION_TYPE = "operation_type"
    COLLECTION_NAME = "collection_name"
    DOCUMENTS_AFFECTED = "documents_affected"
    OPERATION_SOURCE = "operation_source"
    QUERY_CONDITION = "query_condition"
    SCANNED_DOCUMENTS = "scanned_documents"
    RETURNED_DOCUMENTS = "returned_documents"
    RECOMMENDED_INDEX = "recommended_index"
    
    # 通用变量
    RESOURCE_TYPE = "resource_type"
    CURRENT_VALUE = "current_value"
    THRESHOLD_VALUE = "threshold_value"
    USAGE_PERCENTAGE = "usage_percentage"
    TARGET_SERVICE = "target_service"
    TIMESTAMP = "timestamp"
    LEAK_DETAILS = "leak_details"
    GROWTH_TREND = "growth_trend"
    SEVERITY_LEVEL = "severity_level"
    AFFECTED_SERVICE = "affected_service"


class ResourceMonitorCategory(Enum):
    """
    资源监控分类枚举
    
    用于按类别组织资源监控模板。
    """
    
    MYSQL = "mysql"
    REDIS = "redis"
    MONGODB = "mongodb"
    GENERAL = "general"
    LEAK = "leak"


def get_mysql_resource_templates() -> list:
    """
    获取所有 MySQL 相关的资源监控模板枚举值
    
    Returns:
        MySQL 模板枚举值列表
    """
    return [
        ResourceTemplate.MYSQL_CONNECTION_POOL_MONITOR,
        ResourceTemplate.MYSQL_RESOURCE_LEAK_ALERT,
        ResourceTemplate.MYSQL_SLOW_QUERY_ALERT,
        ResourceTemplate.MYSQL_DEADLOCK_ALERT
    ]


def get_redis_resource_templates() -> list:
    """
    获取所有 Redis 相关的资源监控模板枚举值
    
    Returns:
        Redis 模板枚举值列表
    """
    return [
        ResourceTemplate.REDIS_MEMORY_MONITOR,
        ResourceTemplate.REDIS_CONNECTION_MONITOR,
        ResourceTemplate.REDIS_RESOURCE_LEAK_ALERT,
        ResourceTemplate.REDIS_KEY_TTL_MONITOR
    ]


def get_mongodb_resource_templates() -> list:
    """
    获取所有 MongoDB 相关的资源监控模板枚举值
    
    Returns:
        MongoDB 模板枚举值列表
    """
    return [
        ResourceTemplate.MONGODB_CONNECTION_MONITOR,
        ResourceTemplate.MONGODB_RESOURCE_LEAK_ALERT,
        ResourceTemplate.MONGODB_SLOW_OPERATION_ALERT,
        ResourceTemplate.MONGODB_INDEX_MISS_ALERT
    ]


def get_resource_leak_templates() -> list:
    """
    获取所有资源泄露相关的模板枚举值
    
    Returns:
        资源泄露模板枚举值列表
    """
    return [
        ResourceTemplate.MYSQL_RESOURCE_LEAK_ALERT,
        ResourceTemplate.REDIS_RESOURCE_LEAK_ALERT,
        ResourceTemplate.MONGODB_RESOURCE_LEAK_ALERT,
        ResourceTemplate.GENERAL_RESOURCE_LEAK_ALERT
    ]