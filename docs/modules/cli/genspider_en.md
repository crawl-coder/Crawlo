# genspider Command

The `genspider` command generates new spider templates, quickly creating the basic structure for spider classes.

## Command Syntax

```bash
crawlo genspider <spider_name> <domain> [options]
```

### Parameter Description

- `spider_name` - Spider name (required)
- `domain` - Target domain (required)
- `options` - Optional parameters

## Usage Examples

### Basic Usage

```bash
# Generate basic spider
crawlo genspider myspider example.com

# Specify module directory
crawlo genspider myspider example.com --module mymodule

# Generate spider to specified file
crawlo genspider myspider example.com --output myspider.py
```

## Spider Templates

### Default Template

The generated spider template contains basic structure:

```python
import crawlo
from crawlo.spider import Spider
from crawlo.items import Item

class MyspiderSpider(Spider):
    name = 'myspider'
    allowed_domains = ['example.com']
    start_urls = ['http://example.com/']

    def parse(self, response):
        # Parsing logic
        pass
```

### Custom Templates

```bash
# Use custom template
crawlo genspider myspider example.com --template advanced

# List available templates
crawlo genspider --list-templates
```

## Configuration Options

The `genspider` command supports the following options:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| --module | string | 'spiders' | Spider module directory |
| --output | string | - | Output file path |
| --template | string | 'default' | Template name to use |
| --list-templates | flag | - | List all available templates |
| --force | flag | - | Force overwrite existing file |
| --verbose | flag | - | Show verbose output |

## Template Types

### 1. Default Template (default)

```python
class SpiderName(Spider):
    name = 'spidername'
    start_urls = ['http://example.com/']
    
    def parse(self, response):
        pass
```

### 2. Advanced Template (advanced)

```python
class SpiderName(Spider):
    name = 'spidername'
    allowed_domains = ['example.com']
    start_urls = ['http://example.com/']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_setting = kwargs.get('custom_setting')
    
    def parse(self, response):
        # Extract data
        yield Item(data=response.text)
        
        # Follow links
        for link in response.extract_attrs('a', 'href'):
            yield Request(url=link, callback=self.parse)
```

### 3. API Template (api)

```python
class SpiderName(Spider):
    name = 'spidername'
    api_base_url = 'https://api.example.com'
    
    def start_requests(self):
        yield Request(
            url=f'{self.api_base_url}/data',
            headers={'Authorization': 'Bearer token'}
        )
    
    def parse(self, response):
        data = response.json()
        for item in data['items']:
            yield Item(**item)
```

## Best Practices

### 1. Spider Naming

```bash
# Use descriptive spider names
crawlo genspider product_spider example.com
crawlo genspider news_spider news.example.com
crawlo genspider user_spider social.example.com
```

### 2. Domain Configuration

```bash
# Properly configure domains
crawlo genspider myspider example.com
crawlo genspider myspider subdomain.example.com
crawlo genspider myspider example.com --allowed-domains example.com,api.example.com
```

### 3. Template Selection

```bash
# Choose appropriate template based on requirements
crawlo genspider myspider example.com --template default      # Simple spider
crawlo genspider myspider example.com --template advanced     # Complex spider
crawlo genspider myspider api.example.com --template api      # API spider
```

## Troubleshooting

### Common Issues

1. **File Already Exists**
   ```bash
   # Error: File already exists
   # Solution: Use --force option or choose another name
   crawlo genspider myspider example.com --force
   ```

2. **Template Not Found**
   ```bash
   # Error: Template not found
   # Solution: Check template name or use default template
   crawlo genspider myspider example.com --template default
   ```

3. **Module Directory Not Found**
   ```bash
   # Error: Module directory not found
   # Solution: Create directory or use existing directory
   mkdir mymodule
   crawlo genspider myspider example.com --module mymodule
   ```

### Debugging Tips

```bash
# Use verbose mode to see generation process
crawlo genspider myspider example.com --verbose

# Check template list
crawlo genspider --list-templates

# Preview generated content without creating file
crawlo genspider myspider example.com --dry-run
```