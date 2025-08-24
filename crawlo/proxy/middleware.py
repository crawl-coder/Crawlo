#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2025-08-24 12:09
# @Author  : crawl-coder
# @Desc    : 企业级代理中间件，支持多源、策略、定时刷新、健康检查
"""
import time
import asyncio
import random
from typing import Optional, List, Dict, Any
from crawlo import Request, Response
from crawlo.middleware import BaseMiddleware
from crawlo.utils.log import get_logger

from .providers import BaseProxyProvider
from .strategies import STRATEGIES
from .health_check import check_single_proxy
from .stats import ProxyStats
from .utils import import_string, ensure_list, filter_valid_urls


class ProxyMiddleware(BaseMiddleware):
    """
    企业级代理中间件
    支持多源、策略、定时刷新、健康检查
    """

    def __init__(self, crawler):
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__, self.settings.get('LOG_LEVEL'))

        # 核心组件
        self.providers: List[BaseProxyProvider] = []
        self.stats = ProxyStats()
        self.scheduler = None

        # 代理池
        self.proxies: List[Dict] = []

        # 策略
        self.strategy_name = self.settings.get('PROXY_SELECTION_STRATEGY', 'least_used')
        self.strategy = STRATEGIES.get(self.strategy_name)
        if not self.strategy:
            self.logger.warning(f"未知策略 {self.strategy_name}，使用 least_used")
            self.strategy = STRATEGIES['least_used']

        # 控制参数
        self.max_failures = self.settings.get_int('PROXY_MAX_FAILURES', 3)
        self.cooldown_period = self.settings.get_int('PROXY_COOLDOWN_PERIOD', 600)
        self.max_retry_count = self.settings.get_int('PROXY_MAX_RETRY_COUNT', 3)
        self.request_delay = self.settings.get_float('PROXY_REQUEST_DELAY', 0.0)
        self.delay_enabled = self.settings.get_bool('PROXY_REQUEST_DELAY_ENABLED', False)

        # 健康检查
        self.health_check_enabled = self.settings.get_bool('PROXY_HEALTH_CHECK_ENABLED', True)
        self.health_check_interval = self.settings.get_int('PROXY_HEALTH_CHECK_INTERVAL', 300)
        self.last_health_check = 0

        # 定时刷新
        self.update_interval = self.settings.get_int('PROXY_POOL_UPDATE_INTERVAL', 300)
        self.last_update = 0

        # 状态
        self._last_req_time = 0
        self._setup_done = False
        self._lock = asyncio.Lock()

    @classmethod
    def create_instance(cls, crawler):
        return cls(crawler)

    def _load_providers(self):
        """加载所有 Provider"""
        cfgs = ensure_list(self.settings.get('PROXY_PROVIDERS', []))
        static_proxies = self.settings.get_list('PROXIES', [])

        if not cfgs and static_proxies:
            from crawlo.proxy.providers.static import StaticProxyProvider
            cfgs = [
                {
                    'class': 'crawlo.proxy.providers.StaticProxyProvider',
                    'config': {'proxies': static_proxies}
                }
            ]

        for cfg in cfgs:
            try:
                provider = instantiate_provider(cfg)
                if isinstance(provider, BaseProxyProvider):
                    self.providers.append(provider)
                    self.logger.info(f"✅ 加载 Provider: {provider}")
            except Exception as e:
                self.logger.error(f"加载 Provider 失败 {cfg}: {e}")

    async def _update_proxy_pool(self):
        """从所有 Provider 更新代理池"""
        self.logger.info("🔄 更新代理池...")
        all_urls = set()

        tasks = [provider.fetch_proxies() for provider in self.providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        valid_urls = filter_valid_urls(results)
        all_urls.update(valid_urls)

        self._replace_proxies(list(all_urls))
        self.logger.info(f"✅ 代理池更新完成: {len(self.proxies)} 个代理")

    def _replace_proxies(self, new_urls: List[str]):
        """
        替换代理池，保留现有状态，初始化新代理。
        """
        # old_urls = {p['url'] for p in self.proxies}
        new_proxies = []

        for url in new_urls:
            if not isinstance(url, str) or not url.strip():
                continue
            url = url.strip()
            if not url.startswith(('http://', 'https://', 'socks5://', 'socks4://')):
                continue

            # 复用现有状态
            existing = next((p for p in self.proxies if p['url'] == url), None)
            if existing is not None:
                new_proxies.append(existing)
            else:
                # 初始化新代理
                new_proxies.append({
                    'url': url,
                    'healthy': True,
                    'failures': 0,
                    'last_health_check': 0,
                    'unhealthy_since': 0
                })

        # 更新代理池
        old_count = len(self.proxies)
        self.proxies = new_proxies

        # 确保 stats 中有记录
        for proxy in self.proxies:
            if proxy['url'] not in self.stats.data:
                self.stats.data[proxy['url']] = {'success': 0, 'failure': 0, 'total': 0}

        # 清理已移除代理的统计（可选）
        current_urls = {p['url'] for p in self.proxies}
        for url in list(self.stats.data.keys()):
            if url not in current_urls:
                del self.stats.data[url]

        self.logger.info(f"✅ 代理池更新: {old_count} → {len(self.proxies)} 个代理")

    async def _health_check(self):
        """执行健康检查"""
        if not self.health_check_enabled:
            return
        now = time.time()
        if now - self.last_health_check < self.health_check_interval:
            return

        self.logger.info("🔍 健康检查开始...")
        self.last_health_check = now
        tasks = [
            check_single_proxy(p, "https://httpbin.org/ip")
            for p in self.proxies
            if now - p.get('last_health_check', 0) >= self.health_check_interval
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self.logger.info("✅ 健康检查完成")

    async def _initial_setup(self):
        """初始化代理系统（线程安全）"""
        async with self._lock:
            if self._setup_done:
                return
            self._load_providers()
            await self._update_proxy_pool()
            await self._health_check()

            # 只有 scheduler 存在才添加 job
            if self.scheduler is not None:
                self.update_job = self.scheduler.add_job(
                    self._update_proxy_pool,
                    'interval',
                    seconds=self.update_interval,
                    max_instances=1
                )
                self.scheduler.start()

            self._setup_done = True
            self.logger.info(f"⏱️ 代理系统启动完成（刷新周期: {self.update_interval}s）")

    async def process_request(self, request: Request, spider) -> Optional[Request]:
        """为请求设置代理"""
        if not self.settings.get_bool('PROXY_ENABLED', True):
            return None

        await self._initial_setup()

        # 请求延迟
        if self.delay_enabled and self.request_delay > 0:
            current_time = time.time()
            if self._last_req_time > 0:
                elapsed = current_time - self._last_req_time
                if elapsed < self.request_delay:
                    sleep_time = self.request_delay - elapsed
                    await asyncio.sleep(sleep_time)
            self._last_req_time = time.time()

        # 选择代理
        healthy = [p for p in self.proxies if p['healthy']]
        if not healthy:
            spider.logger.warning("⚠️ 无健康代理可用")
            return None

        try:
            proxy_url = self.strategy(healthy, request, self.stats.data)
            request.proxy = proxy_url
            self.stats.record(proxy_url, 'total')
            spider.logger.debug(f"🎯 使用代理: {proxy_url}")
        except Exception as e:
            self.logger.error(f"策略执行失败: {e}")

        return None  # ✅ 返回 None，表示继续流程

    def process_exception(self, request: Request, exc: Exception, spider) -> Optional[Request]:
        """请求失败时更换代理"""
        if not hasattr(request, 'proxy') or not request.proxy:
            return None

        proxy_url = request.proxy
        retry = request.meta.get('proxy_retry_count', 0)
        if retry >= self.max_retry_count:
            return None

        self.stats.record(proxy_url, 'failure')
        self._mark_failure(proxy_url)
        request.meta['proxy_retry_count'] = retry + 1

        new_proxy = self._get_alt(proxy_url)
        if new_proxy:
            request.proxy = new_proxy
            return request  # ✅ 返回新 Request，触发重试

        return None  # ✅ 返回 None，表示放弃

    def process_response(self, request: Request, response: Response, spider) -> Response:
        """记录成功"""
        if hasattr(request, 'proxy') and request.proxy:
            self.stats.record(request.proxy, 'success')
            self.logger.info(request.proxy)
            request.meta.pop('proxy_retry_count', None)
        return response  # ✅ 返回 Response，继续流程

    def _mark_failure(self, url: str):
        """标记代理失败"""
        p = next((p for p in self.proxies if p['url'] == url), None)
        if p:
            p['failures'] += 1
            if p['failures'] >= self.max_failures:
                p['healthy'] = False
                p['unhealthy_since'] = time.time()

    def _get_alt(self, current: str) -> Optional[str]:
        """获取替代代理"""
        others = [p for p in self.proxies if p['url'] != current and p['healthy']]
        return random.choice(others)['url'] if others else None


def instantiate_provider(cfg: Any) -> BaseProxyProvider:
    """根据配置实例化 Provider"""
    if isinstance(cfg, str):
        cls = import_string(cfg)
        return cls()
    elif isinstance(cfg, dict):
        cls = import_string(cfg['class'])
        return cls(**cfg.get('config', {}))
    elif isinstance(cfg, BaseProxyProvider):
        return cfg
    else:
        raise ValueError(f"无效 Provider 配置: {cfg}")