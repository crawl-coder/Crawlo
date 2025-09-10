# Redis Key Naming Convention

## 1. Overview

To improve the readability, maintainability, and consistency of Redis keys, we have established a unified Redis key naming convention. All Redis keys follow the following format:

```
crawlo:{project_name}:{component}:{sub_component}
```

## 2. Naming Convention Explanation

### 2.1 Basic Structure

| Part | Description | Example |
|------|-------------|---------|
| `crawlo` | Fixed prefix, identifying the Crawlo framework | crawlo |
| `{project_name}` | Project name, obtained from configuration | books_distributed, api_data_collection |
| `{component}` | Component type | filter, queue, item |
| `{sub_component}` | Sub-component or function | fingerprint, requests, processing, failed |

### 2.2 Specific Naming Rules

#### 2.2.1 Request Deduplication Filter (Filter)

- Request fingerprint storage: `crawlo:{project_name}:filter:fingerprint`

#### 2.2.2 Queue Manager (Queue)

- Request queue: `crawlo:{project_name}:queue:requests`
- Processing queue: `crawlo:{project_name}:queue:processing`
- Failed queue: `crawlo:{project_name}:queue:failed`

#### 2.2.3 Data Item Deduplication (Item)

- Data item fingerprint storage: `crawlo:{project_name}:item:fingerprint`

## 3. Examples

### 3.1 Books Distributed Crawler Project

```
crawlo:books_distributed:filter:fingerprint
crawlo:books_distributed:queue:requests
crawlo:books_distributed:queue:processing
crawlo:books_distributed:queue:failed
crawlo:books_distributed:item:fingerprint
```

### 3.2 API Data Collection Project

```
crawlo:api_data_collection:filter:fingerprint
crawlo:api_data_collection:queue:requests
crawlo:api_data_collection:queue:processing
crawlo:api_data_collection:queue:failed
crawlo:api_data_collection:item:fingerprint
```

## 4. Configuration Method

### 4.1 Configure Project Name in settings.py

```python
PROJECT_NAME = 'your_project_name'
```

### 4.2 Redis URL Configuration

```python
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = ''
REDIS_DB = 0
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
```

## 5. Advantages

1. **Consistency**: All projects use the same naming convention
2. **Readability**: The purpose and project ownership can be clearly understood from the key name
3. **Maintainability**: Easy to manage and clean up Redis data for specific projects
4. **Scalability**: Supports adding new components and sub-components

## 6. Component Descriptions

### 6.1 Request Deduplication Filter (Filter)
- **Purpose**: Prevent sending duplicate network requests
- **Implementation Location**: Framework core layer
- **Processing Time**: Before sending requests
- **Deduplication Basis**: Request fingerprint (URL, method, parameters, etc.)

### 6.2 Queue Manager (Queue)
- **Purpose**: Manage crawler task queues
- **Implementation Location**: Framework core layer
- **Included Queues**:
  - requests: Pending request queue
  - processing: Requests being processed queue
  - failed: Failed request queue

### 6.3 Data Item Deduplication (Item)
- **Purpose**: Prevent saving duplicate data results
- **Implementation Location**: Data pipeline layer (user-defined)
- **Processing Time**: Before saving data
- **Deduplication Basis**: Data content (data item fields)

## 7. Key Validation Tools

Crawlo framework provides Redis Key validation tools to verify whether Redis Keys comply with naming conventions.

### 7.1 Using Configuration Validator to Validate Redis Keys

```python
from crawlo.config_validator import ConfigValidator

# Create configuration validator
validator = ConfigValidator()

# Validate configuration (including Redis Keys)
config = {
    'PROJECT_NAME': 'test_project',
    'QUEUE_TYPE': 'redis',
    'SCHEDULER_QUEUE_NAME': 'crawlo:test_project:queue:requests',
    'REDIS_HOST': '127.0.0.1',
    'REDIS_PORT': 6379
}

is_valid, errors, warnings = validator.validate(config)
if not is_valid:
    print("Configuration validation failed:")
    for error in errors:
        print(f"  - {error}")
```

### 7.2 Redis Key Naming Convention Validation Function

