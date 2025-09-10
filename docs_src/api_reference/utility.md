# Utility API Reference

This document provides detailed information about the utility components in the Crawlo framework.

## Logging Utilities

### Module: crawlo.utils.log

Utilities for logging in the Crawlo framework.

```python
def get_logger(name, level=None, format=None, file=None):
    # Get a configured logger
    pass

def setup_logger(name, level=None, format=None, file=None):
    # Set up a logger with the specified configuration
    pass
```

#### Functions

##### `get_logger(name, level=None, format=None, file=None)`
Get a configured logger with the specified name and optional configuration.

**Parameters:**
- `name` (str): The name of the logger.
- `level` (str, optional): The logging level (e.g., 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL').
- `format` (str, optional): The logging format string.
- `file` (str, optional): The file to log to.

**Returns:**
- `Logger`: A configured logger instance.

##### `setup_logger(name, level=None, format=None, file=None)`
Set up a logger with the specified configuration.

**Parameters:**
- `name` (str): The name of the logger.
- `level` (str, optional): The logging level.
- `format` (str, optional): The logging format string.
- `file` (str, optional): The file to log to.

**Returns:**
- `Logger`: A configured logger instance.

## Request Utilities

### Module: crawlo.utils.request

Utilities for working with requests in the Crawlo framework.

```python
def request_fingerprint(request):
    # Generate a fingerprint for a request
    pass

def referer_str(request):
    # Get the referer string for a request
    pass
```

#### Functions

##### `request_fingerprint(request)`
Generate a unique fingerprint for a request based on its URL, method, and body.

**Parameters:**
- `request` (Request): The request to fingerprint.

**Returns:**
- `str`: A unique fingerprint for the request.

##### `referer_str(request)`
Get the referer string for a request.

**Parameters:**
- `request` (Request): The request to get the referer for.

**Returns:**
- `str`: The referer string.

## Request Serialization Utilities

### Module: crawlo.utils.request_serializer

Utilities for serializing and deserializing requests in the Crawlo framework.

```python
def request_to_dict(request, spider=None):
    # Convert a request to a dictionary
    pass

def request_from_dict(d, spider=None):
    # Create a request from a dictionary
    pass
```

#### Functions

##### `request_to_dict(request, spider=None)`
Convert a request to a dictionary representation.

**Parameters:**
- `request` (Request): The request to convert.
- `spider` (Spider, optional): The spider associated with the request.

**Returns:**
- `dict`: A dictionary representation of the request.

##### `request_from_dict(d, spider=None)`
Create a request from a dictionary representation.

**Parameters:**
- `d` (dict): The dictionary representation of the request.
- `spider` (Spider, optional): The spider associated with the request.

**Returns:**
- `Request`: A request created from the dictionary.

## Function Tools

### Module: crawlo.utils.func_tools

Utility functions for working with functions in the Crawlo framework.

```python
def get_func_name(func):
    # Get the name of a function
    pass

def get_func_code(func):
    # Get the code of a function
    pass
```

#### Functions

##### `get_func_name(func)`
Get the name of a function.

**Parameters:**
- `func` (callable): The function to get the name of.

**Returns:**
- `str`: The name of the function.

##### `get_func_code(func)`
Get the code of a function.

**Parameters:**
- `func` (callable): The function to get the code of.

**Returns:**
- `str`: The code of the function.

## Environment Configuration Utilities

### Module: crawlo.utils.env_config

Utilities for handling environment configuration in the Crawlo framework.

```python
def get_env_var(name, default=None, var_type=str):
    # Get an environment variable with type conversion
    pass

def get_redis_config():
    # Get Redis configuration from environment variables
    pass

def get_runtime_config():
    # Get runtime configuration from environment variables
    pass
```

#### Functions

##### `get_env_var(name, default=None, var_type=str)`
Get an environment variable with type conversion.

**Parameters:**
- `name` (str): The name of the environment variable.
- `default` (any, optional): The default value if the variable is not set.
- `var_type` (type, optional): The type to convert the variable to. Defaults to str.

**Returns:**
- `any`: The environment variable value converted to the specified type.

##### `get_redis_config()`
Get Redis configuration from environment variables.

**Returns:**
- `dict`: A dictionary containing Redis configuration.

##### `get_runtime_config()`
Get runtime configuration from environment variables.

**Returns:**
- `dict`: A dictionary containing runtime configuration.

## Error Handling Utilities

### Module: crawlo.utils.error_handler

Utilities for handling errors in the Crawlo framework.

```python
class ErrorHandler:
    def __init__(self, name, logger=None):
        # Initialize the error handler
        pass
    
    def handle_error(self, error, context="", raise_error=False):
        # Handle an error
        pass
    
    def get_error_history(self):
        # Get the error history
        pass
```

#### Class: ErrorHandler

##### `__init__(self, name, logger=None)`
Initialize the error handler with a name and optional logger.

**Parameters:**
- `name` (str): The name of the error handler.
- `logger` (Logger, optional): The logger to use for logging errors.

##### `handle_error(self, error, context="", raise_error=False)`
Handle an error by logging it and optionally raising it.

**Parameters:**
- `error` (Exception): The error to handle.
- `context` (str, optional): Additional context information.
- `raise_error` (bool, optional): Whether to re-raise the error. Defaults to False.

##### `get_error_history(self)`
Get the error history.

**Returns:**
- `list`: A list of error records.

## Redis Key Validation Utilities

### Module: crawlo.utils.redis_key_validator

Utilities for validating Redis key naming conventions in the Crawlo framework.

```python
def validate_redis_key_naming(key, project_name):
    # Validate Redis key naming convention
    pass

def validate_redis_key_structure(key):
    # Validate Redis key structure
    pass
```

#### Functions

##### `validate_redis_key_naming(key, project_name)`
Validate that a Redis key follows the naming convention.

**Parameters:**
- `key` (str): The Redis key to validate.
- `project_name` (str): The expected project name.

**Returns:**
- `bool`: True if the key follows the naming convention, False otherwise.

##### `validate_redis_key_structure(key)`
Validate the structure of a Redis key.

**Parameters:**
- `key` (str): The Redis key to validate.

**Returns:**
- `bool`: True if the key has a valid structure, False otherwise.

## Configuration Validator

### Module: crawlo.config_validator

Utilities for validating configuration in the Crawlo framework.

```python
class ConfigValidator:
    def __init__(self):
        # Initialize the configuration validator
        pass
    
    def validate(self, config):
        # Validate a configuration
        pass
```

#### Class: ConfigValidator

##### `__init__(self)`
Initialize the configuration validator.

##### `validate(self, config)`
Validate a configuration dictionary.

**Parameters:**
- `config` (dict): The configuration to validate.

**Returns:**
- `tuple`: A tuple containing (is_valid, errors, warnings) where:
  - `is_valid` (bool): Whether the configuration is valid
  - `errors` (list): A list of error messages
  - `warnings` (list): A list of warning messages

## Example Usage

```python
from crawlo.utils.log import get_logger
from crawlo.utils.request import request_fingerprint
from crawlo.utils.env_config import get_env_var, get_redis_config
from crawlo.utils.error_handler import ErrorHandler
from crawlo.utils.redis_key_validator import validate_redis_key_naming
from crawlo.config_validator import ConfigValidator

# Using logging utilities
logger = get_logger(__name__, level='INFO')

# Using request utilities
fingerprint = request_fingerprint(request)

# Using environment configuration utilities
redis_host = get_env_var('REDIS_HOST', 'localhost')
redis_config = get_redis_config()

# Using error handler
error_handler = ErrorHandler(__name__, logger)
try:
    # Some operation that might fail
    result = some_operation()
except Exception as e:
    error_handler.handle_error(e, "Executing some_operation")

# Using Redis key validator
is_valid = validate_redis_key_naming("crawlo:myproject:queue:requests", "myproject")

# Using configuration validator
validator = ConfigValidator()
config = {
    'PROJECT_NAME': 'test_project',
    'QUEUE_TYPE': 'redis',
    'REDIS_HOST': '127.0.0.1',
}
is_valid, errors, warnings = validator.validate(config)
```