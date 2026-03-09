#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2025-09-10 22:00
# @Author  : crawl-coder
# @Desc    : Crawlo 框架通用工具包（供用户使用）

注意：此模块包含预制的通用工具，供用户在编写爬虫时使用。
框架本身并不使用这些工具，它们完全独立于框架核心逻辑。
"""

# 日期工具
from .text.date_tools import (
    TimeUtils,
    parse_time,
    format_time,
    time_diff,
    to_timestamp,
    to_datetime,
    now,
    to_timezone,
    to_utc,
    to_local,
    from_timestamp_with_tz
)

# 数据清洗工具
from .text.text_cleaner import (
    TextCleaner,
    remove_html_tags,
    decode_html_entities,
    remove_extra_whitespace,
    remove_special_chars,
    normalize_unicode,
    clean_text,
    extract_numbers,
    extract_emails,
    extract_urls
)

# 分布式协调工具
from .distributed.distributed_coordinator import (
    TaskDistributor,
    DeduplicationTool,
    DistributedCoordinator,
    generate_task_id,
    claim_task,
    report_task_status,
    get_cluster_info,
    generate_pagination_tasks,
    distribute_tasks
)

# 附件下载工具
from .attachment_downloader import (
    AttachmentDownloader,
)

# 监控工具
from .monitor.performance_monitor import PerformanceMonitor

__all__ = [
    # 日期工具
    "TimeUtils",
    "parse_time",
    "format_time",
    "time_diff",
    "to_timestamp",
    "to_datetime",
    "now",
    "to_timezone",
    "to_utc",
    "to_local",
    "from_timestamp_with_tz",
    
    # 数据清洗工具
    "TextCleaner",
    "remove_html_tags",
    "decode_html_entities",
    "remove_extra_whitespace",
    "remove_special_chars",
    "normalize_unicode",
    "clean_text",
    "extract_numbers",
    "extract_emails",
    "extract_urls",
    
    # 分布式协调工具
    "TaskDistributor",
    "DeduplicationTool",
    "DistributedCoordinator",
    "generate_task_id",
    "claim_task",
    "report_task_status",
    "get_cluster_info",
    "generate_pagination_tasks",
    "distribute_tasks",
    
    # 附件下载工具
    "AttachmentDownloader",
    
    # 监控工具
    "PerformanceMonitor"
]
