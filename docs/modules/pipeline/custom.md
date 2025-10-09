# 自定义管道

管道是 Crawlo 框架中用于处理爬取数据的组件。通过自定义管道，您可以实现各种数据处理功能，如数据清洗、验证、存储等。

## 创建自定义管道

要创建自定义管道，需要继承 `crawlo.pipelines.Pipeline` 基类并实现相应的方法。

### 基本结构

```python
from crawlo.pipelines import Pipeline

class CustomPipeline(Pipeline):
    def open_spider(self, spider):
        # 爬虫启动时调用
        pass
    
    def close_spider(self, spider):
        # 爬虫关闭时调用
        pass
    
    def process_item(self, item, spider):
        # 处理数据项
        return item
```

### 方法说明

#### open_spider(spider)

- **作用**: 在爬虫启动时调用，用于初始化资源
- **参数**:
  - `spider`: 爬虫实例
- **返回值**: 无

#### close_spider(spider)

- **作用**: 在爬虫关闭时调用，用于释放资源
- **参数**:
  - `spider`: 爬虫实例
- **返回值**: 无

#### process_item(item, spider)

- **作用**: 处理数据项
- **参数**:
  - `item`: 数据项对象
  - `spider`: 爬虫实例
- **返回值**:
  - 返回处理后的数据项
  - 抛出 `DropItem` 异常以丢弃数据项

### DropItem 异常

要丢弃数据项，可以抛出 `DropItem` 异常：

```python
from crawlo.pipelines import Pipeline, DropItem

class ValidationPipeline(Pipeline):
    def process_item(self, item, spider):
        if not item.get('title'):
            raise DropItem(f"Missing title in {item}")
        return item
```

## 示例

### 数据库存储管道

```python
from crawlo.pipelines import Pipeline
import sqlite3

class DatabasePipeline(Pipeline):
    def open_spider(self, spider):
        self.connection = sqlite3.connect('data.db')
        self.cursor = self.connection.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                url TEXT,
                content TEXT
            )
        ''')
        self.connection.commit()
    
    def close_spider(self, spider):
        self.connection.close()
    
    def process_item(self, item, spider):
        self.cursor.execute('''
            INSERT INTO items (title, url, content)
            VALUES (?, ?, ?)
        ''', (item.get('title'), item.get('url'), item.get('content')))
        self.connection.commit()
        return item
```

### JSON 文件存储管道

```python
from crawlo.pipelines import Pipeline
import json
import os

class JsonPipeline(Pipeline):
    def open_spider(self, spider):
        self.file = open('items.json', 'w', encoding='utf-8')
        self.file.write('[\n')
        self.first_item = True
    
    def close_spider(self, spider):
        self.file.write('\n]')
        self.file.close()
    
    def process_item(self, item, spider):
        if not self.first_item:
            self.file.write(',\n')
        else:
            self.first_item = False
        
        line = json.dumps(dict(item), ensure_ascii=False, indent=2)
        self.file.write(line)
        return item
```

### 数据清洗管道

```python
from crawlo.pipelines import Pipeline
import re

class CleaningPipeline(Pipeline):
    def process_item(self, item, spider):
        # 清洗标题
        if 'title' in item:
            item['title'] = re.sub(r'\s+', ' ', item['title']).strip()
        
        # 清洗内容
        if 'content' in item:
            item['content'] = re.sub(r'<[^>]+>', '', item['content'])  # 移除HTML标签
            item['content'] = re.sub(r'\s+', ' ', item['content']).strip()
        
        # 验证URL
        if 'url' in item:
            if not item['url'].startswith(('http://', 'https://')):
                item['url'] = 'http://' + item['url']
        
        return item
```

## 配置管道

在配置文件中启用自定义管道：

```python
# settings.py
PIPELINES = {
    'myproject.pipelines.CleaningPipeline': 300,
    'myproject.pipelines.ValidationPipeline': 400,
    'myproject.pipelines.DatabasePipeline': 500,
}
```

管道的数字表示执行顺序，数字越小优先级越高。

## 最佳实践

1. **单一职责**: 每个管道应该只负责一个功能
2. **异常处理**: 在管道中妥善处理异常
3. **资源管理**: 正确打开和关闭资源（如文件、数据库连接等）
4. **性能考虑**: 避免在管道中执行耗时操作，考虑批量处理
5. **数据一致性**: 确保数据在管道处理过程中保持一致性
6. **测试**: 为管道编写单元测试