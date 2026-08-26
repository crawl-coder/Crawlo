# -*- coding: UTF-8 -*-
"""
InfoQ 动态渲染长时运行稳定性测试爬虫
====================================
真实站点动态场景长跑：列表页与详情页均走浏览器渲染通道
（HYBRID_DYNAMIC_DOMAINS 域名匹配 → 动态下载器），用于检验：

- 浏览器实例/页面池长期工作是否稳定（无句柄泄漏、无僵死标签页）
- item 产出速率是否随时间衰减（反爬退化或资源泄漏的信号）
- 错误率随时间的变化
- 进程 RSS 峰值走势

运行机制：
- 反复请求列表页发现新文章链接（框架去重过滤已抓过的 URL）
- 新文章 → 详情页动态渲染提取正文
- 到达 RUN_MINUTES 截止时间后不再产出新请求，队列排空自然退出

环境变量：
    RUN_MINUTES       运行时长上限（默认 30）
    LIST_INTERVAL     两轮列表刷新之间的最小间隔秒数（默认 60）
    MAX_DETAILS       详情页总数上限（安全阀，0=不限，默认 0）
"""
import os
import threading
import time

from crawlo import Spider, Request
from ..items import InfoqArticle


class InfoqLongRunSpider(Spider):
    """InfoQ 长跑爬虫 - 列表/详情全动态渲染"""

    name = 'infoq_longrun_spider'

    LIST_URL = 'https://www.infoq.cn/zones/harmonyos/latest'

    custom_settings = {
        'CONCURRENCY': 2,
        'DOWNLOAD_DELAY': 2.0,
        'RETRY_TIMES': 2,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.run_minutes = float(os.environ.get('RUN_MINUTES', 30))
        self.list_interval = float(os.environ.get('LIST_INTERVAL', 60))
        self.max_details = int(os.environ.get('MAX_DETAILS', 0))
        self.deadline = time.monotonic() + self.run_minutes * 60
        self.started_at = time.time()

        self._seen_details = set()
        self._detail_count = 0
        self._error_count = 0
        self._list_rounds = 0

        # RSS 峰值采样（后台线程，10s 一拍）
        self._stop_sampling = threading.Event()
        self._rss_samples = []
        self._sampler = threading.Thread(target=self._sample_rss, daemon=True)
        self._sampler.start()

    # ------------------------------------------------------------------
    def _sample_rss(self):
        import sys
        # ru_maxrss 单位：Linux=KB，macOS=bytes
        divisor = 1024 * 1024 if sys.platform == 'darwin' else 1024
        while not self._stop_sampling.is_set():
            try:
                import resource
                rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / divisor
                self._rss_samples.append((time.time() - self.started_at, round(rss_mb, 1)))
            except Exception:
                pass
            self._stop_sampling.wait(10)

    @property
    def _expired(self) -> bool:
        return time.monotonic() >= self.deadline

    # ------------------------------------------------------------------
    def start_requests(self):
        self.logger.info(f"[longrun] 启动：时长上限 {self.run_minutes} 分钟，"
                         f"列表刷新间隔 {self.list_interval}s")
        yield Request(url=self.LIST_URL, callback=self.parse_list)

    def parse_list(self, response):
        if self._expired:
            return
        self._list_rounds += 1
        links = response.xpath('//a[contains(@href,"/article/")]/@href').getall()
        unique = []
        for href in links:
            full = response.urljoin(href)
            if full not in self._seen_details:
                unique.append(full)
        self.logger.info(f"[list] 第 {self._list_rounds} 轮：页面链接 {len(links)}，"
                         f"新文章 {len(unique)}")

        new_details = 0
        for url in unique:
            if self._expired:
                break
            if self.max_details and self._detail_count >= self.max_details:
                break
            self._seen_details.add(url)
            self._detail_count += 1
            new_details += 1
            yield Request(
                url=url,
                callback=self.parse_detail,
                errback=self.on_detail_error,
                meta={'use_dynamic_loader': True},
            )

        # 安排下一轮列表刷新：dont_filter 跳过去重（同 URL 需反复抓取以
        # 发现新文章）；详情侧由 _seen_details + 框架去重双保险防重复。
        # 等当前批次详情消费完后由队列自然调度，形成节律。
        if not self._expired:
            yield Request(
                url=self.LIST_URL,
                callback=self.parse_list,
                dont_filter=True,
                meta={'use_dynamic_loader': True,
                      'list_round': self._list_rounds + 1},
            )
        self.logger.info(f"[list] 本轮跟进详情 {new_details} 个，"
                         f"累计 {self._detail_count}")

    def parse_detail(self, response):
        if self._expired:
            # 截止后到达的响应直接放弃，保证队列可及时排空
            self.logger.debug(f"[detail-skip-expired] {response.url}")
            return
        title = response.xpath('//h1//text()').getall()
        title = ''.join(t.strip() for t in title if t.strip())[:120]
        content = response.xpath(
            '//div[contains(@class,"ProseMirror")]//text() | '
            '//article//text()'
        ).getall()
        content_text = ''.join(t.strip() for t in content if t.strip())

        yield InfoqArticle(
            url=response.url,
            title=title or '(no title)',
            content=content_text[:20000],
            text_length=len(content_text),
            source='infoq.cn',
            type='detail_dynamic',
            status='ok' if len(content_text) > 100 else 'thin_content',
        )

    def on_detail_error(self, failure):
        if self._expired:
            return
        self._error_count += 1
        self.logger.warning(f"[detail-error] {failure.request.url} : "
                            f"{failure.value!r}")
        yield InfoqArticle(
            url=failure.request.url,
            title='(failed)',
            source='infoq.cn',
            type='detail_error',
            status=f'error: {type(failure.value).__name__}',
        )

    # ------------------------------------------------------------------
    async def spider_closed(self) -> None:
        """汇总长跑指标"""
        self._stop_sampling.set()
        elapsed = time.time() - self.started_at
        rss = self._rss_samples
        rss_first = rss[0][1] if rss else 0
        rss_peak = max(v for _, v in rss) if rss else 0
        ok_items = '?'
        if hasattr(self, 'crawler') and self.crawler is not None:
            stats = getattr(self.crawler, 'stats', None)
            if stats is not None and hasattr(stats, 'get_value'):
                ok_items = stats.get_value('item_successful_count', '?')
                if ok_items in (None, '?'):
                    ok_items = stats.get_value('finish_reason', 'finished')
        self.logger.info(
            "\n" + "=" * 60 +
            f"\n[longrun] 汇总：耗时 {elapsed/60:.1f} min"
            f"\n  列表轮次      : {self._list_rounds}"
            f"\n  详情请求      : {self._detail_count}"
            f"\n  详情错误      : {self._error_count}"
            f"\n  成功 item     : {ok_items}"
            f"\n  RSS 峰值      : {rss_peak:.0f} MB（首采 {rss_first:.0f} MB）"
            f"\n  采样点        : {len(rss)}"
            + ("\n  RSS 曲线(每30s): "
               + " ".join(f"{v:.0f}" for _, v in rss[::3]) if rss else "")
            + "\n" + "=" * 60
        )
