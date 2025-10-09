# run Command

The `run` command runs the specified spider and is the main command for executing crawler tasks.

## Command Syntax

```bash
crawlo run <spider_name> [options]
```

### Parameter Description

- `spider_name` - The name of the spider to run (required)
- `options` - Optional parameters

## Command Line Arguments

The `crawlo run` command supports the following arguments:

- `<spider_name>` - The name of the spider to run, use `all` to run all spiders
- `--json` - Output results in JSON format
- `--no-stats` - Don't record statistics
- `--log-level LEVEL` - Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--concurrency NUM` - Set concurrency level

## Usage Examples

```
# Run a specific spider
crawlo run myspider

# Run all spiders
crawlo run all

# Output results in JSON format
crawlo run myspider --json

# Set log level to DEBUG
crawlo run myspider --log-level DEBUG

# Set concurrency to 32
crawlo run myspider --concurrency 32

# Combine multiple arguments
crawlo run myspider --log-level DEBUG --concurrency 32 --json
```

### Advanced Configuration

```
# Set concurrency
crawlo run myspider --concurrency 32

# Set download delay
crawlo run myspider --download-delay 1.0

# Set timeout
crawlo run myspider --download-timeout 60
```

## Configuration Options

The `run` command supports the following options:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| --config | string | 'settings.py' | Configuration file path |
| --log-level | string | 'INFO' | Log level (DEBUG, INFO, WARNING, ERROR) |
| --log-file | string | None | Log file path |
| --concurrency | int | 16 | Concurrent requests |
| --download-delay | float | 0.5 | Download delay (seconds) |
| --download-timeout | int | 30 | Download timeout (seconds) |
| --max-retry-times | int | 3 | Maximum retry times |
| --output-format | string | 'json' | Output format (json, csv, xml) |
| --output-file | string | None | Output file path |
| --stats | flag | - | Show statistics |
| --dry-run | flag | - | Dry run mode, don't actually execute requests |

## Environment Variables

The `run` command supports the following environment variables:

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| CRAWLO_CONFIG | 'settings.py' | Configuration file path |
| CRAWLO_LOG_LEVEL | 'INFO' | Log level |
| CRAWLO_CONCURRENCY | 16 | Concurrent requests |
| CRAWLO_DOWNLOAD_DELAY | 0.5 | Download delay |
| CRAWLO_PROJECT_DIR | Current directory | Project directory path |

## Use Cases

### 1. Development Testing

```
# Run spider during development
crawlo run myspider --log-level DEBUG --concurrency 1

# Test specific functionality
crawlo run myspider --dry-run --stats
```

### 2. Production Deployment

```
# Run spider in production environment
crawlo run myspider --config production_settings.py --log-file logs/myspider.log

# High-performance mode
crawlo run myspider --concurrency 50 --download-delay 0.1
```

### 3. Scheduled Tasks

```
# Use in crontab
0 2 * * * cd /path/to/project && crawlo run myspider --config daily_settings.py

# Scheduled task with output
0 3 * * * cd /path/to/project && crawlo run myspider --output-file data/$(date +\%Y-\%m-\%d).json
```

## Output Formats

### JSON Format

```
# Output to JSON file
crawlo run myspider --output-format json --output-file output.json
```

### CSV Format

```
# Output to CSV file
crawlo run myspider --output-format csv --output-file output.csv
```

### Custom Format

```
# Use custom pipeline
crawlo run myspider --pipeline myproject.pipelines.CustomPipeline
```

## Monitoring and Statistics

### Real-time Statistics

```
# Show real-time statistics
crawlo run myspider --stats

# Periodically output statistics
crawlo run myspider --stats-interval 30
```

### Performance Monitoring

```
# Enable performance monitoring
crawlo run myspider --monitor-performance

# Set memory usage warning threshold
crawlo run myspider --memory-warning-threshold 500
```

## Best Practices

### 1. Configuration Management

```
# Use different configurations for different environments
crawlo run myspider --config settings_dev.py      # Development environment
crawlo run myspider --config settings_test.py     # Testing environment
crawlo run myspider --config settings_prod.py     # Production environment
```

### 2. Log Management

```
# Properly configure logs
crawlo run myspider --log-level INFO --log-file logs/myspider.log --log-max-bytes 10485760 --log-backup-count 5
```

### 3. Resource Control

```
# Adjust resources based on target website
crawlo run myspider --concurrency 5 --download-delay 2.0      # Friendly to sensitive websites
crawlo run myspider --concurrency 50 --download-delay 0.1     # For high-performance websites
```

### 4. Error Handling

```
# Set retry mechanism
crawlo run myspider --max-retry-times 5 --retry-http-codes 500,502,503,504,429
```

## Troubleshooting

### Common Issues

1. **Spider Not Found**
   ```bash
   # Error: Spider not found
   # Solution: Check spider name and project structure
   crawlo list  # View available spiders
   ```

2. **Configuration File Error**
   ```bash
   # Error: Configuration error
   # Solution: Check configuration file syntax
   python -m py_compile settings.py
   ```

3. **Permission Error**
   ```bash
   # Error: Permission denied
   # Solution: Check file permissions
   chmod 644 settings.py
   ```

### Debugging Tips

```bash
# Enable verbose logging
crawlo run myspider --log-level DEBUG

# Dry run mode to check configuration
crawlo run myspider --dry-run --stats

# Single concurrency debugging
crawlo run myspider --concurrency 1 --log-level DEBUG
```