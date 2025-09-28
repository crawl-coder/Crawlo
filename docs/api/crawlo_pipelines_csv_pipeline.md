# crawlo.pipelines.csv_pipeline

## 导入的类

- Path
- Optional
- List
- datetime
- get_logger
- ItemDiscard

## 类

### CsvPipeline
CSV文件输出管道

#### 方法

##### __init__

##### from_crawler

##### _get_file_path
获取输出文件路径

### CsvDictPipeline
CSV字典写入器管道（使用DictWriter，支持字段映射）

#### 方法

##### __init__

##### from_crawler

##### _get_file_path
获取输出文件路径

##### _get_fieldnames
获取字段名列表

### CsvBatchPipeline
CSV批量写入管道（内存缓存，批量写入，提高性能）

#### 方法

##### __init__

##### from_crawler

##### _get_file_path
获取输出文件路径
