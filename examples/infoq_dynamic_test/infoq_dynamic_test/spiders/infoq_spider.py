# -*- coding: UTF-8 -*-
"""
InfoQ AI 快讯爬虫
==================
测试动态下载器对 AI 快讯页 https://www.infoq.cn/aibriefs 的解析。

页面结构（基于 demo.html 实际抓取结果）：
  _aibriefs-list_u5zau_105          — 列表容器
  _aibriefs-list-item_gicxd_61       — 每条快讯
    _aibriefs-list-item-left_gicxd_65 — 日期区域
      _aibriefs-list-item-left-month_gicxd_78  — 月份（如 "07月"）
      _aibriefs-list-item-left-day_gicxd_84    — 日（如 "03"）
      _aibriefs-list-item-left-year_gicxd_91   — 年（如 "2026"）
    _content-item_gicxd_98             — 内容区域
      _item_ndgee_65                   — 条目
        _title_ndgee_69                — 标题
        _info_ndgee_76                 — 信息行
          _item-time_ndgee_82          — 时间（如 "13:16"）
        _desc_ndgee_165               — 描述/全文
"""
import os
from crawlo import Spider, Request
from ..items import InfoqArticle


class InfoqSpider(Spider):
    """InfoQ AI 快讯爬虫"""

    name = 'infoq_spider'

    START_URL = 'https://www.infoq.cn/aibriefs'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_mode = os.environ.get('TEST_MODE', 'dynamic_meta')

    def start_requests(self):
        """生成起始请求"""
        # JS 循环：自动翻页直到按钮消失（async 模式，CloakBrowser 兼容）
        LOAD_MORE_JS = """async () => {
            const sel = 'div[class*="_look-more_"]';
            const wait = ms => new Promise(r => setTimeout(r, ms));
            let noNew = 0;
            while (noNew < 3) {
                window.scrollTo(0, document.body.scrollHeight);
                await wait(500);
                const btn = document.querySelector(sel);
                if (btn && btn.offsetParent !== null) {
                    btn.click();
                    await wait(2000);
                    noNew = 0;
                } else {
                    noNew++;
                    await wait(500);
                }
            }
        }"""

        yield Request(
            url=self.START_URL,
            callback=self.parse,
            dont_filter=True,
            meta={
                'use_dynamic_loader': True,
                'cloakbrowser_auto_scroll': True,
                'cloakbrowser_scroll_delay': 500,
                'cloakbrowser_block_resources': ["image", "font", "media"],
                'dynamic_actions': [
                    {'type': 'evaluate', 'params': {'script': LOAD_MORE_JS}},
                ],
            }
        )

    def parse(self, response):
        """解析 AI 快讯列表页"""
        self.logger.info(
            f"[{response.status}] {response.url} "
            f"({len(response.text)} bytes)"
        )

        # 提取快讯列表
        article_items = response.xpath(
            '//div[contains(@class, "_aibriefs-list-item_")]'
        )
        self.logger.info(f"items: {len(article_items)}")

        # 提取信息（含去重检查）
        seen_titles = set()
        ordered_titles = []  # 有序标题列表（用于详情页引用）
        duplicates = 0
        for item in article_items:
            title = item.xpath(
                './/div[contains(@class, "_title_")]/text()'
            ).get('') or ''
            desc = item.xpath(
                './/div[contains(@class, "_desc_")]/text()'
            ).get('') or ''
            month = item.xpath(
                './/div[contains(@class, "left-month")]/text()'
            ).get('') or ''
            day = item.xpath(
                './/div[contains(@class, "left-day")]/text()'
            ).get('') or ''
            year = item.xpath(
                './/div[contains(@class, "left-year")]/text()'
            ).get('') or ''
            time_str = item.xpath(
                './/div[contains(@class, "_item-time_")]/text()'
            ).get('') or ''

            month_clean = month.replace('月', '').strip()
            date_parts = [p for p in [year, month_clean, day] if p]
            date_str = '-'.join(date_parts)
            if time_str:
                date_str = f"{date_str} {time_str}"

            title_stripped = title.strip()
            if title_stripped in seen_titles:
                duplicates += 1
                continue
            seen_titles.add(title_stripped)
            ordered_titles.append(title_stripped)

            yield InfoqArticle(
                url=response.url,
                title=title_stripped,
                content=desc.strip(),
                date=date_str,
                source='infoq.cn',
                type='aibrief'
            )

        self.logger.info(f"unique: {len(seen_titles)}, duplicates skipped: {duplicates}")

        if len(article_items) == 0:
            self.logger.warning("no items found, dumping HTML...")
            self.logger.warning(response.text[:2000])

        # 尝试展开第一条快讯的更多内容（如果有 _more 按钮）
        self.logger.info("expanding first item...")
        yield Request(
            url=response.url,
            callback=self.parse_detail,
            dont_filter=True,
            meta={
                'use_dynamic_loader': True,
                'dynamic_actions': [{
                    'type': 'click_and_wait',
                    'params': {
                        'selector': (
                            '(//div[contains(@class, "_aibriefs-list-item_")])[1]'
                            '//div[contains(@class, "_more_")]'
                        ),
                        'wait_timeout': 2000,
                        'wait_for': 'networkidle',
                    }
                }],
                'article_title': ordered_titles[0] if ordered_titles else '',
            }
        )

    def parse_detail(self, response):
        """解析详情/展开后的快讯内容"""
        title = response.meta.get('article_title', '')
        self.logger.info(
            f"[detail] {response.url} ({len(response.text)} bytes)"
        )

        content = response.xpath(
            '(//div[@class="_desc_ndgee_165"])[1]/text()'
        ).get('') or ''

        self.logger.info(f"title: {title}, content: {len(content)} chars")
        yield InfoqArticle(
            url=response.url,
            title=title,
            content=content,
            source='infoq.cn',
            type='detail'
        )
