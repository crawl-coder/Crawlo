# Quick Start

This guide will help you quickly get started with the Crawlo framework, create your first crawler project, and run it.

## Installing Crawlo

### Installing with pip

```bash
pip install crawlo
```

### Installing from source

```bash
git clone https://github.com/crawl-coder/Crawlo.git
cd crawlo
pip install -r requirements.txt
pip install .
```

## Creating Your First Project

Use Crawlo's command-line tool to create a new project:

```bash
crawlo startproject myproject
```

This will create the following project structure:

```
myproject/
├── crawlo.cfg           # Project configuration file
├── run.py               # Startup script
├── logs/                # Log directory
└── myproject/           # Project modules directory
    ├── __init__.py
    ├── settings.py       # Project configuration
    ├── items.py         # Data item definition
    ├── middlewares.py   # Middleware
    ├── pipelines.py     # Data pipeline
    └── spiders/         # Spider directory
        ├── __init__.py
        └── example.py   # Example spider
```

## Creating Your First Spider

Navigate to the project directory and generate a new spider:

```bash
cd myproject
crawlo genspider myspider example.com
```

This will create a new spider file `myspider.py` in the `spiders/` directory:

```python
from crawlo import Spider

class MyspiderSpider(Spider):
    name = 'myspider'
    
    def parse(self, response):
        # Implement parsing logic here
        pass
```

## Writing Spider Logic

Edit the `spiders/myspider.py` file and add your spider logic:

```python
from crawlo import Spider

class MyspiderSpider(Spider):
    name = 'myspider'
    start_urls = ['http://example.com']
    
    def parse(self, response):
        # Extract page title
        title = response.extract_text('title')
        
        # Extract all links
        links = response.extract_attrs('a', 'href')
        
        yield {
            'title': title,
            'links': links,
            'url': response.url
        }
        
        # Follow links to continue crawling
        for link in links:
            if link.startswith('http'):
                yield response.follow(link, callback=self.parse)
```

## Run the Spider

Navigate to the project directory and run the spider:

```bash
cd myproject
crawlo run example
```

You can also use the following arguments to control the spider execution:

```bash
# Set log level to DEBUG to see more detailed information
crawlo run example --log-level DEBUG

# Set concurrency to 32
crawlo run example --concurrency 32

# Combine multiple arguments
crawlo run example --log-level INFO --concurrency 16
```

## Viewing Results

After the spider finishes running, you can see the output results in the console, or view the stored data in the configured pipelines.

## Next Steps

- Learn more about the [Spider Base Class](../core/spider_en.md)
- Understand the usage of [Downloaders](../downloader/index_en.md)
- Explore the functionality of [Middleware](../middleware/index_en.md)
- Master the use of [Pipelines](../pipeline/index_en.md)