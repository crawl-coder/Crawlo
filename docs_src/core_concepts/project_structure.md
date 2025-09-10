# Project Structure

A typical Crawlo project follows a well-organized structure that promotes maintainability and scalability.

## Default Project Structure

When you create a new project using `crawlo startproject`, the following structure is generated:

```
project_name/
├── crawlo.cfg              # Project configuration file
├── run.py                  # Main execution script
├── logs/                   # Log directory
├── project_name/           # Main Python package
│   ├── __init__.py         # Package initializer
│   ├── settings.py         # Configuration settings
│   ├── items.py            # Data item definitions
│   ├── middlewares.py      # Custom middlewares
│   ├── pipelines.py        # Data processing pipelines
│   └── spiders/            # Spider implementations
│       ├── __init__.py     # Spiders package initializer
│       └── *.py            # Individual spider files
```

## Key Files and Directories

### 1. crawlo.cfg

This file identifies the project root directory. It's essential for Crawlo to locate project files and configurations.

### 2. run.py

The main execution script that handles command-line arguments and starts the crawling process.

### 3. logs/

Directory for storing log files. The structure and naming of log files can be configured in `settings.py`.

### 4. project_name/

The main Python package containing all project-specific code.

#### __init__.py

Package initializer that makes the directory a Python package.

#### settings.py

Project configuration file where you define settings such as:
- Concurrency level
- Download delays
- Pipeline configurations
- Middleware configurations
- Redis settings (for distributed mode)

#### items.py

Data item definitions that specify the structure of the data you want to extract.

#### middlewares.py

Custom middleware implementations for request/response processing.

#### pipelines.py

Custom pipeline implementations for data processing and storage.

#### spiders/

Directory containing spider implementations.

##### __init__.py

Spiders package initializer.

##### *.py

Individual spider files, each containing one or more spider classes.

## Customizing Project Structure

While the default structure is recommended, you can customize it to suit your needs:

### 1. Multiple Spider Files

You can organize spiders into multiple files based on functionality:

```
spiders/
├── __init__.py
├── news_spiders.py
├── product_spiders.py
└── forum_spiders.py
```

### 2. Subdirectories for Complex Projects

For large projects, you can create subdirectories:

```
project_name/
├── __init__.py
├── settings.py
├── items/
│   ├── __init__.py
│   ├── news_items.py
│   └── product_items.py
├── spiders/
│   ├── __init__.py
│   ├── news/
│   │   ├── __init__.py
│   │   ├── local_news.py
│   │   └── international_news.py
│   └── products/
│       ├── __init__.py
│       ├── electronics.py
│       └── clothing.py
└── utils/
    ├── __init__.py
    └── helpers.py
```

## Best Practices

1. **Keep it organized**: Use a consistent naming convention and directory structure
2. **Separate concerns**: Keep items, spiders, and pipelines in their respective directories
3. **Use meaningful names**: Choose descriptive names for files and classes
4. **Document your structure**: Add comments to explain complex structures
5. **Version control**: Use version control systems like Git to track changes