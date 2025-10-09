# Custom Pipeline

Pipelines are components in the Crawlo framework used to process crawled data. Through custom pipelines, you can implement various data processing functions such as data cleaning, validation, storage, etc.

## Creating Custom Pipelines

To create a custom pipeline, you need to inherit from the `crawlo.pipelines.Pipeline` base class and implement the corresponding methods.

### Basic Structure

```python
from crawlo.pipelines import Pipeline

class CustomPipeline(Pipeline):
    def open_spider(self, spider):
        # Called when the spider starts
        pass
    
    def close_spider(self, spider):
        # Called when the spider closes
        pass
    
    def process_item(self, item, spider):
        # Process data items
        return item
```

### Method Descriptions

#### open_spider(spider)

- **Purpose**: Called when the spider starts, used for initializing resources
- **Parameters**:
  - `spider`: Spider instance
- **Return Value**: None

#### close_spider(spider)

- **Purpose**: Called when the spider closes, used for releasing resources
- **Parameters**:
  - `spider`: Spider instance
- **Return Value**: None

#### process_item(item, spider)

- **Purpose**: Process data items
- **Parameters**:
  - `item`: Data item object
  - `spider`: Spider instance
- **Return Value**:
  - Return the processed data item
  - Raise a `DropItem` exception to discard the data item

### DropItem Exception

To discard a data item, you can raise the `DropItem` exception:

```python
from crawlo.pipelines import Pipeline, DropItem

class ValidationPipeline(Pipeline):
    def process_item(self, item, spider):
        if not item.get('title'):
            raise DropItem(f"Missing title in {item}")
        return item
```

## Examples

### Database Storage Pipeline

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

### JSON File Storage Pipeline

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

### Data Cleaning Pipeline

```python
from crawlo.pipelines import Pipeline
import re

class CleaningPipeline(Pipeline):
    def process_item(self, item, spider):
        # Clean title
        if 'title' in item:
            item['title'] = re.sub(r'\s+', ' ', item['title']).strip()
        
        # Clean content
        if 'content' in item:
            item['content'] = re.sub(r'<[^>]+>', '', item['content'])  # Remove HTML tags
            item['content'] = re.sub(r'\s+', ' ', item['content']).strip()
        
        # Validate URL
        if 'url' in item:
            if not item['url'].startswith(('http://', 'https://')):
                item['url'] = 'http://' + item['url']
        
        return item
```

## Configuring Pipelines

Enable custom pipelines in the configuration file:

```python
# settings.py
PIPELINES = {
    'myproject.pipelines.CleaningPipeline': 300,
    'myproject.pipelines.ValidationPipeline': 400,
    'myproject.pipelines.DatabasePipeline': 500,
}
```

The number for pipelines represents the execution order, with smaller numbers having higher priority.

## Best Practices

1. **Single Responsibility**: Each pipeline should only be responsible for one function
2. **Exception Handling**: Properly handle exceptions in pipelines
3. **Resource Management**: Correctly open and close resources (such as files, database connections, etc.)
4. **Performance Considerations**: Avoid performing time-consuming operations in pipelines, consider batch processing
5. **Data Consistency**: Ensure data remains consistent during pipeline processing
6. **Testing**: Write unit tests for pipelines