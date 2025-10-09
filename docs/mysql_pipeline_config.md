# MySQL 管道配置指南

## 概述

MySQL 管道提供了多种配置选项，允许用户控制数据插入行为。这些配置可以通过全局设置或爬虫特定设置来定义。

## 配置选项

### 基本连接配置

```python
# MySQL连接配置
MYSQL_HOST = 'localhost'
MYSQL_PORT = 3306
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'password'
MYSQL_DB = 'scrapy_db'
MYSQL_TABLE = 'items'

# 连接池配置
MYSQL_POOL_MIN = 3
MYSQL_POOL_MAX = 10
MYSQL_ECHO = False
```

### 批量插入配置

```python
# 批量插入配置
MYSQL_BATCH_SIZE = 100
MYSQL_USE_BATCH = False
```

### SQL 生成行为控制

这是新增的配置选项，用于控制 SQL 语句的生成方式。这些配置选项已在默认配置文件中定义默认值：

```python
# SQL生成行为控制配置（已在默认配置中定义）
MYSQL_AUTO_UPDATE = False      # 是否使用 REPLACE INTO（完全覆盖已存在记录）
MYSQL_INSERT_IGNORE = False    # 是否使用 INSERT IGNORE（忽略重复数据）
MYSQL_UPDATE_COLUMNS = ()      # 冲突时需更新的列名；指定后 MYSQL_AUTO_UPDATE 失效
```

## 使用场景和配置示例

### 1. 默认行为：INSERT INTO

如果记录已存在会报错：

```python
MYSQL_AUTO_UPDATE = False
MYSQL_INSERT_IGNORE = False
MYSQL_UPDATE_COLUMNS = ()
```

### 2. 忽略重复数据：INSERT IGNORE INTO

如果记录已存在则忽略：

```python
MYSQL_AUTO_UPDATE = False
MYSQL_INSERT_IGNORE = True
MYSQL_UPDATE_COLUMNS = ()
```

### 3. 完全覆盖已存在记录：REPLACE INTO

如果记录已存在则完全替换：

```python
MYSQL_AUTO_UPDATE = True
MYSQL_INSERT_IGNORE = False
MYSQL_UPDATE_COLUMNS = ()
```

### 4. 冲突时只更新指定列

使用 `INSERT INTO ... ON DUPLICATE KEY UPDATE` 语法：

```python
MYSQL_AUTO_UPDATE = False  # 此选项会被 MYSQL_UPDATE_COLUMNS 覆盖
MYSQL_INSERT_IGNORE = False
MYSQL_UPDATE_COLUMNS = ('updated_at', 'view_count')
```

## 爬虫特定配置

可以在爬虫类中定义特定配置：

```python
class MySpider:
    name = 'my_spider'
    
    # 爬虫特定的表名
    mysql_table = 'spider_items'
    
    # 爬虫特定的custom_settings
    custom_settings = {
        'MYSQL_TABLE': 'custom_table_for_this_spider',
        'MYSQL_AUTO_UPDATE': True,  # 对于这个爬虫使用 REPLACE INTO
        'MYSQL_UPDATE_COLUMNS': (),  # 不使用 ON DUPLICATE KEY UPDATE
    }
```

## 运行时参数覆盖

在调用 [process_item](file:///d:/dowell/projects/Crawlo/crawlo/pipelines/mysql_pipeline.py#L51-L89) 方法时，可以通过 kwargs 参数临时覆盖配置：

```python
# 在自定义管道中
async def process_item(self, item, spider):
    # 临时覆盖配置
    return await self.mysql_pipeline.process_item(
        item, 
        spider, 
        auto_update=True, 
        insert_ignore=False
    )
```

## 最佳实践

1. **选择合适的策略**：根据业务需求选择合适的插入策略
2. **性能考虑**：批量插入通常比单条插入性能更好
3. **数据一致性**：谨慎使用 REPLACE INTO，因为它会完全替换记录
4. **冲突处理**：使用 UPDATE_COLUMNS 可以精确控制哪些字段在冲突时更新
5. **默认配置**：利用框架提供的默认配置，减少重复配置工作