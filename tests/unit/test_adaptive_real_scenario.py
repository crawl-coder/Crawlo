#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
自适应元素追踪真实场景测试

模拟场景：
1. 首次爬取：网站结构正常，选择器命中，自动保存指纹
2. 网站改版：HTML 结构变化（class 名改变），原选择器失效
3. 自适应恢复：使用指纹自动匹配最相似的元素

测试流程：
- 阶段1：正常页面 → 验证指纹保存
- 阶段2：模拟网站改版 → 验证自适应匹配
- 阶段3：对比结果 → 验证数据完整性
"""

import os
import sys
import tempfile
from pathlib import Path

# 添加 Crawlo 到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from crawlo.network.response import Response
from parsel import Selector


# 模拟原始页面 HTML（首次爬取）
ORIGINAL_HTML = """
<!DOCTYPE html>
<html>
<body>
    <div class="main_left">
        <div class="list_model">
            <div class="model_right model_right2">
                <h3><a href="/article1.html">2024年半导体行业分析报告</a></h3>
                <div class="info">发布时间：2024-01-15</div>
            </div>
            <div class="model_right model_right2">
                <h3><a href="/article2.html">新能源汽车市场趋势</a></h3>
                <div class="info">发布时间：2024-01-16</div>
            </div>
            <div class="model_right model_right2">
                <h3><a href="/article3.html">5G技术应用前景</a></h3>
                <div class="info">发布时间：2024-01-17</div>
            </div>
        </div>
    </div>
</body>
</html>
"""

# 模拟改版后页面 HTML（class 名改变，但结构相似）
MODIFIED_HTML = """
<!DOCTYPE html>
<html>
<body>
    <div class="content_area">
        <div class="news_list">
            <div class="article_card card_style">
                <h3><a href="/article1.html">2024年半导体行业分析报告</a></h3>
                <div class="metadata">发布时间：2024-01-15</div>
            </div>
            <div class="article_card card_style">
                <h3><a href="/article2.html">新能源汽车市场趋势</a></h3>
                <div class="metadata">发布时间：2024-01-16</div>
            </div>
            <div class="article_card card_style">
                <h3><a href="/article3_new.html">6G技术最新进展</a></h3>
                <div class="metadata">发布时间：2024-01-18</div>
            </div>
        </div>
    </div>
