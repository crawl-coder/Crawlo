#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
ofweek 结构 mock 站：与 ee.ofweek.com 的列表/详情 DOM 结构一致，
供本地无网与 CI 验证使用（选择器与真实站点相同）。
"""

import argparse

from aiohttp import web


def _list_page(page: int) -> str:
    rows = ""
    for i in range((page - 1) * 3 + 1, page * 3 + 1):
        rows += f"""
        <div class="model_right model_right2">
          <h3><a href="/news/{i}">News {i:03d}</a></h3>
        </div>"""
    return f"""<!DOCTYPE html>
<html><body>
<div class="main_left">
  <div class="list_model">{rows}</div>
</div>
</body></html>"""


def _detail_page(page: int) -> str:
    return f"""<!DOCTYPE html>
<html><body>
<div class="title"><h1>News {page:03d}</h1></div>
<div class="TRS_Editor"><p>Content of news {page:03d}.</p></div>
</body></html>"""


async def list_handler(request):
    page = 1
    return web.Response(text=_list_page(page), content_type="text/html")


async def detail_handler(request):
    page = int(request.match_info["id"])
    return web.Response(text=_detail_page(page), content_type="text/html")


def main():
    parser = argparse.ArgumentParser(description="ofweek mock 站")
    parser.add_argument("--port", type=int, default=9100)
    args = parser.parse_args()

    app = web.Application()
    app.router.add_get("/CATList-2800-8100-ee-1.html", list_handler)
    app.router.add_get("/news/{id}", detail_handler)
    web.run_app(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