```python
from crawlo.utils.redis_key_validator import validate_redis_key_naming

# Validate a single Redis Key
key = "crawlo:my_project:queue:requests"
is_valid = validate_redis_key_naming(key, "my_project")
print(f"Key '{key}' naming convention validation: {'Passed' if is_valid else 'Failed'}")

# Validate multiple Redis Keys
keys = [
    "crawlo:my_project:filter:fingerprint",
    "crawlo:my_project:queue:requests",
    "crawlo:my_project:queue:processing",
    "crawlo:my_project:item:fingerprint"
]

for key in keys:
    is_valid = validate_redis_key_naming(key, "my_project")
    print(f"Key '{key}' naming convention validation: {'Passed' if is_valid else 'Failed'}")
```

### 7.3 Command Line Tool

Crawlo also provides a command line tool to validate Redis Key naming conventions:

```bash
# Validate Redis Keys in project configuration
crawlo validate-config --project-path /path/to/your/project

# Validate specific Redis Key
crawlo validate-redis-key "crawlo:my_project:queue:requests" --project-name my_project
```

## 8. Modification Records

### 8.1 Migration from Old Configuration to New Convention

#### 8.1.1 Removed Old Configuration Items
- `REDIS_KEY` configuration item has been removed from all configuration files

#### 8.1.2 Modified Files
1. **Framework Core Files**:
   - `crawlo/filters/aioredis_filter.py`: Use unified Redis key naming convention
   - `crawlo/queue/redis_priority_queue.py`: Use unified Redis key naming convention
   - `crawlo/queue/queue_manager.py`: Correctly pass module_name parameter
   - `crawlo/pipelines/redis_dedup_pipeline.py`: Use unified Redis key naming convention
   - `crawlo/mode_manager.py`: Remove old REDIS_KEY configuration

2. **Template Files**:
   - `crawlo/templates/project/settings.py.tmpl`: Update Redis key configuration instructions

3. **Example Projects**:
   - `examples/books_distributed/books_distributed/settings.py`: Update Redis key configuration instructions
   - `examples/api_data_collection/api_data_collection/settings.py`: Update Redis key configuration instructions
   - `examples/telecom_licenses_distributed/telecom_licenses_distributed/settings.py`: Update Redis key configuration instructions

### 8.2 Configuration Migration Guide

#### 8.2.1 Old Configuration Method
```python
# Old configuration method (deprecated)
REDIS_KEY = 'project_name:fingerprint'
```

#### 8.2.2 New Configuration Method
```python
# New configuration method (automatically handled)
# Redis key configuration has been moved to individual components with unified naming convention
# crawlo:{PROJECT_NAME}:filter:fingerprint (request deduplication)
# crawlo:{PROJECT_NAME}:item:fingerprint (data item deduplication)
```

## 9. Best Practices

1. **Use PROJECT_NAME configuration item**: Explicitly set the project name in settings.py
2. **Avoid manual Redis key configuration**: Let the framework automatically generate Redis keys
3. **Regularly clean up Redis data**: Clean up expired Redis data as needed
4. **Monitor Redis usage**: Pay attention to Redis memory usage and performance metrics
5. **Use validation tools**: Use Redis Key validation tools to ensure naming conventions are correct before deployment

## 10. Troubleshooting

### 10.1 Common Issues

1. **Key naming not compliant**:
   - Symptom: Redis operations fail or data is混乱
   - Solution: Use validation tools to check key naming and correct

2. **Project name mismatch**:
   - Symptom: Data confusion between different projects
   - Solution: Ensure each project's PROJECT_NAME configuration is unique

3. **Component type error**:
   - Symptom: Function abnormality or data loss
   - Solution: Check if component type is correct (filter, queue, item)

### 10.2 Debugging Tips

1. **Use Redis CLI to view Keys**:
   ```bash
   redis-cli KEYS "crawlo:*"
   ```

2. **Monitor Redis memory usage**:
   ```bash
   redis-cli INFO memory
   ```

3. **Enable debug logging**:
   ```python
   FILTER_DEBUG = True
   LOG_LEVEL = 'DEBUG'
   ```