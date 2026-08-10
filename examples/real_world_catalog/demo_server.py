#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
本地演示服务器：模拟一个"分页列表页 + 详情页"的电商目录站。

用法：
    python demo_server.py [--port 9000]

然后另开终端运行：
    python run.py
    # 可选：CATALOG_MAX_PAGES=3 限制抓取页数
"""

import argparse
import html
import random
import string

from aiohttp import web


def _product_card(index: int, base: str) -> str:
    title = f"Product {index:04d}"
    price = f"{random.randint(99, 9999)}.{random.randint(0, 99):02d}"
    category = ["electronics", "books", "home", "toys"][index % 4]
    sku = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"""
    <div class="product-card" data-sku="{sku}">
      <a class="product-link" href="/product/{index}">{title}</a>
      <span class="product-title">{title}</span>
      <span class="product-price">${price}</span>
      <span class="product-category">{category}</span>
    </div>"""


def _listing_page(page: int, per_page: int, base: str) -> str:
    cards = "".join(
        _product_card(i, base)
        for i in range((page - 1) * per_page + 1, page * per_page + 1)
    )
    next_link = (
        f'<a class="pagination-link next" href="/catalog?page={page + 1}">next</a>'
        if page < 3
        else ""
    )
    return f"""<!DOCTYPE html>
<html><head><title>Catalog page {page}</title></head><body>
<h1>Catalog</h1>
{cards}
<nav>{next_link}</nav>
</body></html>"""


def _detail_page(product_id: int) -> str:
    title = f"Product {product_id:04d}"
    return f"""<!DOCTYPE html>
<html><head><title>{title}</title></head><body>
<h1 class="product-title">{title}</h1>
<div class="product-price">${random.randint(99, 9999)}.{random.randint(0, 99):02d}</div>
<div class="product-description">Description for {title}.</div>
<div class="product-sku">SKU-{product_id:04d}</div>
<div class="stock-status in-stock">in stock</div>
</body></html>"""


async def catalog_page(request: web.Request) -> web.Response:
    page = max(1, int(request.query.get("page", "1")))
    base = f"http://{request.host}"
    return web.Response(
        text=_listing_page(page, per_page=5, base=base),
        content_type="text/html",
    )


async def product_page(request: web.Request) -> web.Response:
    product_id = int(request.match_info["id"])
    return web.Response(text=_detail_page(product_id), content_type="text/html")


def main():
    parser = argparse.ArgumentParser(description="real_world_catalog 演示服务器")
    parser.add_argument("--port", type=int, default=9000)
    args = parser.parse_args()

    app = web.Application()
    app.router.add_get("/catalog", catalog_page)
    app.router.add_get("/product/{id}", product_page)
    web.run_app(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
