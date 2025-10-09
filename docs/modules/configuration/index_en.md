# Configuration System

Crawlo provides a powerful and flexible configuration management system that supports multiple configuration methods and validation mechanisms to ensure stable framework operation.

## Configuration Methods

Crawlo supports multiple configuration methods, and users can choose the most suitable method according to their needs:

### 1. Code Configuration

Create configurations through static factory methods of the [CrawloConfig](../../api/crawlo_config.md) class:

```python
from crawlo.config import CrawloConfig

# Standalone mode configuration
config = CrawloConfig.standalone(
    project_name='my_project',
    concurrency=10,
    download_delay=1.0
)

# Distributed mode configuration
config = CrawloConfig.distributed(
    project_name='my_project',
    redis_host='127.0.0.1',
    redis_port=6379,
    concurrency=20
)
```

### 2. Configuration Files

Create a `settings.py` file to define configurations:

```python
# settings.py
PROJECT_NAME = 'my_project'
CONCURRENCY = 10
DOWNLOAD_DELAY = 1.0
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
```

### 3. Environment Variables

Configure key parameters through environment variables:

```bash
export CRAWLO_CONCURRENCY=20
export CRAWLO_DOWNLOAD_DELAY=0.5
export CRAWLO_REDIS_HOST=192.168.1.100
```

## Configuration Priority

Crawlo uses the following configuration priority order (from highest to lowest):

1. **Code Configuration** - Configurations set directly through the CrawloConfig class
2. **Environment Variables** - System environment variables
3. **Configuration Files** - Configurations in the settings.py file
4. **Default Configuration** - Built-in default configurations of the framework

## Core Configuration Items

### Basic Configuration

| Configuration Item | Type | Default Value | Description |
|-------------------|------|---------------|-------------|
| PROJECT_NAME | str | 'crawlo_project' | Project name |
| VERSION | str | '1.0.0' | Project version |
| CONCURRENCY | int | 16 | Concurrent requests |
| DOWNLOAD_DELAY | float | 0.5 | Download delay (seconds) |
| DOWNLOAD_TIMEOUT | int | 30 | Download timeout (seconds) |
| MAX_RETRY_TIMES | int | 3 | Maximum retry times |

### Queue Configuration

| Configuration Item | Type | Default Value | Description |
|-------------------|------|---------------|-------------|
| QUEUE_TYPE | str | 'memory' | Queue type (memory/redis) |
| SCHEDULER_MAX_QUEUE_SIZE | int | 10000 | Maximum scheduler queue size |
| REDIS_HOST | str | '127.0.0.1' | Redis host address |
| REDIS_PORT | int | 6379 | Redis port |
| REDIS_PASSWORD | str | None | Redis password |
| REDIS_DB | int | 0 | Redis database number |

### Storage Configuration

| Configuration Item | Type | Default Value | Description |
|-------------------|------|---------------|-------------|
| MYSQL_HOST | str | '127.0.0.1' | MySQL host address |
| MYSQL_PORT | int | 3306 | MySQL port |
| MYSQL_USER | str | 'root' | MySQL username |
| MYSQL_PASSWORD | str | '' | MySQL password |
| MYSQL_DATABASE | str | 'crawlo' | MySQL database name |
| MONGO_URI | str | 'mongodb://127.0.0.1:27017' | MongoDB connection URI |

### Logging Configuration

| Configuration Item | Type | Default Value | Description |
|-------------------|------|---------------|-------------|
| LOG_LEVEL | str | 'INFO' | Log level |
| LOG_FILE | str | None | Log file path |
| LOG_MAX_BYTES | int | 10*1024*1024 | Maximum log file size |
| LOG_BACKUP_COUNT | int | 5 | Number of log file backups |

## Configuration Validation

Crawlo has built-in configuration validation mechanisms to ensure configuration correctness and completeness.

### Validator

The [ConfigValidator](../../api/crawlo_config_validator.md) class provides comprehensive configuration validation functionality:

```python
from crawlo.config_validator import validate_config, print_validation_report

# Validate configuration
is_valid, errors, warnings = validate_config(settings_dict)

if not is_valid:
    print(f"Configuration validation failed, found {len(errors)} errors")
    for error in errors:
        print(f"❌ {error}")
else:
    print("Configuration validation passed")

# Print detailed validation report
print_validation_report(settings_dict)
```

### Validation Content

The configuration validator checks the following content:

1. **Basic Settings Validation** - Checks basic configuration items like project name and version
2. **Network Settings Validation** - Validates network-related parameters like download timeout, delay, and retry times
3. **Concurrency Settings Validation** - Ensures concurrency is a positive integer
4. **Queue Settings Validation** - Checks the validity of queue type
5. **Storage Settings Validation** - Validates database-related configurations
6. **Redis Settings Validation** - Validates Redis configurations when using Redis queues
7. **Middleware and Pipeline Validation** - Ensures middleware and pipeline configurations are list types
8. **Logging Settings Validation** - Validates that log level is a valid value

## Redis Key Naming Convention

To ensure unified and maintainable key names in Redis, Crawlo recommends using the following naming convention:

```python
# Recommended Redis Key Naming Convention
crawlo:{PROJECT_NAME}:queue:requests     # Request queue
crawlo:{PROJECT_NAME}:item:fingerprint   # Data item deduplication
crawlo:{PROJECT_NAME}:queue:processing   # Processing queue
crawlo:{PROJECT_NAME}:queue:failed       # Failed queue
```

## Best Practices

### Configuration Management Recommendations

1. **Development Environment** - Use code configuration or simple configuration files
2. **Testing Environment** - Use configuration files, override key parameters through environment variables
3. **Production Environment** - Use a combination of configuration files and environment variables, pass sensitive information through environment variables

### Security Configuration

1. **Sensitive Information** - Sensitive information like passwords should be configured through environment variables
2. **Access Control** - Configuration files should have appropriate file permissions
3. **Backup Strategy** - Important configurations should be backed up regularly

### Performance Tuning

1. **Concurrency Settings** - Adjust concurrency based on the target website's capacity
2. **Delay Settings** - Set download delays appropriately to avoid putting pressure on the target website
3. **Timeout Settings** - Adjust timeout times based on network environment