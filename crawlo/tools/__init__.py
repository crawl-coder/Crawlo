#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2025-09-10 22:00
# @Author  : crawl-coder
# @Desc    : Crawlo框架工具包集合
"""

# 日期工具封装
from .date_tools import (
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

# 数据清洗工具封装
from .text_cleaner import (
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
from .distributed_coordinator import (
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
    "AttachmentDownloader"
]