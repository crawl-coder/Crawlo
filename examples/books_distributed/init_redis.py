#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Initialize Redis queue with start URLs for the books spider
"""
import redis
import sys
import os

# Add the project root to sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def initialize_redis_queue():
    """Initialize Redis queue with start URLs"""
    # Redis configuration (should match settings.py)
    redis_host = '127.0.0.1'
    redis_port = 6379
    redis_db = 4
    redis_password = 'Oscar&0503'  # Local Redis password
    redis_key = 'books:start_urls'
    
    try:
        # Connect to Redis
        r = redis.Redis(
            host=redis_host, 
            port=redis_port, 
            db=redis_db, 
            password=redis_password,
            decode_responses=True
        )
        
        # Test connection
        r.ping()
        print("Connected to Redis successfully")
        
        # Clear existing queue
        r.delete(redis_key)
        
        # Add start URLs
        start_urls = [
            'http://books.toscrape.com/catalogue/page-1.html',
            'http://books.toscrape.com/catalogue/page-2.html',
            'http://books.toscrape.com/catalogue/page-3.html',
        ]
        
        for url in start_urls:
            r.lpush(redis_key, url)
            print(f"Added to queue: {url}")
        
        # Verify queue contents
        urls = r.lrange(redis_key, 0, -1)
        print(f"\nQueue '{redis_key}' initialized with {len(urls)} URLs:")
        for url in urls:
            print(f"  - {url}")
            
        print("\nRedis queue initialization completed successfully!")
        
    except redis.ConnectionError as e:
        print(f"Error connecting to Redis: {e}")
        print("Please make sure Redis server is running and accessible.")
        sys.exit(1)
    except Exception as e:
        print(f"Error initializing Redis queue: {e}")
        sys.exit(1)

if __name__ == '__main__':
    initialize_redis_queue()