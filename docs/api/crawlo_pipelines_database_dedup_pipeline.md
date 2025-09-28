# crawlo.pipelines.database_dedup_pipeline

基于数据库的数据项去重管道
=======================
提供持久化去重功能，适用于需要长期运行或断点续爬的场景。

特点:
- 持久化存储: 重启爬虫后仍能保持去重状态
- 可靠性高: 数据库事务保证一致性
- 适用性广: 支持多种数据库后端
- 可扩展: 支持自定义表结构和字段

## 导入的类

- Dict
- Any
- Optional
- Item
- Spider
- get_logger
- DropItem

## 类

### DatabaseDedupPipeline
基于数据库的数据项去重管道

#### 方法

##### __init__
初始化数据库去重管道

:param db_host: 数据库主机地址
:param db_port: 数据库端口
:param db_user: 数据库用户名
:param db_password: 数据库密码
:param db_name: 数据库名称
:param table_name: 存储指纹的表名
:param log_level: 日志级别

##### from_crawler
从爬虫配置创建管道实例

##### _generate_item_fingerprint
生成数据项指纹

基于数据项的所有字段生成唯一指纹，用于去重判断。

:param item: 数据项
:return: 指纹字符串
