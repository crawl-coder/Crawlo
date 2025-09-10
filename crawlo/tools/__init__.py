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
from ..cleaners import (
    TextCleaner,
    DataFormatter,
    EncodingConverter,
    remove_html_tags,
    decode_html_entities,
    remove_extra_whitespace,
    remove_special_chars,
    normalize_unicode,
    clean_text,
    extract_numbers,
    extract_emails,
    extract_urls,
    format_number,
    format_currency,
    format_percentage,
    format_phone_number,
    format_chinese_id_card,
    capitalize_words,
    detect_encoding,
    to_utf8,
    convert_encoding
)

# 数据验证工具封装
from .data_validator import (
    DataValidator,
    validate_email,
    validate_phone,
    validate_url,
    validate_chinese_id_card,
    validate_date,
    validate_number_range,
    check_data_integrity
)

# 重试机制封装
from .retry_mechanism import (
    RetryMechanism,
    retry,
    should_retry,
    exponential_backoff
)

# 反爬虫应对工具
from .anti_crawler import (
    ProxyPoolManager,
    CaptchaHandler,
    AntiCrawler,
    get_random_user_agent,
    rotate_proxy,
    handle_captcha,
    detect_rate_limiting
)

# 带认证代理工具
from .authenticated_proxy import (
    AuthenticatedProxy,
    create_proxy_config,
    format_proxy_for_request,
    parse_proxy_url,
    validate_proxy_url,
    get_proxy_info
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
    "DataFormatter",
    "EncodingConverter",
    "remove_html_tags",
    "decode_html_entities",
    "remove_extra_whitespace",
    "remove_special_chars",
    "normalize_unicode",
    "clean_text",
    "extract_numbers",
    "extract_emails",
    "extract_urls",
    "format_number",
    "format_currency",
    "format_percentage",
    "format_phone_number",
    "format_chinese_id_card",
    "capitalize_words",
    "detect_encoding",
    "to_utf8",
    "convert_encoding",
    
    # 数据验证工具
    "DataValidator",
    "validate_email",
    "validate_phone",
    "validate_url",
    "validate_chinese_id_card",
    "validate_date",
    "validate_number_range",
    "check_data_integrity",
    
    # 重试机制封装
    "RetryMechanism",
    "retry",
    "should_retry",
    "exponential_backoff",
    
    # 反爬虫应对工具
    "ProxyPoolManager",
    "CaptchaHandler",
    "AntiCrawler",
    "get_random_user_agent",
    "rotate_proxy",
    "handle_captcha",
    "detect_rate_limiting",
    
    # 带认证代理工具
    "AuthenticatedProxy",
    "create_proxy_config",
    "format_proxy_for_request",
    "parse_proxy_url",
    "validate_proxy_url",
    "get_proxy_info",
    
    # 分布式协调工具
    "TaskDistributor",
    "DeduplicationTool",
    "DistributedCoordinator",
    "generate_task_id",
    "claim_task",
    "report_task_status",
    "get_cluster_info",
    "generate_pagination_tasks",
    "distribute_tasks"
]