# crawlo.pipelines.bloom_dedup_pipeline

基于 Bloom Filter 的数据项去重管道
=============================
提供大规模数据采集场景下的高效去重功能，使用概率性数据结构节省内存。

特点:
- 内存效率高: 相比传统集合节省大量内存
- 高性能: 快速的插入和查找操作
- 可扩展: 支持自定义容量和误判率
- 适用性广: 特别适合大规模数据采集

注意: Bloom Filter 有误判率，可能会错误地丢弃一些未见过的数据项。

## 导入的类

- Item
- Spider
- get_logger
- DropItem

## 类

### BloomDedupPipeline
基于 Bloom Filter 的数据项去重管道

#### 方法

##### __init__
初始化 Bloom Filter 去重管道

:param capacity: 预期存储的元素数量
:param error_rate: 误判率 (例如 0.001 表示 0.1%)
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
