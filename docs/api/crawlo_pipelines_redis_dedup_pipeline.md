# crawlo.pipelines.redis_dedup_pipeline

基于 Redis 的数据项去重管道
========================
提供分布式环境下的数据项去重功能，防止保存重复的数据记录。

特点:
- 分布式支持: 多节点共享去重数据
- 高性能: 使用 Redis 集合进行快速查找
- 可配置: 支持自定义 Redis 连接参数
- 容错设计: 网络异常时不会丢失数据

## 导入的类

- Optional
- Item
- DropItem
- Spider
- get_logger

## 类

### RedisDedupPipeline
基于 Redis 的数据项去重管道

#### 方法

##### __init__
初始化 Redis 去重管道

:param redis_host: Redis 主机地址
:param redis_port: Redis 端口
:param redis_db: Redis 数据库编号
:param redis_password: Redis 密码
:param redis_key: 存储指纹的 Redis 键名
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
