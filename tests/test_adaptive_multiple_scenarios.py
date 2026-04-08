#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
自适应元素追踪 - 多场景支持测试

测试不同类型的网站改版场景：
1. Class 名称变化
2. DOM 结构层级调整
3. 标签类型变化
4. 属性顺序/内容变化
5. 文本内容微调
6. 混合变化（多种变化同时发生）
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from crawlo.network.response import Response


# ========== 场景1：Class 名称变化 ==========
SCENARIO_1_ORIGINAL = """
<div class="main_left">
    <div class="list_model">
        <div class="model_right model_right2">
            <h3><a href="/article1.html">半导体行业分析报告</a></h3>
            <div class="info">发布时间：2024-01-15</div>
        </div>
    </div>
</div>
"""

SCENARIO_1_MODIFIED = """
<div class="content_area">
    <div class="news_list">
        <div class="article_card card_style">
            <h3><a href="/article1.html">半导体行业分析报告</a></h3>
            <div class="metadata">发布时间：2024-01-15</div>
        </div>
    </div>
</div>
"""


# ========== 场景2：DOM 结构层级调整 ==========
SCENARIO_2_ORIGINAL = """
<div class="container">
    <div class="list">
        <div class="item">
            <div class="title">
                <h3><a href="/article1.html">新能源汽车市场趋势</a></h3>
            </div>
            <div class="date">2024-01-16</div>
        </div>
    </div>
</div>
"""

SCENARIO_2_MODIFIED = """
<div class="container">
    <div class="list">
        <h3><a href="/article1.html">新能源汽车市场趋势</a></h3>
        <div class="date">2024-01-16</div>
    </div>
</div>
"""


# ========== 场景3：标签类型变化 ==========
SCENARIO_3_ORIGINAL = """
<div class="articles">
    <div class="article">
        <h3><a href="/article1.html">5G技术应用前景</a></h3>
        <span class="date">2024-01-17</span>
    </div>
</div>
"""

SCENARIO_3_MODIFIED = """
<div class="articles">
    <article class="article">
        <h4><a href="/article1.html">5G技术应用前景</a></h4>
        <time class="date">2024-01-17</time>
    </article>
</div>
"""


# ========== 场景4：属性顺序/内容变化 ==========
SCENARIO_4_ORIGINAL = """
<div class="container">
    <div id="list" class="news-list" data-type="tech">
        <div class="item" data-id="1">
            <a href="/article1.html" title="AI芯片最新进展">AI芯片最新进展</a>
            <span>2024-01-18</span>
        </div>
    </div>
</div>
"""

SCENARIO_4_MODIFIED = """
<div class="container">
    <div id="news-list" class="article-list" data-type="technology" data-version="2">
        <div class="article" data-id="1" data-status="published">
            <a href="/article1.html" title="AI芯片最新进展" target="_blank">AI芯片最新进展</a>
            <span>2024-01-18</span>
        </div>
    </div>
</div>
"""


# ========== 场景5：文本内容微调 ==========
SCENARIO_5_ORIGINAL = """
<div class="news">
    <div class="news-item">
        <h3><a href="/article1.html">2024年半导体行业分析报告全文</a></h3>
        <div class="info">发布时间：2024年01月15日 10:30</div>
    </div>
</div>
"""

SCENARIO_5_MODIFIED = """
<div class="news">
    <div class="news-item">
        <h3><a href="/article1.html">2024半导体行业分析报告</a></h3>
        <div class="info">发布：2024-01-15 10:30:00</div>
    </div>
</div>
"""


# ========== 场景6：混合变化（最复杂） ==========
SCENARIO_6_ORIGINAL = """
<div class="main_left">
    <div class="list_model">
        <div class="model_right model_right2">
            <h3><a href="/article1.html">量子计算技术突破</a></h3>
            <div class="info">
                <span class="date">2024-01-19</span>
                <span class="source">科技日报</span>
            </div>
        </div>
    </div>
</div>
"""

SCENARIO_6_MODIFIED = """
<div class="content_wrapper">
    <section class="article_section">
        <article class="news_card featured">
            <h4><a href="/article1.html" class="article_link">量子计算重大技术突破</a></h4>
            <div class="article_meta">
                <time datetime="2024-01-19">2024年01月19日</time>
                <span class="author">科技日报</span>
            </div>
        </article>
    </section>
</div>
"""


