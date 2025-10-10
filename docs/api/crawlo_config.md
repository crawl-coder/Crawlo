# crawlo.config

Configuration management module for the Crawlo framework.

## Overview

The configuration module provides a unified way to manage framework settings. It supports multiple configuration sources and provides validation capabilities.

## Classes

### Config

Main configuration class that manages framework settings.

#### Methods

##### `__init__(self, settings=None)`

Initialize the configuration object.

**Parameters:**
- `settings` (dict, optional): Initial settings dictionary

##### `get(self, key, default=None)`

Get a configuration value by key.

**Parameters:**
- `key` (str): Configuration key
- `default` (any, optional): Default value if key not found

**Returns:**
- Configuration value or default

##### `set(self, key, value)`

Set a configuration value.

**Parameters:**
- `key` (str): Configuration key
- `value` (any): Configuration value

##### `update(self, settings)`

Update configuration with a dictionary.

**Parameters:**
- `settings` (dict): Settings to update

##### `validate(self)`

Validate configuration settings.

**Returns:**
- bool: True if validation passes

## Usage Example

```python
from crawlo.config import Config

# Create configuration
config = Config({
    'DOWNLOAD_DELAY': 1.0,
    'CONCURRENT_REQUESTS': 16,
    'USER_AGENT': 'Crawlo/1.0'
})

# Get configuration values
delay = config.get('DOWNLOAD_DELAY')
concurrent = config.get('CONCURRENT_REQUESTS')

# Set configuration values
config.set('DOWNLOAD_DELAY', 2.0)

# Update with dictionary
config.update({
    'RETRY_TIMES': 3,
    'RETRY_HTTP_CODES': [500, 502, 503, 504]
})
```