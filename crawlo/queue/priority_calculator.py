#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
优先级计算器

基于域名/URL/响应时间/错误计数的多维度优先级计算，
内置内存淘汰机制防止统计字典无限增长。

"""

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from crawlo import Request


class PriorityCalculator:
    """优先级计算器

    管理请求优先级的多维度评分逻辑。内部维护多个统计字典，
    为防止长时间运行导致内存泄漏，url_stats 和 domain_stats
    有最大容量限制，超出时自动淘汰最旧的记录。
    """

    # 内存控制常量
    MAX_DOMAINS = 1000       # 最多跟踪 1000 个域名
    MAX_URLS = 10000         # 最多跟踪 10000 个 URL

    def __init__(self):
        self.domain_stats = {}  # 域名统计信息
        self.url_stats = {}  # URL统计信息
        self.last_request_time = {}  # 最后请求时间
        self.response_times = {}  # 响应时间统计
        self.error_counts = {}  # 错误计数
        self.content_type_preferences = {}  # 内容类型偏好
        self.crawl_frequency = {}  # 抓取频率统计

    def calculate_priority(self, request: "Request") -> int:
        """计算请求的智能优先级"""
        priority = getattr(request, 'priority', 0)

        # 获取域名
        domain = self._extract_domain(request.url)

        # 基于域名访问频率调整优先级
        if domain in self.domain_stats:
            domain_access_count = self.domain_stats[domain]['count']
            last_access_time = self.domain_stats[domain]['last_time']

            # 如果最近访问过该域名，降低优先级（避免过度集中访问同一域名）
            time_since_last = time.time() - last_access_time
            if time_since_last < 5:  # 5秒内访问过
                priority -= 2
            elif time_since_last < 30:  # 30秒内访问过
                priority -= 1

            # 如果该域名访问次数过多，进一步降低优先级
            if domain_access_count > 10:
                priority -= 1

        # 基于URL访问历史调整优先级
        if request.url in self.url_stats:
            url_access_count = self.url_stats[request.url]
            if url_access_count > 1:
                # 重复URL降低优先级
                priority -= url_access_count

        # 基于深度调整优先级
        depth = getattr(request, 'meta', {}).get('depth', 0)
        priority -= depth  # 深度越大，优先级越低

        # 基于响应时间调整优先级
        if domain in self.response_times:
            avg_response_time = sum(self.response_times[domain]) / len(self.response_times[domain])
            # 如果响应时间较长，适当降低优先级
            if avg_response_time > 5.0:  # 超过5秒
                priority -= 1
            elif avg_response_time < 1.0:  # 响应很快，提高优先级
                priority += 1

        # 基于错误计数调整优先级
        if domain in self.error_counts and self.error_counts[domain] > 3:
            # 如果错误较多，降低优先级
            priority -= min(self.error_counts[domain], 5)

        # 基于内容类型偏好调整优先级
        content_type = getattr(request, 'meta', {}).get('content_type', '')
        if content_type in ['html', 'json', 'xml']:
            # 这些内容类型通常更重要，提高优先级
            priority += 1

        # 基于抓取频率调整优先级
        if domain in self.crawl_frequency:
            freq_info = self.crawl_frequency[domain]
            if 'last_hour_count' in freq_info and freq_info['last_hour_count'] > 100:
                # 如果过去一小时抓取过多，降低优先级
                priority -= 1

        return priority

    def update_stats(self, request: "Request"):
        """更新统计信息（带内存控制）"""
        domain = self._extract_domain(request.url)

        # 更新域名统计（带容量控制）
        if domain not in self.domain_stats:
            # 超出限制时淘汰最旧的域名记录
            if len(self.domain_stats) >= self.MAX_DOMAINS:
                self._evict_oldest_domain()
            self.domain_stats[domain] = {'count': 0, 'last_time': 0}

        self.domain_stats[domain]['count'] += 1
        self.domain_stats[domain]['last_time'] = time.time()

        # 更新URL统计（带容量控制）
        if request.url not in self.url_stats:
            # 超出限制时淘汰最旧的 URL 记录
            if len(self.url_stats) >= self.MAX_URLS:
                self._evict_oldest_urls(int(self.MAX_URLS * 0.1))  # 淘汰 10%
            self.url_stats[request.url] = 0
        self.url_stats[request.url] += 1

        # 更新最后请求时间
        self.last_request_time[domain] = time.time()
    
    def _evict_oldest_domain(self) -> None:
        """淘汰最旧的域名记录（基于 last_time）"""
        if not self.domain_stats:
            return
        oldest_domain = min(
            self.domain_stats.keys(),
            key=lambda d: self.domain_stats[d].get('last_time', 0)
        )
        self.domain_stats.pop(oldest_domain, None)
        # 同步清理关联的统计
        self.error_counts.pop(oldest_domain, None)
        self.crawl_frequency.pop(oldest_domain, None)
        self.response_times.pop(oldest_domain, None)
        self.last_request_time.pop(oldest_domain, None)
    
    def _evict_oldest_urls(self, count: int) -> None:
        """淘汰指定数量的 URL 记录（FIFO 策略）"""
        # 先收集要删除的 key，避免在迭代过程中修改字典
        keys_to_remove = []
        keys_iterator = iter(self.url_stats.keys())
        for _ in range(count):
            key = next(keys_iterator, None)
            if key is None:
                break
            keys_to_remove.append(key)
            
        # 批量删除
        for key in keys_to_remove:
            self.url_stats.pop(key, None)

    def update_response_time(self, request: "Request", response_time: float):
        """更新响应时间统计"""
        domain = self._extract_domain(request.url)
        if domain not in self.response_times:
            self.response_times[domain] = []
        self.response_times[domain].append(response_time)
        # 只保留最近10次响应时间
        if len(self.response_times[domain]) > 10:
            self.response_times[domain] = self.response_times[domain][-10:]

    def update_error_count(self, request: "Request", has_error: bool = True):
        """更新错误计数"""
        domain = self._extract_domain(request.url)
        if domain not in self.error_counts:
            self.error_counts[domain] = 0
        if has_error:
            self.error_counts[domain] += 1
        else:
            # 成功时减少错误计数
            self.error_counts[domain] = max(0, self.error_counts[domain] - 1)

    def update_crawl_frequency(self, request: "Request"):
        """更新抓取频率统计"""
        domain = self._extract_domain(request.url)
        if domain not in self.crawl_frequency:
            self.crawl_frequency[domain] = {'last_hour_count': 0, 'last_update': time.time()}
        
        current_time = time.time()
        # 每小时重置计数器
        if current_time - self.crawl_frequency[domain]['last_update'] > 3600:
            self.crawl_frequency[domain]['last_hour_count'] = 0
            self.crawl_frequency[domain]['last_update'] = current_time
        
        self.crawl_frequency[domain]['last_hour_count'] += 1

    def _extract_domain(self, url: str) -> str:
        """提取域名"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return "unknown"
