# CLI Tools

Crawlo provides rich command-line tools to help users quickly create projects, generate spiders, run spiders, and manage spider tasks.

## Tools Overview

CLI tools adopt a modular design, with each command having specific functions, allowing users to complete complex spider management tasks through simple command-line operations.

### Core Commands

1. [startproject](startproject_en.md) - Create a new spider project
2. [genspider](genspider_en.md) - Generate a new spider template
3. [run](run_en.md) - Run a spider
4. [list](list_en.md) - List available spiders
5. [check](check_en.md) - Check project configuration
6. [stats](stats_en.md) - View spider statistics

## Installation and Usage

### Installation

CLI tools are installed together with the Crawlo framework:

```bash
pip install crawlo
```

### Basic Usage

After installation, all CLI tools can be accessed through the `crawlo` command:

```bash
# View help information
crawlo --help

# View help information for a specific command
crawlo <command> --help
```

## Command Details

### startproject

Create a new spider project.

```bash
# Create project
crawlo startproject myproject

# Create project to specified directory
crawlo startproject myproject /path/to/projects
```

### genspider

Generate a new spider template.

```bash
# Generate spider
crawlo genspider myspider example.com

# Generate spider to specified module
crawlo genspider myspider example.com --module mymodule
```

### run

Run a spider.

```bash
# Run spider
crawlo run myspider

# Run spider with specified configuration file
crawlo run myspider --config settings.py

# Run spider and set log level
crawlo run myspider --log-level DEBUG
```

### list

List all available spiders in the project.

```bash
# List all spiders
crawlo list

# List spiders in JSON format
crawlo list --format json
```

### check

Check project configuration and spider implementation.

```bash
# Check project
crawlo check

# Check specific spider
crawlo check myspider
```

### stats

View spider runtime statistics.

```bash
# View statistics
crawlo stats

# View statistics for specific spider
crawlo stats myspider
```

## Global Options

All CLI commands support the following global options:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| --help | flag | - | Show help information |
| --version | flag | - | Show version information |
| --config | string | 'settings.py' | Specify configuration file path |
| --log-level | string | 'INFO' | Set log level (DEBUG, INFO, WARNING, ERROR) |
| --project-dir | string | Current directory | Specify project directory |

## Usage Examples

### Create and Run Spider Project

```bash
# 1. Create new project
crawlo startproject myproject
cd myproject

# 2. Generate spider
crawlo genspider myspider example.com

# 3. Edit spider file
# Edit myproject/spiders/myspider.py

# 4. Run spider
crawlo run myspider

# 5. View statistics
crawlo stats
```

### Configuration Management

```bash
# Use different configuration files
crawlo run myspider --config production_settings.py

# Set debug mode
crawlo run myspider --log-level DEBUG

# Specify project directory
crawlo list --project-dir /path/to/myproject
```

## Environment Variables

CLI tools support the following environment variables:

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| CRAWLO_PROJECT_DIR | Current directory | Project directory path |
| CRAWLO_CONFIG | 'settings.py' | Configuration file path |
| CRAWLO_LOG_LEVEL | 'INFO' | Log level |
| CRAWLO_CONCURRENCY | 16 | Concurrent requests |
| CRAWLO_DOWNLOAD_DELAY | 0.5 | Download delay |

## Error Handling

### Common Errors

1. **Spider not found**
   ```bash
   crawlo run nonexistentspider
   # Error: Spider 'nonexistentspider' not found
   ```

2. **Configuration file error**
   ```bash
   crawlo run myspider --config bad_settings.py
   # Error: Configuration file 'bad_settings.py' format error
   ```

3. **Permission error**
   ```bash
   crawlo startproject myproject /root/projects
   # Error: No permission to create directory
   ```

### Debugging Tips

```bash
# Enable verbose logging
crawlo run myspider --log-level DEBUG

# Check configuration
crawlo check

# View available spiders
crawlo list
```

## Best Practices

### Project Structure Management

```bash
# Recommended project structure
myproject/
├── settings.py          # Main configuration file
├── spiders/             # Spider directory
│   ├── __init__.py
│   └── myspider.py
├── pipelines/           # Pipeline directory
│   ├── __init__.py
│   └── custom_pipeline.py
├── middlewares/         # Middleware directory
│   ├── __init__.py
│   └── custom_middleware.py
└── items/               # Item definitions
    ├── __init__.py
    └── myitem.py
```

### Configuration File Management

```bash
# Development environment configuration
crawlo run myspider --config settings_dev.py

# Testing environment configuration
crawlo run myspider --config settings_test.py

# Production environment configuration
crawlo run myspider --config settings_prod.py
```

### Log Management

```bash
# Set log level
crawlo run myspider --log-level INFO

# Output to file
crawlo run myspider --log-file crawler.log

# Set log rotation
crawlo run myspider --log-max-bytes 10485760 --log-backup-count 5
```

### Performance Tuning

```bash
# Adjust concurrency
crawlo run myspider --concurrency 32

# Set download delay
crawlo run myspider --download-delay 1.0

# Set timeout
crawlo run myspider --download-timeout 60
```