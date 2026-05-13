#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Redis Key 管理
================
提供 Redis Key 管理器、Key 验证器和相关便利函数
"""
from typing import Optional, Any, List, Tuple

from crawlo.logging import get_logger


def validate_redis_key_naming(key: str, project_name: Optional[str] = None) -> bool:
    """
    验证Redis Key是否符合命名规范

    Args:
        key: Redis Key
        project_name: 项目名称（可选）

    Returns:
        bool: 是否符合命名规范
    """
    validator = RedisKeyValidator()
    return validator.validate_key_naming(key, project_name)


class RedisKeyManager:
    """Redis Key 管理器"""

    def __init__(self, project_name: str = "default", spider_name: Optional[str] = None):
        """
        初始化 Redis Key 管理器

        Args:
            project_name: 项目名称
            spider_name: 爬虫名称（可选）
        """
        self.project_name = project_name
        self.spider_name = spider_name
        self.logger = get_logger(self.__class__.__name__)

        if self.spider_name:
            self.namespace = f"{self.project_name}:{self.spider_name}"
        else:
            self.namespace = self.project_name

    def set_spider_name(self, spider_name: str) -> None:
        """设置爬虫名称"""
        self.spider_name = spider_name if spider_name else None
        if self.spider_name:
            self.namespace = f"{self.project_name}:{self.spider_name}"
        else:
            self.namespace = self.project_name

    def _generate_key(self, component: str, sub_component: str) -> str:
        """生成 Redis Key"""
        key = f"crawlo:{self.namespace}:{component}:{sub_component}"

        if not validate_redis_key_naming(key, self.project_name):
            self.logger.warning(f"生成的 Redis Key 不符合命名规范: {key}")

        return key

    # ==================== 队列相关 Key ====================

    def get_requests_queue_key(self) -> str:
        """获取请求队列 Key"""
        return self._generate_key("queue", "requests")

    def get_processing_queue_key(self) -> str:
        """获取处理中队列 Key"""
        return self._generate_key("queue", "processing")

    def get_failed_queue_key(self) -> str:
        """获取失败队列 Key"""
        return self._generate_key("queue", "failed")

    def get_requests_data_key(self) -> str:
        """获取请求数据 Hash Key"""
        return f"{self.get_requests_queue_key()}:data"

    def get_processing_data_key(self) -> str:
        """获取处理中数据 Hash Key"""
        return f"{self.get_processing_queue_key()}:data"

    def get_failed_retries_key(self, request_key: str) -> str:
        """获取失败重试计数 Key"""
        return f"{self.get_failed_queue_key()}:retries:{request_key}"

    # ==================== 过滤器相关 Key ====================

    def get_filter_fingerprint_key(self) -> str:
        """获取请求去重过滤器指纹 Key"""
        return self._generate_key("filter", "fingerprint")

    # ==================== 数据项相关 Key ====================

    def get_item_fingerprint_key(self) -> str:
        """获取数据项去重指纹 Key"""
        return self._generate_key("item", "fingerprint")

    # ==================== 静态方法 ====================

    @staticmethod
    def from_settings(settings: Any) -> 'RedisKeyManager':
        """从配置创建 Redis Key 管理器实例"""
        project_name = RedisKeyManager._get_setting(settings, 'PROJECT_NAME', 'default')
        spider_name = RedisKeyManager._get_setting(settings, 'SPIDER_NAME', None)
        return RedisKeyManager(project_name, spider_name)

    @staticmethod
    def _get_setting(settings: Any, key: str, default: Any) -> Any:
        """统一获取配置值，兼容多种 settings 对象"""
        if hasattr(settings, 'get'):
            return settings.get(key, default)
        return getattr(settings, key, default)

    @staticmethod
    def extract_project_name_from_key(key: str) -> Optional[str]:
        """从 Redis Key 中提取项目名称"""
        if not key or not key.startswith('crawlo:'):
            return None

        parts = key.split(':')
        if len(parts) >= 2:
            return parts[1]
        return None

    @staticmethod
    def extract_spider_name_from_key(key: str) -> Optional[str]:
        """从 Redis Key 中提取爬虫名称"""
        if not key or not key.startswith('crawlo:'):
            return None

        parts = key.split(':')
        if len(parts) >= 4:
            if parts[2] not in ['queue', 'filter', 'item']:
                return parts[2]
        return None


# 便利函数
def create_redis_key_manager(project_name: str = "default", spider_name: Optional[str] = None) -> RedisKeyManager:
    """创建 Redis Key 管理器实例"""
    return RedisKeyManager(project_name, spider_name)


def get_redis_key_manager_from_settings(settings: Any) -> RedisKeyManager:
    """从配置创建 Redis Key 管理器实例"""
    return RedisKeyManager.from_settings(settings)


class RedisKeyValidator:
    """Redis Key 验证器"""

    def __init__(self):
        self.logger = None

    @property
    def _logger(self):
        if self.logger is None:
            # get_logger 已在顶部导入
            self.logger = get_logger(self.__class__.__name__)
        return self.logger

    def validate_key_naming(self, key: str, project_name: Optional[str] = None) -> bool:
        """验证Redis Key是否符合命名规范"""
        if not isinstance(key, str) or not key:
            return False

        if not key.startswith('crawlo:'):
            return False

        parts = key.split(':')
        if len(parts) < 3:
            return False

        if parts[0] != 'crawlo':
            return False

        valid_components = ['filter', 'queue', 'item']

        if len(parts) >= 4 and parts[3] in valid_components:
            if project_name and parts[1] != project_name:
                return False
            if parts[3] not in valid_components:
                return False
            if parts[3] == 'queue':
                valid_subcomponents = ['requests', 'processing', 'failed']
                if len(parts) < 5 or parts[4] not in valid_subcomponents:
                    return False
            elif parts[3] in ['filter', 'item']:
                if len(parts) < 5 or parts[4] != 'fingerprint':
                    return False
        else:
            if project_name and parts[1] != project_name:
                return False
            if parts[2] not in valid_components:
                return False
            if parts[2] == 'queue':
                valid_subcomponents = ['requests', 'processing', 'failed']
                if len(parts) < 4 or parts[3] not in valid_subcomponents:
                    return False
            elif parts[2] in ['filter', 'item']:
                if len(parts) < 4 or parts[3] != 'fingerprint':
                    return False

        return True

    def validate_multiple_keys(self, keys: List[str], project_name: Optional[str] = None) -> Tuple[bool, List[str]]:
        """验证多个Redis Key"""
        invalid_keys = []
        for key in keys:
            if not self.validate_key_naming(key, project_name):
                invalid_keys.append(key)

        return len(invalid_keys) == 0, invalid_keys

    def get_key_info(self, key: str) -> dict:
        """获取Redis Key的信息"""
        if not self.validate_key_naming(key):
            return {
                'valid': False,
                'error': 'Key不符合命名规范'
            }

        parts = key.split(':')
        info = {
            'valid': True,
            'framework': parts[0]
        }

        if len(parts) >= 4 and parts[3] in ['filter', 'queue', 'item']:
            info['project'] = parts[1]
            info['spider'] = parts[2]
            info['component'] = parts[3]
            if len(parts) >= 5:
                info['sub_component'] = parts[4]
        else:
            info['project'] = parts[1]
            info['component'] = parts[2]
            if len(parts) >= 4:
                info['sub_component'] = parts[3]

        return info


def validate_multiple_redis_keys(keys: List[str], project_name: Optional[str] = None) -> Tuple[bool, List[str]]:
    """验证多个Redis Key"""
    validator = RedisKeyValidator()
    return validator.validate_multiple_keys(keys, project_name)


def get_redis_key_info(key: str) -> dict:
    """获取Redis Key的信息"""
    validator = RedisKeyValidator()
    return validator.get_key_info(key)


def print_validation_report(keys: List[str], project_name: Optional[str] = None):
    """打印Redis Key验证报告"""
    logger = get_logger('RedisKeyValidator')

    validator = RedisKeyValidator()
    is_valid, invalid_keys = validator.validate_multiple_keys(keys, project_name)

    logger.info("=" * 50)
    logger.info("Redis Key 命名规范验证报告")
    logger.info("=" * 50)

    if is_valid:
        logger.info("所有Redis Key命名规范验证通过")
    else:
        logger.info("发现不符合命名规范的Redis Key:")
        for key in invalid_keys:
            logger.info(f"  - {key}")

    logger.info("\nKey 详细信息:")
    for key in keys:
        info = validator.get_key_info(key)
        if info['valid']:
            logger.info(f"  {key}")
            logger.info(f"     框架: {info['framework']}")
            logger.info(f"     项目: {info['project']}")
            logger.info(f"     组件: {info['component']}")
            if 'sub_component' in info:
                logger.info(f"     子组件: {info['sub_component']}")
        else:
            logger.info(f"  {key} - {info.get('error', '无效')}")

    logger.info("=" * 50)
