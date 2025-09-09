# -*- coding: utf-8 -*-
"""
Pipelines for processing BookItem
"""
import os
import uuid
from crawlo.pipelines import BasePipeline
from crawlo.utils.log import get_logger

logger = get_logger(__name__)


class URLLoggingPipeline(BasePipeline):
    """Pipeline to log processed URLs to instance-specific log files"""
    
    def __init__(self, crawler=None):
        self.instance_id = str(uuid.uuid4())[:8]
        self.log_file_path = f"instance_{self.instance_id}_urls.log"
        
        # Initialize log file
        with open(self.log_file_path, 'w', encoding='utf-8') as f:
            f.write(f"# Instance ID: {self.instance_id}\n")
            f.write("# URL, Status, Timestamp\n")
    
    @classmethod
    def from_crawler(cls, crawler):
        """Create pipeline instance from crawler"""
        return cls(crawler)
    
    async def process_item(self, item, spider):
        """Log the URL of processed items"""
        try:
            url = item.get('url', 'Unknown')
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(f"{url}, SUCCESS, {self.instance_id}\n")
        except Exception as e:
            logger.error(f"Failed to log URL: {e}")
        
        return item
    
    async def close_spider(self, spider):
        """Output log file path when spider closes"""
        abs_path = os.path.abspath(self.log_file_path)
        logger.info(f"URLs processed by this instance saved to: {abs_path}")
        logger.info("Please run analyze_duplicates.py script to check for duplicate crawls!")