</body>
</html>
"""


class TestAdaptiveTracking:
    """自适应元素追踪测试"""

    def __init__(self):
        self.temp_db = tempfile.mktemp(suffix='.db')
        self.results = {
            'phase1_save': {},
            'phase2_adaptive': {},
            'success': False
        }

    def setup(self):
        """配置自适应追踪"""
        Response.configure_adaptive(
            backend='sqlite',
            storage_file=self.temp_db,
            threshold=0.0
        )
        print(f"✓ 自适应追踪已配置，数据库: {self.temp_db}")

    def cleanup(self):
        """清理测试文件"""
        # 重置自适应状态
        Response._adaptive_enabled_global = None
        Response._adaptive_storage = None
        Response._adaptive_matcher = None
        
        import time
        time.sleep(0.5)  # 等待文件释放
        
        if os.path.exists(self.temp_db):
            try:
                os.remove(self.temp_db)
                print(f"\n✓ 已清理测试数据库: {self.temp_db}")
            except PermissionError:
                print(f"\n⚠ 数据库文件稍后手动删除: {self.temp_db}")

    def phase1_normal_page(self):
        """阶段1：正常页面 - 验证指纹保存"""
        print("\n" + "="*60)
        print("阶段1：正常页面爬取（保存指纹）")
        print("="*60)

        response = Response(
            url='https://ee.ofweek.com/test.html',
            body=ORIGINAL_HTML.encode('utf-8')
        )

        # 使用 adaptive=True 提取列表项
        selector = '//div[@class="model_right model_right2"]'
        items = response.xpath(selector, adaptive=True, identifier='list_item_selector')

        print(f"\n原始选择器: {selector}")
        print(f"提取到 {len(items)} 个元素:")

        self.results['phase1_save']['count'] = len(items)
        self.results['phase1_save']['titles'] = []

        for i, item in enumerate(items, 1):
            title = item.xpath('./h3/a/text()').extract_first()
            link = item.xpath('./h3/a/@href').extract_first()
            print(f"  [{i}] {title} -> {link}")
            self.results['phase1_save']['titles'].append(title)

        # 验证指纹已保存
        fingerprint = Response._adaptive_storage.retrieve(
            'https://ee.ofweek.com/test.html',
            'list_item_selector'
        )
        if fingerprint:
            print(f"\n✓ 指纹已保存")
            print(f"  - 标签: {fingerprint.get('tag', 'N/A')}")
            text_preview = fingerprint.get('text', '') or ''
            print(f"  - 文本: {text_preview[:50]}...")
            path = fingerprint.get('path', [])
            print(f"  - 路径: {' > '.join(path[-3:]) if path else 'N/A'}")
            self.results['phase1_save']['fingerprint_saved'] = True
        else:
            print("\n✗ 指纹保存失败")
            self.results['phase1_save']['fingerprint_saved'] = False

        return len(items) > 0

    def phase2_modified_page(self):
        """阶段2：改版页面 - 验证自适应匹配"""
        print("\n" + "="*60)
        print("阶段2：网站改版后爬取（自适应匹配）")
        print("="*60)

        response = Response(
            url='https://ee.ofweek.com/test.html',
            body=MODIFIED_HTML.encode('utf-8')
        )

        # 原始选择器（应该失效）
        original_selector = '//div[@class="model_right model_right2"]'
        original_result = response.xpath(original_selector)

        print(f"\n原始选择器: {original_selector}")
        print(f"原始选择器结果: {len(original_result)} 个元素（应该为0）")

        if len(original_result) == 0:
            print("✓ 原始选择器已失效（符合预期）")

        # 使用 adaptive=True 自动匹配
        print("\n尝试自适应匹配...")
        adaptive_items = response.xpath(
            original_selector,
            adaptive=True,
            identifier='list_item_selector'
        )

        print(f"自适应匹配结果: {len(adaptive_items)} 个元素")

        self.results['phase2_adaptive']['count'] = len(adaptive_items)
        self.results['phase2_adaptive']['titles'] = []

        for i, item in enumerate(adaptive_items, 1):
            title = item.xpath('./h3/a/text()').extract_first()
            link = item.xpath('./h3/a/@href').extract_first()
            print(f"  [{i}] {title} -> {link}")
            self.results['phase2_adaptive']['titles'].append(title)

        return len(adaptive_items) > 0

    def phase3_verify_results(self):
        """阶段3：验证结果"""
        print("\n" + "="*60)
        print("阶段3：结果验证")
        print("="*60)

        phase1_count = self.results['phase1_save']['count']
        phase2_count = self.results['phase2_adaptive']['count']
        phase1_titles = set(self.results['phase1_save']['titles'])
        phase2_titles = set(self.results['phase2_adaptive']['titles'])

        # 验证提取数量
        print(f"\n提取数量对比:")
        print(f"  - 原始页面: {phase1_count} 个元素")
        print(f"  - 改版页面: {phase2_count} 个元素")

        # 验证共同标题（应该有2个相同，1个不同）
        common_titles = phase1_titles & phase2_titles
        new_titles = phase2_titles - phase1_titles

        print(f"\n标题匹配情况:")
        print(f"  - 共同标题: {len(common_titles)} 个")
        for title in common_titles:
            print(f"    ✓ {title}")

        print(f"  - 新增标题: {len(new_titles)} 个")
        for title in new_titles:
            print(f"    + {title}")

        # 综合判断
        success = (
            phase1_count >= 3 and
            phase2_count >= 2 and
            len(common_titles) >= 2 and
            self.results['phase1_save']['fingerprint_saved']
        )

        print(f"\n{'='*60}")
        if success:
            print("✓✓✓ 测试通过：自适应元素追踪功能正常！")
            print(f"{'='*60}")
            print("\n核心能力验证:")
            print("  1. ✓ 选择器命中时自动保存指纹")
            print("  2. ✓ 选择器失效时自动匹配相似元素")
            print("  3. ✓ 基于多维度相似度准确匹配")
            print("  4. ✓ 成功提取改版后页面的数据")
        else:
            print("✗✗✗ 测试失败：自适应元素追踪功能异常")
            print(f"{'='*60}")

        self.results['success'] = success
        return success

    def run(self):
        """运行完整测试"""
        try:
            self.setup()

            # 阶段1：正常页面
            if not self.phase1_normal_page():
                print("\n✗ 阶段1失败，终止测试")
                return False

            # 阶段2：改版页面
            if not self.phase2_modified_page():
                print("\n✗ 阶段2失败，终止测试")
                return False

            # 阶段3：验证结果
            return self.phase3_verify_results()

        finally:
            self.cleanup()


if __name__ == '__main__':
    print("自适应元素追踪真实场景测试")
    print("="*60)

    test = TestAdaptiveTracking()
    success = test.run()

    sys.exit(0 if success else 1)
