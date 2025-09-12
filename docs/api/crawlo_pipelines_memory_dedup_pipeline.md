# crawlo.pipelines.memory_dedup_pipeline

基于内存的数据项去重管道
======================
提供单节点环境下的数据项去重功能，防止保存重复的数据记录。

特点:
- 高性能: 使用内存集合进行快速查找
- 简单易用: 无需外部依赖
- 轻量级: 适用于小规模数据采集
- 低延迟: 内存操作无网络开销

## 导入的类

- Dict
- Any
- Set
- Item
- Spider
- get_logger
- DropItem

## 类

### MemoryDedupPipeline
基于内存的数据项去重管道

#### 方法

##### __init__
初始化内存去重管道

:param log_level: 日志级别

##### from_crawler
从爬虫配置创建管道实例

##### process_item
处理数据项，进行去重检查

:param item: 要处理的数据项
:param spider: 爬虫实例
:return: 处理后的数据项或抛出 DropItem 异常

##### _generate_item_fingerprint
生成数据项指纹

基于数据项的所有字段生成唯一指纹，用于去重判断。

:param item: 数据项
:return: 指纹字符串

##### close_spider
爬虫关闭时的清理工作

:param spider: 爬虫实例
