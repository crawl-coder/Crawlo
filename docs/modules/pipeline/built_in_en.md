# Built-in Pipelines

Crawlo provides several built-in pipeline components that handle common data processing and storage tasks. These pipeline components can be enabled or disabled through configuration.

## Overview

Built-in pipelines provide essential functionality for data processing:

- Data output and storage
- Item deduplication
- Data transformation
- Validation and cleaning

## ConsolePipeline

Outputs items to the console for debugging and development.

### Features

- Simple item display
- JSON formatting
- Colorized output
- Configurable verbosity

### Configuration

```python
# In settings.py
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
]

# Console pipeline settings
CONSOLE_PIPELINE_ENABLED = True
CONSOLE_PIPELINE_FORMAT = 'json'  # or 'pretty'
```

## JsonPipeline

Saves items to JSON files for persistent storage.

### Features

- JSON file output
- Configurable file naming
- Append or overwrite modes
- Pretty printing support

### Configuration

```python
# In settings.py
PIPELINES = [
    'crawlo.pipelines.json_pipeline.JsonPipeline',
]

# JSON pipeline settings
JSON_PIPELINE_ENABLED = True
JSON_PIPELINE_FILENAME = 'items.json'
JSON_PIPELINE_MODE = 'append'  # or 'overwrite'
JSON_PIPELINE_INDENT = 2
```

## CsvPipeline

Saves items to CSV files for spreadsheet compatibility.

### Features

- CSV file output
- Automatic field detection
- Custom field mapping
- Encoding support

### Configuration

```python
# In settings.py
PIPELINES = [
    'crawlo.pipelines.csv_pipeline.CsvPipeline',
]

# CSV pipeline settings
CSV_PIPELINE_ENABLED = True
CSV_PIPELINE_FILENAME = 'items.csv'
CSV_PIPELINE_ENCODING = 'utf-8'
CSV_PIPELINE_DELIMITER = ','
```

## MemoryDedupPipeline

Deduplicates items using in-memory storage.

### Features

- Fast in-memory deduplication
- Configurable fingerprinting
- Memory-efficient storage
- Suitable for standalone mode

### Configuration

```python
# In settings.py
PIPELINES = [
    'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline',
]

# Memory dedup pipeline settings
MEMORY_DEDUP_ENABLED = True
MEMORY_DEDUP_FIELD = None  # Use entire item, or specify field
```

## RedisDedupPipeline

Deduplicates items using Redis storage for distributed deduplication.

### Features

- Distributed deduplication
- Persistent storage
- Configurable TTL
- Shared across nodes

### Configuration

```python
# In settings.py
PIPELINES = [
    'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline',
]

# Redis dedup pipeline settings
REDIS_DEDUP_ENABLED = True
REDIS_DEDUP_KEY = 'crawlo:dedup:items'
REDIS_DEDUP_TTL = 86400  # 24 hours
REDIS_URL = 'redis://localhost:6379'
```

## BloomDedupPipeline

Deduplicates items using Bloom filters for memory-efficient deduplication.

### Features

- Memory-efficient deduplication
- Probabilistic data structure
- Configurable error rates
- High performance

### Configuration

```python
# In settings.py
PIPELINES = [
    'crawlo.pipelines.bloom_dedup_pipeline.BloomDedupPipeline',
]

# Bloom dedup pipeline settings
BLOOM_DEDUP_ENABLED = True
BLOOM_DEDUP_CAPACITY = 1000000
BLOOM_DEDUP_ERROR_RATE = 0.001
```

## AsyncmyMySQLPipeline

Stores items in MySQL database using asyncmy driver.

### Features

- Asynchronous MySQL operations
- Connection pooling
- Batch inserts
- Transaction support

### Configuration

```python
# In settings.py
PIPELINES = [
    'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',
]

# MySQL pipeline settings
MYSQL_PIPELINE_ENABLED = True
MYSQL_HOST = 'localhost'
MYSQL_PORT = 3306
MYSQL_USER = 'user'
MYSQL_PASSWORD = 'password'
MYSQL_DB = 'database'
MYSQL_TABLE = 'items'
MYSQL_BATCH_SIZE = 100
```

## MongoPipeline

Stores items in MongoDB database.

### Features

- Asynchronous MongoDB operations
- Connection pooling
- Batch inserts
- Flexible document structure

### Configuration

```python
# In settings.py
PIPELINES = [
    'crawlo.pipelines.mongo_pipeline.MongoPipeline',
]

# MongoDB pipeline settings
MONGO_PIPELINE_ENABLED = True
MONGO_URI = 'mongodb://localhost:27017'
MONGO_DATABASE = 'database'
MONGO_COLLECTION = 'items'
MONGO_BATCH_SIZE = 100
```

## DatabaseDedupPipeline

Deduplicates items using database storage.

### Features

- Database-based deduplication
- Multiple database support
- Configurable fingerprinting
- Persistent storage

### Configuration

```python
# In settings.py
PIPELINES = [
    'crawlo.pipelines.database_dedup_pipeline.DatabaseDedupPipeline',
]

# Database dedup pipeline settings
DATABASE_DEDUP_ENABLED = True
DATABASE_DEDUP_TABLE = 'dedup_fingerprints'
DATABASE_DEDUP_FIELD = 'fingerprint'
```

## Usage Example

To enable multiple built-in pipelines:

```python
# In settings.py
PIPELINES = [
    # Deduplication (typically first)
    'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline',
    
    # Output for debugging
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
    
    # File storage
    'crawlo.pipelines.json_pipeline.JsonPipeline',
    
    # Database storage (typically last)
    'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',
]
```

## Pipeline Order Considerations

Pipeline order is important for proper functionality:

1. **Deduplication pipelines** should typically be first
2. **Processing pipelines** come in the middle
3. **Storage pipelines** should typically be last

Example recommended order:
```python
PIPELINES = [
    # 1. Deduplication
    'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline',
    
    # 2. Data processing
    'crawlo.pipelines.validation_pipeline.ValidationPipeline',
    'crawlo.pipelines.cleaning_pipeline.CleaningPipeline',
    
    # 3. Output and storage
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
    'crawlo.pipelines.json_pipeline.JsonPipeline',
    'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',
]
```

## Performance Considerations

- Place lightweight pipelines first to filter early
- Disable unused pipelines to reduce overhead
- Use batch processing for database pipelines
- Monitor pipeline processing times to identify bottlenecks
- Consider using appropriate deduplication for your scale