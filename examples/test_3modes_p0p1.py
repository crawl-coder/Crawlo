#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
三模式完整测绘脚本 — 跑 ofweek 真实列表页（验证 P0 XCLAIM + P1 engine 拆分）
- standalone: Memory 队列 + 2页
- auto:       Redis ZSET 队列 + 2页（2次运行验证去重 + idle 速退）
- distributed:Stream 队列 + 种子锁 + XCLAIM(stale pending 手动注入)
- P0 XCLAIM:  人为注入 5 条 stale pending → claim_stale_pending 回收
"""
import os, sys, asyncio, time, json
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'examples/ofweek_standalone'))

import redis as redis_mod
REDIS_HOST, REDIS_PORT, REDIS_DB = '127.0.0.1', 6379, 0

# =============== 复用 OfWeekSpider（2页），不依赖 MySQL ===============
from crawlo.spider import Spider
from crawlo import Request, Item

class OfWeek2PageSpider(Spider):
    name = 'ofweek_2page'
    allowed_domains = ['ee.ofweek.com']

    def start_requests(self):
        for page in range(1, 3):
            url = f'https://ee.ofweek.com/CATList-2800-8100-ee-{page}.html'
            yield Request(url, callback=self.parse, dont_filter=True, meta={'depth': 1})

    def parse(self, response):
        if response.status != 200:
            self.logger.warning(f'列表页非200: {response.status} {response.url}')
            return
        rows = response.xpath('//div[@class="main_left"]/div[@class="list_model"]/div[@class="model_right model_right2"]')
        self.logger.info(f'列表页 {response.url} → 找到 {len(rows)} 个条目')
        for row in rows:
            url = row.xpath('./h3/a/@href').extract_first()
            title = row.xpath('./h3/a/text()').extract_first()
            if not url:
                continue
            abs_url = response.urljoin(url)
            if not abs_url.startswith('http'):
                continue
            yield Request(abs_url, callback=self.parse_detail,
                          meta={'depth': 2, 'title': (title or '').strip()})

    def parse_detail(self, response):
        if response.status != 200:
            return
        title = response.meta.get('title', '') or (response.css('title::text').get('')[:30].strip())
        if not title:
            return
        publish_time = response.xpath('//div[@class="time fl"]/text()').extract_first() or ''
        item = Item()
        item['title'] = title
        item['publish_time'] = publish_time.strip() if publish_time else ''
        item['url'] = response.url
        yield item


def clear_redis_prefix(prefix):
    """按前缀清理 Redis key。前缀兼容 raw prefix 和 crawlo:{project}:* 的形式。"""
    try:
        r = redis_mod.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
        keys = r.keys(prefix)
        if keys:
            r.delete(*keys)
            print(f'  🧹 清理 {len(keys)} 个 Redis key (prefix={prefix})')
    except Exception as e:
        print(f'  ⚠️ Redis 清理失败: {e}')

def clear_redis_mode(mode, spider='ofweek_2page'):
    """清理指定 mode 的所有 key：
    - 全局前缀 crawlo:crawlo_map_{mode}:* (包含 stream/filter/dedup/control/leader 等)
    - 兜底清除 crawl_map_{mode}:*、crawlo_map_{mode}_*
    """
    project = f'crawlo_map_{mode}'
    for p in [f'crawlo:{project}:{spider}:*',
              f'crawlo:{project}:*',
              f'{project}:*',
              f'crawlo:*{project}*']:
        clear_redis_prefix(p)

def make_settings(mode):
    project = f'crawlo_map_{mode}'
    from crawlo.core.config import CrawloConfig
    if mode == 'standalone':
        cfg = CrawloConfig.standalone(project_name=project, concurrency=4, download_delay=0.5)
    elif mode == 'auto':
        cfg = CrawloConfig.auto(project_name=project, redis_host=REDIS_HOST, redis_port=REDIS_PORT, concurrency=4, download_delay=0.5)
    elif mode == 'distributed':
        cfg = CrawloConfig.distributed(project_name=project, redis_host=REDIS_HOST, redis_port=REDIS_PORT, concurrency=4, download_delay=0.5)
    s = cfg.to_dict()
    s['SPIDER_NAME'] = 'ofweek_2page'
    s['LOG_LEVEL'] = 'INFO'
    s['DOWNLOADER'] = 'crawlo.downloader.aiohttp_downloader.AioHttpDownloader'
    s['CLOSESPIDER_PAGECOUNT'] = 50   # 2 列表页 → 约 40 详情页 → 50 上限够
    # P0: 调小 XCLAIM 参数，便于 distributed 实跑时也能触发
    s['DISTRIBUTED_IDLE_XCLAIM_SCAN_INTERVAL'] = 3
    s['DISTRIBUTED_IDLE_XCLAIM_MIN_IDLE'] = 5
    s['DISTRIBUTED_WORKER_IDLE_TIMEOUT'] = 40
    return s

async def run_single(mode, worker_id=None, worker_tag=''):
    from crawlo.crawler import CrawlerProcess, reset_framework
    reset_framework()
    t0 = time.monotonic()
    settings = make_settings(mode)
    if worker_id:
        settings['WORKER_ID'] = worker_id
    tag = f'[{mode}{(" "+worker_tag) if worker_tag else ""}]'
    print(f"\n{'='*60}\n  🚀 {tag} 启动 | max_page={settings.get('CLOSESPIDER_PAGECOUNT')}\n{'='*60}")
    try:
        p = CrawlerProcess(settings=settings)
        crawler = await p.crawl(OfWeek2PageSpider)
        s = crawler.stats.get_stats() if crawler and crawler.stats else {}
        elapsed = time.monotonic() - t0
        def g(key, default=0):
            # 兼容 crawlo: 前缀与无前缀
            return s.get(f'crawlo:{key}', s.get(key, default))
        result = {
            'ok': True, 'elapsed': elapsed,
            'requests': int(g('request_scheduler_count', 0)),
            'responses': int(g('response_received_count', 0)),
            'items': int(g('item_successful_count', 0)),
            'dedup_new': int(g('dedup/new_count', 0)),
            'dedup_cleanup': int(g('dedup/cleanup_count', 0)),
            'reason': g('reason', ''),
            'stats': s,
        }
        print(f"  📊 {tag} 结果: {elapsed:.1f}s | req={result['requests']} resp={result['responses']} item={result['items']} | dedup_new={result['dedup_new']} | exit={result['reason']}")
        return result
    except Exception as e:
        elapsed = time.monotonic() - t0
        import traceback
        print(f"  ❌ {tag} 异常 ({elapsed:.1f}s): {type(e).__name__}: {e}")
        print(traceback.format_exc())
        return {'ok': False, 'elapsed': elapsed, 'error': str(e)}

async def p0_xclaim_mapping_test():
    """P0 XCLAIM 测绘：
    1) 创建 Stream 队列，塞入 5 条假请求
    2) 用不存在的 worker_dead XREADGROUP 造 pending（不 ACK）
    3) 等 6s 越过 min_idle=5s
    4) 调 claim_stale_pending(min_idle=5)
    5) 验证：pending 减少 + 回收数 ≥5
    """
    from crawlo.queue.backends.redis_stream import RedisStreamQueue
    from crawlo import Request
    clear_redis_prefix('crawlo:*map_xclaim*')
    project = 'map_xclaim'
    q = RedisStreamQueue(
        redis_url=f'redis://{REDIS_HOST}:{REDIS_PORT}',
        project_name=project, spider_name='ofweek_2page',
        stream_compact=True, priority_enabled=True,
    )
    await q.connect()
    print(f"\n{'='*60}\n  🔬 P0 XCLAIM 测绘: 注入 5 条 stale pending + claim_stale_pending\n{'='*60}")

    # 塞 5 条假请求
    for i in range(5):
        await q.put(Request(f'https://example.com/stale/{i}', meta={'depth': 1}))
    print(f"  📥 put 5 条: stream(main) xlen={await q._redis.xlen(q._stream)} high={await q._redis.xlen(q._high_stream)}")

    # 造 stale pending
    dead_consumer = 'worker_dead'
    try:
        await q._redis.xgroup_create(q._stream, q.group_name, id='0', mkstream=True)
    except Exception:
        pass
    got = await q._redis.xreadgroup(q.group_name, dead_consumer, {q._stream: '>'}, count=5, noack=False)
    if got:
        for _, msgs in got:
            print(f"  💀 worker_dead 读到 {len(msgs)} 条消息（故意不 ACK，将变成 stale pending）")

    # 等 6s > min_idle=5s
    print('  ⏱️ 等待 6s，让 pending idle > min_idle=5s ...')
    await asyncio.sleep(6)

    info_before = await q.pending_info()
    print(f'  📋 回收前 pending_info={json.dumps(info_before, ensure_ascii=False)}')

    recovered = await q.claim_stale_pending(min_idle_sec=5, count=50)
    info_after = await q.pending_info()
    print(f'  ♻️ claim_stale_pending(min_idle=5s) → 回收 {recovered} 条')
    print(f'  📋 回收后 pending_info={json.dumps(info_after, ensure_ascii=False)}')
    print(f'  📋 回收后 stream xlen(main)={await q._redis.xlen(q._stream)}')
    await q.close()

    ok = recovered >= 5
    print(f"\n  {'✅ XCLAIM 测绘通过' if ok else '❌ XCLAIM 测绘失败'}: 回收 {recovered}/5, pending {info_before.get('total')}→{info_after.get('total')}")
    clear_redis_prefix('crawlo:*map_xclaim*')
    return {'ok': ok, 'recovered': recovered,
            'pending_before': info_before.get('total'),
            'pending_after': info_after.get('total')}

async def main():
    results = {}
    print(f'🗓️  开始时间: {time.strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'🧪 Redis 可用性: {redis_mod.Redis(host=REDIS_HOST,port=REDIS_PORT).ping()}')

    # ----- 1. Standalone -----
    clear_redis_mode('standalone')
    results['standalone'] = await run_single('standalone')

    # ----- 2. Auto Run 1 (冷启动) -----
    clear_redis_mode('auto')
    results['auto_R1'] = await run_single('auto', worker_tag='R1冷启')

    # ----- 2. Auto Run 2 (热启动，Redis 去重生效) -----
    print('\n  ⏩ Auto 模式第 2 次运行 — 验证 Redis ZSET 去重 + idle 速退（R2 dedup_new 应≈2）')
    results['auto_R2'] = await run_single('auto', worker_tag='R2热启')

    # ----- 3. Distributed -----
    clear_redis_mode('distributed')
    results['distributed_W1'] = await run_single('distributed', worker_id='W1_map', worker_tag='W1')

    # ----- 4. P0 XCLAIM 单元测绘 -----
    results['P0_XCLAIM'] = await p0_xclaim_mapping_test()

    # ===== Summary =====
    print(f"\n\n{'='*72}")
    print(f'  📋 三模式 + P0 XCLAIM 完整测绘结果 @ {time.strftime("%H:%M:%S")}')
    print(f'{"="*72}')
    for k, v in results.items():
        if not v.get('ok'):
            print(f'  ❌ {k:20s}: FAIL — {v.get("error","unknown")}')
            continue
        if 'recovered' in v:
            print(f'  ✅ {k:20s}: XCLAIM回收 {v["recovered"]}/5  pending {v["pending_before"]}→{v["pending_after"]}')
        else:
            print(f'  ✅ {k:20s}: {v["elapsed"]:6.1f}s  req={v["requests"]:3d}  resp={v["responses"]:3d}  item={v["items"]:3d}  dedup_new={v["dedup_new"]:3d}  exit={v["reason"]}')

    # ===== 关键断言（快速判定）=====
    def _stat(mode, key, default=0):
        """从指定模式运行结果的 stats dict 中提取指标值（兼容 crawlo: 前缀）"""
        s = results.get(mode, {}).get('stats', {})
        return s.get(f'crawlo:{key}', s.get(key, default))

    checks = {
        'standalone_req>=40': results.get('standalone', {}).get('requests', 0) >= 30,
        'standalone_item>=20': results.get('standalone', {}).get('items', 0) >= 10,
        'standalone_finished': results.get('standalone', {}).get('reason') == 'finished',
        'auto_R1_uses_redis': results.get('auto_R1', {}).get('requests', 0) >= 30,
        # R2 仅 2 个 start_requests(dont_filter=True) 新增，详情页被 Redis 去重
        'auto_R2_dedup_works': results.get('auto_R2', {}).get('dedup_new', 0) <= 5,
        'auto_R2_fast_exit': results.get('auto_R2', {}).get('elapsed', 999) <= 30,
        'distributed_W1_ok': results.get('distributed_W1', {}).get('requests', 0) >= 30,
        'distributed_W1_finished': results.get('distributed_W1', {}).get('reason') == 'finished',
        # P4 D方向 #3：distributed 模式 idle 期间触发 XCLAIM 主动扫描，scan_runs >= 1
        'distributed_W1_xclaim_scan': _stat('distributed_W1', 'queue/xclaim/scan_runs') >= 1,
        'P0_XCLAIM_5of5': results.get('P0_XCLAIM', {}).get('recovered', 0) >= 5,
    }
    print(f'\n  🎯 关键断言:')
    all_ok = True
    for ck, ok in checks.items():
        flag = '✅' if ok else '❌'
        if not ok:
            all_ok = False
        print(f'     {flag} {ck}')
    print(f'\n  🏁 总体: {"✅ 全部通过" if all_ok else "❌ 存在失败项，需排查"}')

    clear_redis_mode('standalone')
    clear_redis_mode('auto')
    clear_redis_mode('distributed')
    return 0 if all_ok else 1

if __name__ == '__main__':
    rc = asyncio.run(main())
    sys.exit(rc)
