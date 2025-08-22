#!/usr/bin/python
# -*- coding: UTF-8 -*-
import time
import httpx
import random
import asyncio
from typing import Optional, List, Dict, Any

from crawlo import Request, Response
from crawlo.utils.log import get_logger
from crawlo.middleware import BaseMiddleware


class ProxyMiddleware(BaseMiddleware):
    """
    高级IP代理中间件
    支持：
    - 静态代理列表
    - 动态代理池 API
    - SOCKS 代理支持 (通过 httpx 自动支持)
    - 并发的异步代理健康检查
    - 代理冷却与自动恢复机制
    - 代理使用统计
    - 异步的非阻塞请求延迟控制
    """

    def __init__(self, crawler):
        self._last_request_time: float = 0
        self.proxies: List[Dict[str, Any]] = []  # 代理信息列表
        self.proxy_rules: Dict[str, str] = {}  # 域名 -> 代理
        self.proxy_pool_api: Optional[str] = None
        self.proxy_pool_auth: Optional[tuple] = None
        self.proxy_pool_last_update: float = 0
        self.proxy_pool_update_interval: int = 300
        self.proxy_stats: Dict[str, Dict[str, int]] = {}  # 代理统计

        self.max_failures = 3
        self.cooldown_period = 600  # 代理失败后的冷却时间（秒）
        self.max_retry_count = 3  # 最大重试次数

        self.health_check_enabled = True
        self.health_check_interval = 300
        self.last_health_check: float = 0

        self.request_delay: float = 0
        self.request_delay_enabled = False

        self._initial_setup_done = False
        self._init_lock = asyncio.Lock()  # 初始化锁
        self.logger = get_logger(self.__class__.__name__, crawler.settings.get('LOG_LEVEL'))

    @classmethod
    def create_instance(cls, crawler):
        """创建中间件实例并加载配置"""
        middleware = cls(crawler)
        middleware._load_settings(crawler.settings)
        return middleware

    def _load_settings(self, settings):
        """加载代理配置"""
        self.enabled = settings.get_bool('PROXY_ENABLED', True)
        self.max_failures = settings.get_int('PROXY_MAX_FAILURES', 3)
        self.cooldown_period = settings.get_int('PROXY_COOLDOWN_PERIOD', 600)
        self.max_retry_count = settings.get_int('PROXY_MAX_RETRY_COUNT', 3)

        static_proxies = settings.getlist('PROXIES', [])
        for proxy in static_proxies:
            self._add_proxy(proxy, source='static')

        self.proxy_rules.update(settings.getdict('PROXY_RULES', {}))
        self.proxy_pool_api = settings.get('PROXY_POOL_API')
        self.proxy_pool_auth = settings.get('PROXY_POOL_AUTH')
        self.proxy_pool_update_interval = settings.get_int('PROXY_POOL_UPDATE_INTERVAL', 300)

        self.health_check_enabled = settings.get_bool('PROXY_HEALTH_CHECK_ENABLED', True)
        self.health_check_interval = settings.get_int('PROXY_HEALTH_CHECK_INTERVAL', 300)

        self.request_delay = settings.get_float('PROXY_REQUEST_DELAY', 0)
        self.request_delay_enabled = settings.get_bool('PROXY_REQUEST_DELAY_ENABLED', False)

    def _add_proxy(self, proxy_url: str, source: str = 'unknown'):
        """添加代理到列表，并初始化其状态"""
        # 避免重复添加
        if any(p['url'] == proxy_url for p in self.proxies):
            return

        proxy_info = {
            'url': proxy_url,
            'source': source,
            'healthy': True,
            'failures': 0,
            'last_health_check': 0,
            'unhealthy_since': 0,
            'priority': 0,  # 可用于优先级排序
        }
        self.proxies.append(proxy_info)
        self.proxy_stats[proxy_url] = {'success': 0, 'failure': 0, 'total': 0}

    async def _fetch_proxies_from_api(self):
        """从代理池 API 异步获取代理"""
        if not self.proxy_pool_api or time.time() - self.proxy_pool_last_update < self.proxy_pool_update_interval:
            return

        self.logger.info("正在从 API 更新代理池...")
        try:
            async with httpx.AsyncClient() as client:
                # 支持认证
                auth = self.proxy_pool_auth if self.proxy_pool_auth else None
                response = await client.get(
                    self.proxy_pool_api,
                    timeout=10.0,
                    auth=auth
                )
                if response.status_code == 200:
                    data = response.json()
                    new_proxies = data.get('proxies', [])

                    # 增量更新，避免丢失状态
                    existing_api_proxies = {p['url'] for p in self.proxies if p['source'] == 'api'}
                    new_proxies_set = set(new_proxies)

                    # 移除已失效的 API 代理
                    self.proxies = [p for p in self.proxies if
                                    not (p['source'] == 'api' and p['url'] not in new_proxies_set)]
                    # 添加新增的 API 代理
                    for proxy in new_proxies_set:
                        if proxy not in existing_api_proxies:
                            self._add_proxy(proxy, source='api')

                    self.proxy_pool_last_update = time.time()
                    self.logger.info(f"从代理池获取到 {len(new_proxies)} 个新代理")
                else:
                    self.logger.error(f"获取代理池失败, HTTP 状态码: {response.status_code}")
        except Exception as e:
            self.logger.error(f"获取代理池异常: {e}")

    async def _check_single_proxy(self, proxy_info: Dict[str, Any], test_url: str):
        """对单个代理执行异步健康检查"""
        proxy_url = proxy_info['url']
        try:
            async with httpx.AsyncClient(proxies=proxy_url, timeout=10.0) as client:
                response = await client.get(test_url)
                if 200 <= response.status_code < 300:
                    # 检查通过，恢复代理状态
                    proxy_info['healthy'] = True
                    proxy_info['failures'] = 0
                    proxy_info['unhealthy_since'] = 0
                    self.logger.debug(f"代理 {proxy_url} 健康检查通过")
                else:
                    # 检查失败
                    proxy_info['healthy'] = False
                    proxy_info['unhealthy_since'] = time.time()
                    self.logger.warning(f"代理 {proxy_url} 健康检查失败: HTTP {response.status_code}")
        except Exception as e:
            proxy_info['healthy'] = False
            proxy_info['unhealthy_since'] = time.time()
            self.logger.warning(f"代理 {proxy_url} 健康检查异常: {e}")

        proxy_info['last_health_check'] = time.time()

    async def _health_check_proxies(self):
        """并发地对所有需要检查的代理进行健康检查"""
        if not self.health_check_enabled:
            return

        current_time = time.time()
        if current_time - self.last_health_check < self.health_check_interval:
            return

        self.logger.info("开始执行代理健康检查...")
        self.last_health_check = current_time

        test_url = 'https://httpbin.org/ip'  # ✅ 修复：移除末尾空格
        tasks = []

        for proxy_info in self.proxies:
            # 单独判断每个代理的检查间隔
            if current_time - proxy_info['last_health_check'] < self.health_check_interval:
                continue

            # 检查冷却期
            if not proxy_info['healthy']:
                time_since_unhealthy = current_time - proxy_info.get('unhealthy_since', 0)
                if time_since_unhealthy < self.cooldown_period:
                    continue  # 仍在冷却期

            tasks.append(self._check_single_proxy(proxy_info, test_url))

        if tasks:
            await asyncio.gather(*tasks)
        self.logger.info("代理健康检查完成")

    async def _initial_setup(self):
        """在首次请求前，执行一次代理获取和健康检查"""
        async with self._init_lock:  # ✅ 添加锁避免竞态条件
            if self._initial_setup_done:
                return

            self.logger.info("执行首次代理设置...")
            await self._fetch_proxies_from_api()
            await self._health_check_proxies()
            self._initial_setup_done = True
            self.logger.info("首次代理设置完成")

    async def process_request(self, request: Request, spider) -> Optional[Request]:
        """为请求设置代理（异步实现）"""
        if not self.enabled or (hasattr(request, 'proxy') and request.proxy):
            return None

        # 确保代理列表和健康状态已初始化
        await self._initial_setup()

        # 异步请求延迟
        if self.request_delay_enabled and self.request_delay > 0:
            if self._last_request_time:
                elapsed = time.time() - self._last_request_time
                if elapsed < self.request_delay:
                    await asyncio.sleep(self.request_delay - elapsed)
            self._last_request_time = time.time()

        # 获取可用代理
        proxy_url = self._select_proxy(request)
        if proxy_url:
            request.proxy = proxy_url
            spider.logger.debug(f"为请求 {request.url} 设置代理: {proxy_url}")
            self._record_proxy_use(proxy_url, 'total')

        return None

    def process_exception(self, request: Request, exp: Exception, spider) -> Optional[Request]:
        """处理代理失败异常"""
        if not self.enabled or not hasattr(request, 'proxy') or not request.proxy:
            return None

        # 从 meta 中获取重试次数（避免只读属性错误）
        retry_count = request.meta.get('proxy_retry_count', 0)
        if retry_count >= self.max_retry_count:
            spider.logger.error(f"请求 {request.url} 代理重试次数已达上限({self.max_retry_count})，放弃重试")
            return None

        proxy_url = request.proxy
        self._record_proxy_use(proxy_url, 'failure')
        self._record_proxy_failure(proxy_url)
        spider.logger.warning(f"代理 {proxy_url} 请求失败: {type(exp).__name__}: {exp}")

        # 增加重试次数并存储到 meta
        request.meta['proxy_retry_count'] = retry_count + 1

        # 尝试更换代理并重新发起请求
        new_proxy_url = self._get_alternative_proxy(proxy_url)
        if new_proxy_url:
            spider.logger.info(f"请求 {request.url} 更换代理为: {new_proxy_url} (第{retry_count + 1}次重试)")
            request.proxy = new_proxy_url
            return request

        spider.logger.error(f"请求 {request.url} 失败，且无备用代理可用")
        return None

    def process_response(self, request: Request, response: Response, spider) -> Response:
        """处理响应，记录代理成功"""
        if self.enabled and hasattr(request, 'proxy') and request.proxy:
            self._record_proxy_use(request.proxy, 'success')

        # 清理成功的请求的重试计数
        if 'proxy_retry_count' in request.meta:
            del request.meta['proxy_retry_count']

        return response

    def _select_proxy(self, request: Request) -> Optional[str]:
        """根据请求选择合适的代理"""
        # 1. 按域名规则匹配
        for domain, proxy_url in self.proxy_rules.items():
            if domain in request.url:
                return proxy_url

        # 2. 选择一个健康的代理
        available_proxies = self._get_healthy_proxies()
        if not available_proxies:
            return None

        # 优先选择优先级高的，然后选择使用次数少的代理
        available_proxies.sort(key=lambda p: (-p['priority'], self.proxy_stats[p['url']]['total']))
        return available_proxies[0]['url']

    def _get_healthy_proxies(self) -> List[Dict[str, Any]]:
        """获取所有当前状态为健康的代理"""
        current_time = time.time()
        healthy_proxies = []

        for proxy_info in self.proxies:
            if proxy_info['healthy']:
                healthy_proxies.append(proxy_info)
            elif not proxy_info['healthy']:
                # 检查是否已过冷却期
                time_since_unhealthy = current_time - proxy_info.get('unhealthy_since', 0)
                if time_since_unhealthy >= self.cooldown_period:
                    # 冷却期结束，标记为健康（等待下次健康检查确认）
                    proxy_info['healthy'] = True
                    healthy_proxies.append(proxy_info)

        return healthy_proxies

    def _record_proxy_failure(self, proxy_url: str):
        """记录代理失败，并在达到阈值时禁用它"""
        proxy_info = next((p for p in self.proxies if p['url'] == proxy_url), None)
        if not proxy_info:
            return

        proxy_info['failures'] += 1
        if proxy_info['failures'] >= self.max_failures:
            proxy_info['healthy'] = False
            proxy_info['unhealthy_since'] = time.time()
            self.logger.warning(
                f"代理 {proxy_url} 失败次数达到上限({self.max_failures})，已禁用并进入冷却期({self.cooldown_period}秒)")

    def _record_proxy_use(self, proxy_url: str, stat_type: str):
        """记录代理使用统计"""
        if proxy_url in self.proxy_stats:
            self.proxy_stats[proxy_url][stat_type] += 1

    def _get_alternative_proxy(self, current_proxy_url: str) -> Optional[str]:
        """获取一个不同于当前代理的替代代理"""
        healthy_proxies = self._get_healthy_proxies()
        alternatives = [p for p in healthy_proxies if p['url'] != current_proxy_url]
        return random.choice(alternatives)['url'] if alternatives else None

    def get_stats(self) -> Dict[str, Dict[str, int]]:
        """获取代理使用统计"""
        return self.proxy_stats.copy()