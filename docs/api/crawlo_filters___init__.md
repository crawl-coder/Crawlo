# crawlo.filters.__init__

Crawlo Filters Module
====================
提供多种请求去重过滤器实现。

过滤器类型:
- MemoryFilter: 基于内存的高效去重，适合单机模式
- AioRedisFilter: 基于Redis的分布式去重，适合分布式模式
- MemoryFileFilter: 内存+文件持久化，适合需要重启恢复的场景

核心接口:
- BaseFilter: 所有过滤器的基类
- requested(): 检查请求是否重复的主要方法

## 导入的类

- ABC
- abstractmethod
- Optional
- request_fingerprint

## 类

### BaseFilter
请求去重过滤器基类

提供统一的去重接口和统计功能。
所有过滤器实现都应该继承此类。

#### 方法

##### __init__
初始化过滤器

:param logger: 日志器实例
:param stats: 统计信息存储
:param debug: 是否启用调试日志

##### create_instance

##### requested
检查请求是否重复（主要接口）

:param request: 请求对象
:return: True 表示重复，False 表示新请求

##### add_fingerprint
添加请求指纹（子类必须实现）

:param fp: 请求指纹字符串

##### __contains__
检查指纹是否存在（支持 in 操作符）

:param item: 要检查的指纹
:return: 是否已存在

##### log_stats
记录统计信息

:param request: 重复的请求对象

##### get_stats
获取过滤器统计信息

:return: 统计信息字典

##### reset_stats
重置统计信息

##### close
关闭过滤器并清理资源

##### __str__

## 函数

### get_filter_class
根据名称获取过滤器类