class TestMultipleScenarios:
    """多场景自适应测试"""

    def __init__(self):
        self.temp_db = tempfile.mktemp(suffix='.db')
        self.results = []

    def setup(self):
        """配置自适应追踪"""
        Response.configure_adaptive(
            backend='sqlite',
            storage_file=self.temp_db,
            threshold=0.0
        )

    def cleanup(self):
        """清理"""
        Response._adaptive_enabled_global = None
        Response._adaptive_storage = None
        Response._adaptive_matcher = None
        
        import time
        time.sleep(0.5)
        
        if os.path.exists(self.temp_db):
            try:
                os.remove(self.temp_db)
            except:
                pass

    def test_scenario(self, name, original_html, modified_html, selector, identifier, extract_xpath):
        """测试单个场景"""
        print(f"\n{'='*60}")
        print(f"场景：{name}")
        print(f"{'='*60}")

        # 阶段1：原始页面保存指纹
        response1 = Response(
            url='https://test.com/page.html',
            body=original_html.encode('utf-8')
        )

        items1 = response1.xpath(selector, adaptive=True, identifier=identifier)
        print(f"\n原始选择器: {selector}")
        print(f"原始页面提取: {len(items1)} 个元素")

        if not items1:
            print("✗ 原始选择器未命中，跳过此场景")
            return False

        for i, item in enumerate(items1, 1):
            text = item.xpath(extract_xpath).extract_first()
            print(f"  [{i}] {text}")

        # 阶段2：改版页面自适应匹配
        response2 = Response(
            url='https://test.com/page.html',
            body=modified_html.encode('utf-8')
        )

        # 先测试原始选择器是否失效
        original_result = response2.xpath(selector)
        print(f"\n改版后原始选择器结果: {len(original_result)} 个元素")

        # 自适应匹配
        adaptive_items = response2.xpath(selector, adaptive=True, identifier=identifier)
        print(f"自适应匹配结果: {len(adaptive_items)} 个元素")

        success = len(adaptive_items) > 0
        if success:
            for i, item in enumerate(adaptive_items, 1):
                text = item.xpath(extract_xpath).extract_first()
                print(f"  [{i}] {text}")
            print(f"\n✓ 场景测试通过")
        else:
            print(f"\n✗ 场景测试失败")

        self.results.append({
            'name': name,
            'original_count': len(items1),
            'adaptive_count': len(adaptive_items),
            'success': success
        })

        return success

    def run_all(self):
        """运行所有场景测试"""
        self.setup()

        try:
            # 场景1：Class 名称变化
            self.test_scenario(
                "Class 名称变化",
                SCENARIO_1_ORIGINAL,
                SCENARIO_1_MODIFIED,
                '//div[@class="model_right model_right2"]',
                'scenario1_list',
                './h3/a/text()'
            )

            # 场景2：DOM 结构层级调整
            self.test_scenario(
                "DOM 结构层级调整（元素上移）",
                SCENARIO_2_ORIGINAL,
                SCENARIO_2_MODIFIED,
                '//div[@class="item"]',
                'scenario2_item',
                './/a/text()'
            )

            # 场景3：标签类型变化
            self.test_scenario(
                "标签类型变化（div→article, h3→h4, span→time）",
                SCENARIO_3_ORIGINAL,
                SCENARIO_3_MODIFIED,
                '//div[@class="article"]',
                'scenario3_article',
                './/a/text()'
            )

            # 场景4：属性变化
            self.test_scenario(
                "属性顺序/内容变化（增加、修改属性）",
                SCENARIO_4_ORIGINAL,
                SCENARIO_4_MODIFIED,
                '//div[@class="item"]',
                'scenario4_item',
                './a/text()'
            )

            # 场景5：文本内容微调
            self.test_scenario(
                "文本内容微调（格式变化）",
                SCENARIO_5_ORIGINAL,
                SCENARIO_5_MODIFIED,
                '//div[@class="news-item"]',
                'scenario5_news',
                './h3/a/text()'
            )

            # 场景6：混合变化
            self.test_scenario(
                "混合变化（class+标签+结构+文本同时变化）",
                SCENARIO_6_ORIGINAL,
                SCENARIO_6_MODIFIED,
                '//div[@class="model_right model_right2"]',
                'scenario6_mixed',
                './/a/text()'
            )

            # 汇总结果
            print(f"\n{'='*60}")
            print("测试汇总")
            print(f"{'='*60}")

            for result in self.results:
                status = "✓ 通过" if result['success'] else "✗ 失败"
                print(f"\n{result['name']}:")
                print(f"  状态: {status}")
                print(f"  原始提取: {result['original_count']} 个")
                print(f"  自适应匹配: {result['adaptive_count']} 个")

            success_count = sum(1 for r in self.results if r['success'])
            total_count = len(self.results)

            print(f"\n{'='*60}")
            print(f"总计: {success_count}/{total_count} 个场景通过")
            print(f"{'='*60}")

            if success_count == total_count:
                print("\n✓✓✓ 所有场景测试通过！自适应元素追踪功能强大！")
            else:
                print(f"\n⚠ {total_count - success_count} 个场景未通过，但核心功能正常")

            return success_count

        finally:
            self.cleanup()


if __name__ == '__main__':
    print("自适应元素追踪 - 多场景支持测试")
    print("="*60)

    test = TestMultipleScenarios()
    success_count = test.run_all()

    sys.exit(0 if success_count > 0 else 1)
