#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
向后兼容便利函数
================
原 crawlo.config 中遗留的函数式 API，
新代码请直接使用 CrawloConfig 静态工厂。

注意：本模块不顶层导入 CrawloConfig（避免 config.py ↔ compat 循环导入），
     改为在函数体内部按需导入。
"""
from typing import TYPE_CHECKING, Dict, Any, List, Tuple

if TYPE_CHECKING:
    from crawlo.core.config import CrawloConfig

from crawlo.core.config.validator import ConfigValidator


def create_config(mode: str = 'standalone', **kwargs) -> 'CrawloConfig':
    """创建配置（向后兼容）"""
    from crawlo.core.config import CrawloConfig  # 延迟导入，避免循环
    if mode.lower() == 'standalone':
        return CrawloConfig.standalone(**kwargs)
    if mode.lower() == 'distributed':
        return CrawloConfig.distributed(**kwargs)
    if mode.lower() == 'auto':
        return CrawloConfig.auto(**kwargs)
    raise ValueError(f"Unknown mode: {mode}")


def validate_config(config: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    """验证配置（向后兼容）"""
    return ConfigValidator().validate(config)


def standalone_mode(project_name: str = 'crawlo', **kwargs) -> Dict[str, Any]:
    """单机模式配置（向后兼容）"""
    from crawlo.core.config import CrawloConfig  # 延迟导入，避免循环
    return CrawloConfig.standalone(project_name, **kwargs).to_dict()


def distributed_mode(redis_host: str = '127.0.0.1', redis_port: int = 6379,
                     project_name: str = 'crawlo', **kwargs) -> Dict[str, Any]:
    """分布式模式配置（向后兼容）"""
    from crawlo.core.config import CrawloConfig  # 延迟导入，避免循环
    return CrawloConfig.distributed(
        project_name=project_name,
        redis_host=redis_host,
        redis_port=redis_port,
        **kwargs,
    ).to_dict()


def auto_mode(project_name: str = 'crawlo', **kwargs) -> Dict[str, Any]:
    """自动检测模式配置（向后兼容）"""
    from crawlo.core.config import CrawloConfig  # 延迟导入，避免循环
    return CrawloConfig.auto(project_name, **kwargs).to_dict()


def from_env(default_mode: str = 'standalone') -> Dict[str, Any]:
    """从环境变量创建配置（向后兼容）"""
    from crawlo.core.config import CrawloConfig  # 延迟导入，避免循环
    return CrawloConfig.from_env(default_mode).to_dict()


__all__ = [
    'create_config',
    'validate_config',
    'standalone_mode',
    'distributed_mode',
    'auto_mode',
    'from_env',
]
