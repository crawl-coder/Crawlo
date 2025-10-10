# crawlo.config_validator

Configuration validation module for the Crawlo framework.

## Overview

The configuration validation module provides tools to validate framework settings. It ensures that configuration values meet the required criteria and formats.

## Classes

### ConfigValidator

Main configuration validator class.

#### Methods

##### `__init__(self)`

Initialize the configuration validator.

##### `add_rule(self, key, rule)`

Add a validation rule for a configuration key.

**Parameters:**
- `key` (str): Configuration key
- `rule` (callable): Validation function that takes a value and returns bool

##### `validate(self, config)`

Validate a configuration dictionary.

**Parameters:**
- `config` (dict): Configuration to validate

**Returns:**
- tuple: (is_valid, errors) where is_valid is a boolean and errors is a list of error messages

## Usage Example

```python
from crawlo.config_validator import ConfigValidator

# Create validator
validator = ConfigValidator()

# Add validation rules
validator.add_rule('DOWNLOAD_DELAY', lambda x: isinstance(x, (int, float)) and x >= 0)
validator.add_rule('CONCURRENT_REQUESTS', lambda x: isinstance(x, int) and x > 0)
validator.add_rule('USER_AGENT', lambda x: isinstance(x, str) and len(x) > 0)

# Validate configuration
config = {
    'DOWNLOAD_DELAY': 1.0,
    'CONCURRENT_REQUESTS': 16,
    'USER_AGENT': 'Crawlo/1.0'
}

is_valid, errors = validator.validate(config)
if not is_valid:
    print("Configuration errors:", errors)
```