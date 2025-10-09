# check Command

The `check` command checks project configuration and spider implementation, helping to identify potential issues and errors.

## Command Syntax

```bash
crawlo check [spider_name] [options]
```

### Parameter Description

- `spider_name` - The spider name to check (optional, checks entire project if not specified)
- `options` - Optional parameters

## Usage Examples

### Basic Usage

```bash
# Check entire project
crawlo check

# Check specific spider
crawlo check myspider

# Specify project directory
crawlo check --project-dir /path/to/project
```

### Detailed Checking

```bash
# Show detailed information
crawlo check --verbose

# Show errors only
crawlo check --errors-only

# Generate check report
crawlo check --output report.txt
```

## Check Content

### 1. Configuration Check

```bash
# Check configuration file
crawlo check --check-config

# Check environment variables
crawlo check --check-env
```

Checked configuration items include:
- Project name and version
- Concurrency configuration
- Downloader configuration
- Queue and filter configuration
- Log configuration
- Pipeline and middleware configuration

### 2. Spider Check

```bash
# Check spider implementation
crawlo check --check-spiders

# Check specific spider
crawlo check myspider --check-spider
```

Checked spider items include:
- Spider name uniqueness
- Inheritance correctness
- Parse method implementation
- Request and item processing

### 3. Dependency Check

```bash
# Check dependencies
crawlo check --check-deps

# Check version compatibility
crawlo check --check-versions
```

## Configuration Options

The `check` command supports the following options:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| --project-dir | string | Current directory | Project directory path |
| --config | string | 'settings.py' | Configuration file path |
| --verbose | flag | - | Show detailed information |
| --quiet | flag | - | Quiet mode, show errors only |
| --errors-only | flag | - | Show error information only |
| --warnings-only | flag | - | Show warning information only |
| --check-config | flag | True | Check configuration file |
| --check-spiders | flag | True | Check spider implementation |
| --check-deps | flag | False | Check dependencies |
| --check-env | flag | False | Check environment variables |
| --output | string | None | Output report file path |
| --format | string | 'text' | Output format (text, json, xml) |

## Check Report

### Text Format (Default)

```bash
$ crawlo check
Checking project: myproject
Configuration check: Passed
Spider check: 
  - news_spider: Passed
  - product_spider: Warning - Missing description document
Dependency check: Passed

Total: 3 checks, 0 errors, 1 warning
```

### JSON Format

```bash
$ crawlo check --format json
{
  "project": "myproject",
  "timestamp": "2023-01-01T12:00:00Z",
  "checks": [
    {
      "type": "config",
      "status": "passed",
      "details": []
    },
    {
      "type": "spider",
      "name": "news_spider",
      "status": "passed",
      "details": []
    },
    {
      "type": "spider",
      "name": "product_spider",
      "status": "warning",
      "details": ["Missing description document"]
    }
  ],
  "summary": {
    "total": 3,
    "errors": 0,
    "warnings": 1
  }
}
```

## Common Check Items

### Configuration Check Items

```python
# Check configuration item types
CONCURRENCY = 16        # ✅ Correct
CONCURRENCY = "16"      # ❌ Error, should be integer

# Check required configuration items
PROJECT_NAME = "myproject"  # ✅ Required
# PROJECT_NAME missing    # ❌ Error, missing required item

# Check configuration value ranges
DOWNLOAD_DELAY = 0.5    # ✅ Correct range
DOWNLOAD_DELAY = -1     # ❌ Error, cannot be negative
```

### Spider Check Items

```python
# Check spider names
class MySpider(Spider):
    name = "my_spider"  # ✅ Correct
    
class AnotherSpider(Spider):
    # name missing       # ❌ Error, missing name

# Check method implementation
class MySpider(Spider):
    def parse(self, response):
        pass  # ✅ Correct implementation
        
class BadSpider(Spider):
    # Missing parse method  # ❌ Error, missing required method
```

### Dependency Check Items

```bash
# Check required dependencies
requests>=2.25.0    # ✅ Version requirement met
requests>=3.0.0     # ❌ Version requirement not met

# Check optional dependencies
selenium>=4.0.0     # ✅ Optional dependency, needed if used
# selenium missing   # ⚠️ Warning, needed if configured for use
```

## Best Practices

### 1. Development Stage Checking

```bash
# Regular checking during development
crawlo check --verbose

# Pre-commit checking
crawlo check --errors-only
```

### 2. CI/CD Integration

```bash
# Use in CI/CD pipeline
# .github/workflows/ci.yml
- name: Check Project
  run: |
    pip install -r requirements.txt
    crawlo check --errors-only
```

### 3. Configuration Validation

```bash
# Validate configuration before deployment
crawlo check --check-config --check-env

# Production environment configuration check
crawlo check --config production_settings.py
```

## Custom Check Rules

### Adding Custom Checkers

```python
# custom_checker.py
from crawlo.check import BaseChecker

class CustomChecker(BaseChecker):
    def check(self, project):
        """Custom checking logic"""
        issues = []
        
        # Check custom rules
        if not project.settings.get('CUSTOM_SETTING'):
            issues.append({
                'type': 'error',
                'message': 'Missing custom configuration item'
            })
        
        return issues
```

### Registering Custom Checkers

```python
# settings.py
CUSTOM_CHECKERS = [
    'myproject.checkers.CustomChecker'
]
```

## Troubleshooting

### Common Issues

1. **Configuration File Error**
   ```bash
   # Error: Configuration file not found
   # Solution: Check configuration file path
   crawlo check --config settings.py
   
   # Error: Invalid configuration syntax
   # Solution: Check configuration file syntax
   python -m py_compile settings.py
   ```

2. **Spider Implementation Error**
   ```bash
   # Error: Spider class not found
   # Solution: Check spider class definition and inheritance
   grep -r "class.*Spider" spiders/
   
   # Error: Missing required method
   # Solution: Implement required methods
   ```

3. **Dependency Issues**
   ```bash
   # Error: Missing dependency
   # Solution: Install missing dependencies
   pip install -r requirements.txt
   
   # Error: Version conflict
   # Solution: Update or downgrade dependency version
   pip install package==required_version
   ```

### Debugging Tips

```bash
# Show detailed checking process
crawlo check --verbose

# Focus on specific types of checks
crawlo check --check-config --verbose

# Generate detailed check report
crawlo check --output detailed_report.json --format json --verbose
```