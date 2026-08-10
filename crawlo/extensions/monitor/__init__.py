# Crawlo Monitor module

"""监控扩展子包：MemoryMonitorExtension / MySQLMonitorExtension / RedisMonitorExtension 等。"""


def __getattr__(name):
    """延迟导入监控扩展类，保持短路径 crawlo.extensions.monitor.MemoryMonitorExtension。"""
    _MAPPING = {
        'MemoryMonitorExtension': 'crawlo.extensions.monitor.memory',
        'MySQLMonitorExtension': 'crawlo.extensions.monitor.mysql',
        'RedisMonitorExtension': 'crawlo.extensions.monitor.redis',
    }
    if name in _MAPPING:
        import importlib
        return getattr(importlib.import_module(_MAPPING[name]), name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    'MemoryMonitorExtension',
    'MySQLMonitorExtension',
    'RedisMonitorExtension',
]
