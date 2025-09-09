# Books Distributed Crawling Project

This is a distributed crawling project built with the Crawlo framework, equivalent to the Scrapy project that scrapes books from books.toscrape.com.

## Project Structure

```
books_distributed/
├── crawlo.cfg                 # Project configuration file
├── init_redis.py             # Script to initialize Redis queue
├── run.py                    # Script to run the spider
├── analyze_duplicates.py     # Script to analyze duplicate URLs
├── requirements.txt          # Required Python packages
└── books_distributed/        # Project package
    ├── __init__.py
    ├── items.py              # Data item definitions
    ├── pipelines.py          # Data processing pipelines
    ├── settings.py           # Project configuration
    ├── items/                # Items package (empty)
    ├── pipelines/            # Pipelines package (empty)
    └── spiders/              # Spider implementations
        ├── __init__.py
        └── books.py          # Books spider implementation
```

## Features

- Distributed crawling using Redis for queue management and deduplication
- High concurrency support
- Multi-node collaborative crawling
- URL logging with instance-specific log files
- Configurable retry mechanism
- Detailed logging and statistics

## Requirements

- Python 3.8+
- Redis server
- Crawlo framework
- Required Python packages (see requirements.txt)

## Setup

1. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure Redis:
   - If your Redis server requires authentication, update the `REDIS_PASSWORD` in both:
     - `init_redis.py` 
     - `books_distributed/settings.py`
   - If your Redis server doesn't require authentication, leave `REDIS_PASSWORD` as an empty string

3. Start Redis server:
   ```bash
   redis-server
   ```

4. Initialize Redis queue with start URLs:
   ```bash
   python init_redis.py
   ```

## Running the Spider

You can run the spider in several ways:

1. Using the run script:
   ```bash
   python run.py
   ```

2. Using crawlo command:
   ```bash
   crawlo run books
   ```

## Configuration

The project configuration is in `books_distributed/settings.py`. Key settings include:

- `RUN_MODE = 'distributed'`: Enables distributed mode
- `QUEUE_TYPE = 'redis'`: Uses Redis for queue management
- `FILTER_CLASS`: Uses Redis-based deduplication
- `CONCURRENCY = 16`: Sets high concurrency for distributed crawling
- Redis connection settings for queue and deduplication

## Distributed Operation

To run multiple instances of the spider on different nodes:

1. Ensure all nodes can access the same Redis server
2. Run the spider on each node:
   ```bash
   crawlo run books
   ```

Each instance will:
- Generate a unique instance ID
- Process URLs from the shared Redis queue
- Log processed URLs to instance-specific files
- Participate in distributed deduplication

## Output

- Console output of scraped data
- Instance-specific URL log files (`instance_{ID}_urls.log`)
- Detailed logging to `logs/books_distributed.log`
- Statistics output during and after crawling

## Analyzing Results

After crawling, you can analyze for duplicate URLs using:
```bash
python analyze_duplicates.py
```

This will check if multiple instances processed the same URLs, which should be prevented by the distributed deduplication system.

## Customization

You can customize the spider by modifying:
- `books_distributed/spiders/books.py`: Spider logic
- `books_distributed/items.py`: Data item definitions
- `books_distributed/pipelines.py`: Data processing pipelines
- `books_distributed/settings.py`: Project configuration