# startproject Command

The `startproject` command initializes a new Crawlo crawler project, creating the basic directory structure and configuration files.

## Usage

```bash
crawlo startproject <project_name> [template_type] [--modules module1,module2]
```

### Parameter Description

- `project_name`: Project name, must be a valid Python identifier
- `template_type`: Optional, template type (default: default)
- `--modules`: Optional, select modules to include

## Template Types

Crawlo provides several predefined templates to meet different scenario requirements:

### default (Default Template)
General configuration suitable for most projects. Contains complete configuration options and best practice settings.

### simple (Simple Template)
Minimal configuration for quick start. Contains only the most basic configuration items for easy onboarding.

### distributed (Distributed Template)
Optimized for distributed crawling. Pre-configured with Redis queue and deduplication filter, suitable for large-scale data collection.

### high-performance (High-Performance Template)
Optimized for large-scale high-concurrency scenarios. Uses high-performance downloaders and optimized concurrency settings.

### gentle (Gentle Template)
Low-load configuration that is friendly to target websites. Uses lower concurrency and longer request delays.

## Module Components

Use the `--modules` parameter to selectively include specific functional modules:

- `mysql`: MySQL database support
- `mongodb`: MongoDB database support
- `redis`: Redis support (distributed queue and deduplication)
- `proxy`: Proxy support
- `monitoring`: Monitoring and performance analysis
- `dedup`: Deduplication functionality
- `httpx`: HttpX downloader
- `aiohttp`: AioHttp downloader
- `curl`: CurlCffi downloader

## Usage Examples

### Create a Default Project
```bash
crawlo startproject my_spider_project
```

### Create a Distributed Project
```bash
crawlo startproject news_crawler distributed
```

### Create a High-Performance Project with MySQL and Proxy Support
```bash
crawlo startproject ecommerce_spider high-performance --modules mysql,proxy
```

### Create a Simple Project with MongoDB Support
```bash
crawlo startproject simple_spider simple --modules mongodb
```

## Project Structure

Projects created using the `startproject` command have the following standard structure:

```
project_name/
├── crawlo.cfg                 # Project configuration file
├── run.py                     # Project startup script
├── logs/                      # Log directory
├── output/                    # Data output directory
└── project_name/              # Project package
    ├── __init__.py            # Package initialization file
    ├── settings.py            # Project configuration (generated based on template type)
    ├── items.py               # Data structure definitions
    ├── middlewares.py         # Middlewares
    ├── pipelines.py           # Data pipelines
    └── spiders/               # Spider directory
        └── __init__.py        # Spider package initialization file
```

## run.py Startup Script Description

The `run.py` file in the project root directory is a simplified crawler startup script that users can run directly:

```bash
python run.py
```

This script has the following features:

1. **Automatic Configuration Loading**: The script automatically finds and loads the project's configuration file
2. **Fixed Spider Execution**: By default, it runs a spider named `your_spider_name`
3. **Simplified Design**: The code is concise and easy to understand and modify

Usage:
1. Open the `run.py` file
2. Replace `'your_spider_name'` with the actual spider name you want to run
3. Run the command `python run.py`

Note: If you need more complex running options (such as running multiple spiders, custom configurations, etc.), it is recommended to use the command-line tool:
```bash
crawlo run spider_name
```

## Configuration File Description

Regardless of the template type chosen, the generated configuration file is uniformly named `settings.py`, but the content will be adjusted accordingly based on the template type:

- **default template**: Contains complete configuration options and detailed comments
- **simple template**: Contains only the most basic configuration items
- **distributed template**: Pre-configured Redis settings required for distributed crawling
- **high-performance template**: Optimized high-performance configuration
- **gentle template**: Low-load, website-friendly configuration

## Best Practices

1. **Choose the Right Template**: Select the most appropriate template type based on project requirements
2. **Modular Building**: Use the `--modules` parameter to include only the required functional components
3. **Configuration Adjustment**: Adjust the `settings.py` configuration according to specific needs after project creation
4. **Version Control**: Include the project in a version control system for management

## Troubleshooting

### Project Name Validation
Project names must meet the following requirements:
- Start with a lowercase letter
- Contain only lowercase letters, numbers, and underscores
- Be a valid Python identifier
- Not be a Python keyword

### Template Type Error
If an unsupported template type is specified, the command will display a list of available template types.

### Directory Already Exists
If the target directory already exists, the command will prompt to choose a different project name or delete the existing directory.