#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
测试2 诊断：Crawler 对象泄漏原因排查
- 跑 3 轮后，强制 gc.collect()，查看 gc.garbage（uncollectable）
- 检查 Crawler 的 referrers 类型 Top N（谁在持有引用）
- tracemalloc snapshot 对比
"""
import os
import sys
import asyncio
import gc
import tracemalloc
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawlo.crawler_process import CrawlerProcess


async def diag():
    gc.set_debug(gc.DEBUG_SAVEALL)   # 把不可达对象放进 gc.garbage，不释放
    tracemalloc.start()

    for r in range(3):
        cp = CrawlerProcess()
        await cp.crawl('of_week')
        del cp
        collected = gc.collect()
        print(f"R{r+1}: gc.collect() returned {collected}, gc.garbage now {len(gc.garbage)}")

    # ---- Crawler 对象 referrer 类型 Top 10 ----
    crawler_objs = [o for o in gc.get_objects() if type(o).__name__ == 'Crawler']
    print(f"\n=== Crawler 对象存活数: {len(crawler_objs)} ===")
    if crawler_objs:
        target = crawler_objs[0]
        ref_types = collections.Counter()
        for ref in gc.get_referrers(target):
            if isinstance(ref, dict):
                ref_types[f"dict(__module__={ref.get('__module__','?')})"] += 1
            else:
                ref_types[type(ref).__name__] += 1
        print(f"\nTop referrers for Crawler[0] id={id(target)}:")
        for name, cnt in ref_types.most_common(15):
            print(f"  {cnt:3d}  {name}")

        # 特别看 list 对象：是不是 CrawlerProcess._crawlers 没清？
        list_refs = [r for r in gc.get_referrers(target) if isinstance(r, list)]
        print(f"\n指向 Crawler[0] 的 list: {len(list_refs)} 个")
        for i, lst in enumerate(list_refs[:5]):
            id_ = id(lst)
            # 反向查谁持有这个 list
            outer = gc.get_referrers(lst)
            outer_types = collections.Counter(type(o).__name__ for o in outer)
            print(f"  list#{i} id={id_} len={len(lst)}, 外层持有者: {dict(outer_types)}")

    # ---- gc.garbage 类型 Top ----
    print(f"\n=== gc.garbage (uncollectable, N={len(gc.garbage)}) ===")
    if gc.garbage:
        types = collections.Counter(type(o).__name__ for o in gc.garbage)
        for name, cnt in types.most_common(10):
            print(f"  {cnt:5d}  {name}")

    # ---- PipelineManager 对象 referrer 类型 Top ----
    pm_objs = [o for o in gc.get_objects() if type(o).__name__ == 'PipelineManager']
    print(f"\n=== PipelineManager 存活数: {len(pm_objs)} ===")
    if pm_objs:
        ref_types = collections.Counter(type(r).__name__ for r in gc.get_referrers(pm_objs[0]))
        print(f"Top referrers for PipelineManager[0]:")
        for name, cnt in ref_types.most_common(10):
            print(f"  {cnt:3d}  {name}")

    # ---- AioHttpDownloader referrers ----
    dl_objs = [o for o in gc.get_objects() if type(o).__name__ == 'AioHttpDownloader']
    print(f"\n=== AioHttpDownloader 存活数: {len(dl_objs)} ===")
    if dl_objs:
        ref_types = collections.Counter(type(r).__name__ for r in gc.get_referrers(dl_objs[0]))
        print(f"Top referrers for dl[0]: {dict(ref_types.most_common(10))}")

    # ---- AioRedisFilter referrers ----
    ft_objs = [o for o in gc.get_objects() if type(o).__name__ == 'AioRedisFilter']
    print(f"\n=== AioRedisFilter 存活数: {len(ft_objs)} ===")
    if ft_objs:
        ref_types = collections.Counter(type(r).__name__ for r in gc.get_referrers(ft_objs[0]))
        print(f"Top referrers for ft[0]: {dict(ref_types.most_common(10))}")

    tracemalloc.stop()
    gc.set_debug(0)


if __name__ == '__main__':
    asyncio.run(diag())
