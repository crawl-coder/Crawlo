#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo框架数据清洗工具使用示例
"""
from crawlo.tools import (
    TextCleaner,
    DataFormatter,
    remove_html_tags,
    decode_html_entities,
    clean_text,
    extract_numbers,
    extract_emails,
    extract_urls,
    format_number,
    format_currency,
    format_phone_number,
    format_chinese_id_card
)


def demo_text_cleaner():
    """演示文本清洗工具的使用"""
    print("=== 文本清洗工具演示 ===\n")
    
    # 1. 移除HTML标签
    print("1. 移除HTML标签:")
    html_text = "<p>这是一个<b>测试</b>文本</p>"
    clean_text_result = remove_html_tags(html_text)
    print(f"  原始文本: {html_text}")
    print(f"  清洗后: {clean_text_result}")
    
    print()
    
    # 2. 解码HTML实体
    print("2. 解码HTML实体:")
    entity_text = "这是一个&nbsp;<b>测试</b>&amp;文本"
    decoded_text = decode_html_entities(entity_text)
    print(f"  原始文本: {entity_text}")
    print(f"  解码后: {decoded_text}")
    
    print()
    
    # 3. 移除多余空白字符
    print("3. 移除多余空白字符:")
    whitespace_text = "这是   一个\t\t测试\n\n文本"
    clean_whitespace = TextCleaner.remove_extra_whitespace(whitespace_text)
    print(f"  原始文本: {repr(whitespace_text)}")
    print(f"  清洗后: {repr(clean_whitespace)}")
    
    print()
    
    # 4. 综合清洗
    print("4. 综合清洗:")
    complex_text = "<p>这是&nbsp;一个<b>测试</b>&amp;文本&nbsp;&nbsp;</p>"
    cleaned = clean_text(complex_text)
    print(f"  原始文本: {complex_text}")
    print(f"  清洗后: {cleaned}")
    
    print()
    
    # 5. 提取信息
    print("5. 提取信息:")
    info_text = "联系邮箱: test@example.com, 电话: 13812345678, 价格: ¥123.45"
    numbers = extract_numbers(info_text)
    emails = extract_emails(info_text)
    urls = extract_urls(info_text)
    print(f"  原始文本: {info_text}")
    print(f"  提取的数字: {numbers}")
    print(f"  提取的邮箱: {emails}")
    print(f"  提取的URL: {urls}")


def demo_data_formatter():
    """演示数据格式化工具的使用"""
    print("\n=== 数据格式化工具演示 ===\n")
    
    # 1. 数字格式化
    print("1. 数字格式化:")
    number = 1234567.891
    formatted_num1 = format_number(number, precision=2, thousand_separator=False)
    formatted_num2 = format_number(number, precision=2, thousand_separator=True)
    print(f"  原始数字: {number}")
    print(f"  格式化(无千位分隔符): {formatted_num1}")
    print(f"  格式化(有千位分隔符): {formatted_num2}")
    
    print()
    
    # 2. 货币格式化
    print("2. 货币格式化:")
    price = 1234.567
    formatted_currency1 = format_currency(price, "¥", 2)
    formatted_currency2 = format_currency(price, "$", 2)
    print(f"  原始价格: {price}")
    print(f"  人民币格式: {formatted_currency1}")
    print(f"  美元格式: {formatted_currency2}")
    
    print()
    
    # 3. 电话号码格式化
    print("3. 电话号码格式化:")
    phone = "13812345678"
    formatted_phone1 = format_phone_number(phone, "+86", "international")
    formatted_phone2 = format_phone_number(phone, "", "domestic")
    formatted_phone3 = format_phone_number(phone, "", "plain")
    print(f"  原始号码: {phone}")
    print(f"  国际格式: {formatted_phone1}")
    print(f"  国内格式: {formatted_phone2}")
    print(f"  纯数字格式: {formatted_phone3}")
    
    print()
    
    # 4. 身份证号码格式化
    print("4. 身份证号码格式化:")
    id_card = "110101199001011234"
    formatted_id = format_chinese_id_card(id_card)
    print(f"  原始号码: {id_card}")
    print(f"  格式化后: {formatted_id}")


def demo_in_spider():
    """演示在爬虫中使用数据清洗工具"""
    print("\n=== 在爬虫中使用数据清洗工具 ===\n")
    print("在爬虫项目中，您可以这样使用数据清洗工具:")
    print("""
from crawlo import Spider, Request, Item, Field
from crawlo.tools import clean_text, format_currency, extract_numbers

class ProductItem(Item):
    name = Field()
    price = Field()
    description = Field()

class ProductSpider(Spider):
    def parse(self, response):
        # 从网页中提取数据
        name = response.css('.product-name::text').get()
        price_text = response.css('.price::text').get()
        description = response.css('.description::text').get()
        
        # 清洗和格式化数据
        clean_name = clean_text(name) if name else None
        price_numbers = extract_numbers(price_text) if price_text else []
        clean_price = format_currency(price_numbers[0]) if price_numbers else None
        clean_description = clean_text(description) if description else None
        
        # 创建数据项
        item = ProductItem()
        item['name'] = clean_name
        item['price'] = clean_price
        item['description'] = clean_description
        
        yield item
    """)


if __name__ == '__main__':
    # 运行演示
    demo_text_cleaner()
    demo_data_formatter()
    demo_in_spider()