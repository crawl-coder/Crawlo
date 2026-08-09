#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""谁还在持有 Crawler？"""
import os
import sys
import asyncio
import gc
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawlo.crawler_process import CrawlerProcess


async def main():
    for r in range(3):
        cp = CrawlerProcess()
        await cp.crawl('of_week')
        del cp
        gc.collect()
        gc.collect()
        gc.collect()

    crawlers = [o for o in gc.get_objects() if type(o).__name__ == 'Crawler']
    print(f"\nCrawler alive: {len(crawlers)}")
    for i, c in enumerate(crawlers[:3]):
        print(f"\n--- Crawler[{i}] id={id(c)} state={getattr(c, '_state', '?')} ---")
        refs = gc.get_referrers(c)
        types = collections.Counter()
        details = []
        for r in refs:
            t = type(r).__name__
            types[t] += 1
            if isinstance(r, dict):
                # 看看是不是 module dict 或 crawler self 内部成员
                keys = list(r.keys())
                # 寻找有没有指向 Crawler 的属性名在对象里拥有
                owner = [f"{k}={type(r.get(k)).__name__}" for k in ('_crawlers', 'crawler', '_crawler', 'spider', '_spider') if k in r]
                if owner:
                    details.append(f"dict(has: {','.join(owner)}) keys_sample={keys[:8]}")
            elif isinstance(r, list):
                # 看看 list 属于谁
                outer = gc.get_referrers(r)
                outer_types = collections.Counter(type(o).__name__ for o in outer)
                details.append(f"list(len={len(r)}, owners={dict(outer_types)})")
            elif t == 'frame':
                # frame 的 code name
                co = getattr(r, 'f_code', None)
                if co:
                    details.append(f"frame(co={co.co_name}@{co.co_filename}:{getattr(r,'f_lineno','?')})")
        print(f"  Top referrer types: {dict(types.most_common(12))}")
        if details:
            print(f"  Details:")
            for d in details[:10]:
                print(f"    - {d}")


if __name__ == '__main__':
    asyncio.run(main())
