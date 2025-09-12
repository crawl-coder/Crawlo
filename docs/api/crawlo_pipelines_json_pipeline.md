# crawlo.pipelines.json_pipeline

## 导入的类

- Path
- Optional
- datetime
- get_logger
- ItemDiscard

## 类

### JsonPipeline
JSON文件输出管道

#### 方法

##### __init__

##### from_crawler

##### _get_file_path
获取输出文件路径

### JsonLinesPipeline
JSON Lines格式输出管道（每行一个JSON对象）

#### 方法

##### __init__

##### from_crawler

##### _get_file_path
获取输出文件路径

### JsonArrayPipeline
JSON数组格式输出管道（所有item组成一个JSON数组）

#### 方法

##### __init__

##### from_crawler

##### _get_file_path
获取输出文件路径
