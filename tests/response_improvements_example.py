#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Response 改进功能使用示例
"""
from crawlo.network.response import Response


def demo_response_improvements():
    """演示Response改进功能"""
    print("=== Response 改进功能演示 ===\n")
    
    # 创建一个示例HTML响应
    html_content = """
    <html>
    <head>
        <title>Crawlo框架示例页面</title>
    </head>
    <body>
        <div class="container">
            <h1>产品列表</h1>
            <div class="product-list">
                <div class="product-item" data-id="1">
                    <h2>产品A</h2>
                    <p class="price">¥99.99</p>
                    <p class="description">这是产品A的描述信息</p>
                    <a href="/product/1" class="details-link">查看详情</a>
                </div>
                <div class="product-item" data-id="2">
                    <h2>产品B</h2>
                    <p class="price">¥149.99</p>
                    <p class="description">这是产品B的描述信息</p>
                    <a href="/product/2" class="details-link">查看详情</a>
                </div>
                <div class="product-item" data-id="3">
                    <h2>产品C</h2>
                    <p class="price">¥199.99</p>
                    <p class="description">这是产品C的描述信息</p>
                    <a href="/product/3" class="details-link">查看详情</a>
                </div>
            </div>
            <div class="pagination">
                <a href="/page/1" class="page-link">1</a>
                <a href="/page/2" class="page-link active">2</a>
                <a href="/page/3" class="page-link">3</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    # 创建Response对象
    response = Response(
        url="https://example.com/products",
        body=html_content.encode('utf-8'),
        headers={"content-type": "text/html; charset=utf-8"}
    )
    
    # 1. 演示 extract_text 方法（支持CSS和XPath）
    print("1. 提取文本内容:")
    title = response.extract_text('title')
    print(f"   页面标题: {title}")
    
    # 使用CSS选择器提取第一个产品名称
    first_product_name = response.extract_text('.product-item:first-child h2')
    print(f"   第一个产品名称 (CSS): {first_product_name}")
    
    # 使用XPath选择器
    first_product_name_xpath = response.extract_text('//div[@class="product-item"][1]/h2')
    print(f"   第一个产品名称 (XPath): {first_product_name_xpath}")
    
    # 使用默认值处理不存在的元素
    non_exist = response.extract_text('.non-exist', default='未找到')
    print(f"   不存在的元素: {non_exist}")
    
    print()
    
    # 2. 演示 extract_texts 方法（提取多个元素的文本）
    print("2. 提取多个元素的文本:")
    # 提取所有产品名称
    product_names = response.extract_texts('.product-item h2')
    print(f"   所有产品名称: {product_names}")
    
    # 提取所有价格
    prices = response.extract_texts('.price')
    print(f"   所有价格: {prices}")
    
    # 使用XPath提取所有产品名称
    product_names_xpath = response.extract_texts('//div[@class="product-item"]/h2')
    print(f"   所有产品名称 (XPath): {product_names_xpath}")
    
    print()
    
    # 3. 演示 extract_attr 方法（提取元素属性）
    print("3. 提取元素属性:")
    # 提取第一个产品项的data-id属性
    first_product_id = response.extract_attr('.product-item', 'data-id')
    print(f"   第一个产品ID: {first_product_id}")
    
    # 提取详情链接的href属性
    first_detail_link = response.extract_attr('.details-link', 'href')
    print(f"   第一个详情链接: {first_detail_link}")
    
    # 提取不存在属性的默认值
    non_exist_attr = response.extract_attr('.product-item', 'non-exist', default='默认值')
    print(f"   不存在的属性: {non_exist_attr}")
    
    print()
    
    # 4. 演示 extract_attrs 方法（提取多个元素的属性）
    print("4. 提取多个元素的属性:")
    # 提取所有产品项的data-id属性
    product_ids = response.extract_attrs('.product-item', 'data-id')
    print(f"   所有产品ID: {product_ids}")
    
    # 提取所有详情链接的href属性
    detail_links = response.extract_attrs('.details-link', 'href')
    print(f"   所有详情链接: {detail_links}")
    
    # 提取分页链接的href属性
    page_links = response.extract_attrs('.page-link', 'href')
    print(f"   分页链接: {page_links}")
    
    print()
    
    # 5. 演示复杂文本提取
    print("5. 复杂文本提取:")
    # 提取所有产品描述
    descriptions = response.extract_texts('.description')
    print(f"   所有产品描述: {descriptions}")
    
    print()
    
    # 6. 边界情况处理
    print("6. 边界情况处理:")
    # 空响应测试
    empty_response = Response(url="https://example.com/empty", body=b"")
    empty_text = empty_response.extract_text('title', default='默认标题')
    print(f"   空响应默认值: {empty_text}")
    
    print("\n=== 演示完成 ===")


if __name__ == '__main__':
    demo_response_improvements()