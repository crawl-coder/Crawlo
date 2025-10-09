# list Command

The `list` command lists all available spiders in the project, helping users understand the project structure and available spiders.

## Command Syntax

```bash
crawlo list [options]
```

### Parameter Description

- `options` - Optional parameters

## Usage Examples

### Basic Usage

```bash
# List all spiders
crawlo list

# Specify project directory
crawlo list --project-dir /path/to/project

# Output in JSON format
crawlo list --format json
```

### Advanced Usage

```bash
# Verbose information
crawlo list --verbose

# Show spider names only
crawlo list --names-only

# Filter spiders
crawlo list --filter "news_*"
```

## Configuration Options

The `list` command supports the following options:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| --project-dir | string | Current directory | Project directory path |
| --format | string | 'table' | Output format (table, json, csv) |
| --verbose | flag | - | Show detailed information |
| --names-only | flag | - | Show spider names only |
| --filter | string | None | Spider name filter |
| --sort | string | 'name' | Sort method (name, created) |

## Output Formats

### Table Format (Default)

```bash
$ crawlo list
+----+-------------+------------------+------------+
| No | Spider Name | Description      | Created    |
+----+-------------+------------------+------------+
| 1  | news_spider | News website spider | 2023-01-01 |
| 2  | product_spider | Product info spider | 2023-01-02 |
+----+-------------+------------------+------------+
```

### JSON Format

```bash
$ crawlo list --format json
[
  {
    "name": "news_spider",
    "description": "News website spider",
    "created": "2023-01-01",
    "file": "spiders/news_spider.py"
  },
  {
    "name": "product_spider",
    "description": "Product info spider",
    "created": "2023-01-02",
    "file": "spiders/product_spider.py"
  }
]
```

### CSV Format

```bash
$ crawlo list --format csv
No,Spider Name,Description,Created,File Path
1,news_spider,News website spider,2023-01-01,spiders/news_spider.py
2,product_spider,Product info spider,2023-01-02,spiders/product_spider.py
```

## Spider Discovery Mechanism

### Auto Discovery

```python
# Configure spider modules in settings.py
SPIDER_MODULES = [
    'myproject.spiders',
    'myproject.custom_spiders',
]

# Spiders must inherit from Spider base class
class MySpider(Spider):
    name = 'my_spider'
```

### Naming Convention

```bash
# Recommended spider file naming
spiders/
├── news_spider.py          # News spider
├── product_spider.py       # Product spider
├── user_spider.py          # User spider
└── api_data_spider.py      # API data spider
```

## Detailed Information Display

### Using --verbose Option

```bash
$ crawlo list --verbose
Spider List:
  1. news_spider
     File: spiders/news_spider.py
     Class: NewsSpider
     Description: News website spider
     Created: 2023-01-01
     Last Modified: 2023-01-15

  2. product_spider
     File: spiders/product_spider.py
     Class: ProductSpider
     Description: Product info spider
     Created: 2023-01-02
     Last Modified: 2023-01-10
```

## Filtering and Sorting

### Name Filtering

```bash
# Filter spiders containing specific strings
crawlo list --filter "news"

# Use wildcard filtering
crawlo list --filter "news_*"

# Regular expression filtering
crawlo list --filter "^news.*spider$"
```

### Sorting Options

```bash
# Sort by name (default)
crawlo list --sort name

# Sort by creation time
crawlo list --sort created
```

## Best Practices

### 1. Project Structure Management

```bash
# Organize spiders by function
spiders/
├── news/
│   ├── cnn_spider.py
│   ├── bbc_spider.py
│   └── reuters_spider.py
├── ecommerce/
│   ├── amazon_spider.py
│   ├── ebay_spider.py
│   └── aliexpress_spider.py
└── social/
    ├── twitter_spider.py
    └── facebook_spider.py
```

### 2. Spider Naming Convention

```python
# Use descriptive spider names
class NewsSpider(Spider):           # ✅ Good
    name = 'news_spider'

class ProductSpider(Spider):        # ✅ Good
    name = 'product_spider'

class Spider1(Spider):              # ❌ Bad
    name = 'spider1'
```

### 3. Documenting Spiders

```python
class NewsSpider(Spider):
    """News website spider
    
    Used to crawl article content from news websites, including title, body, publication time, etc.
    
    Supported websites:
    - news.example.com
    - blog.example.com
    """
    name = 'news_spider'
```

## Troubleshooting

### Common Issues

1. **No Spiders Found**
   ```bash
   # Issue: No spiders found
   # Solution: Check spider module configuration and file structure
   # Ensure SPIDER_MODULES is configured in settings.py
   ```

2. **Spider Name Conflicts**
   ```bash
   # Issue: Duplicate spider names found
   # Solution: Ensure each spider has a unique name
   # Check name attribute in all spider files
   ```

3. **Permission Issues**
   ```bash
   # Issue: Permission denied
   # Solution: Check directory and file permissions
   ls -la spiders/
   ```

### Debugging Tips

```bash
# Show detailed information to debug issues
crawlo list --verbose

# Check specific project directory
crawlo list --project-dir /path/to/project --verbose

# Output in different formats for analysis
crawlo list --format json | jq '.[] | .name'
```