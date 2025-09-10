# 数据清洗工具

Crawlo 框架提供了一套完整的数据清洗工具，专门针对爬虫场景中常见的数据处理需求进行了优化。

## 功能特性

1. **文本清洗**：移除HTML标签、解码HTML实体、清理空白字符等
2. **数据提取**：从文本中提取数字、邮箱、URL等信息
3. **数据格式化**：数字、货币、电话号码、身份证等格式化
4. **编码转换**：处理不同编码的网页内容

## 使用方法

### 导入工具

```python
from crawlo.cleaners import (
    TextCleaner,        # 文本清洗工具类
    DataFormatter,      # 数据格式化工具类
    EncodingConverter,  # 编码转换工具类
    
    # 文本清洗函数
    remove_html_tags,
    decode_html_entities,
    clean_text,
    extract_numbers,
    extract_emails,
    extract_urls,
    
    # 数据格式化函数
    format_number,
    format_currency,
    format_phone_number,
    format_chinese_id_card,
    
    # 编码转换函数
    detect_encoding,
    to_utf8,
    convert_encoding
)
```

### 文本清洗

```python
from crawlo.cleaners import clean_text, remove_html_tags, decode_html_entities

# 移除HTML标签
html_text = "<p>这是一个<b>测试</b>文本</p>"
clean_text_result = remove_html_tags(html_text)
# 结果: "这是一个测试文本"

# 解码HTML实体
entity_text = "这是一个&nbsp;测试&amp;文本"
decoded_text = decode_html_entities(entity_text)
# 结果: "这是一个 测试&文本"

# 综合清洗
complex_text = "<p>这是&nbsp;一个<b>测试</b>&amp;文本</p>"
cleaned = clean_text(complex_text)
# 结果: "这是 一个测试&文本"
```

### 数据提取

```python
from crawlo.cleaners import extract_numbers, extract_emails, extract_urls

# 提取数字
text = "价格: ¥123.45, 数量: 100"
numbers = extract_numbers(text)
# 结果: ['123.45', '100']

# 提取邮箱
text = "联系邮箱: test@example.com"
emails = extract_emails(text)
# 结果: ['test@example.com']

# 提取URL
text = "网站: https://example.com"
urls = extract_urls(text)
# 结果: ['https://example.com']
```

### 数据格式化

```python
from crawlo.cleaners import format_number, format_currency, format_phone_number

# 数字格式化
number = 1234567.891
formatted_num = format_number(number, precision=2, thousand_separator=True)
# 结果: "1,234,567.89"

# 货币格式化
price = 1234.567
formatted_currency = format_currency(price, "¥", 2)
# 结果: "¥1,234.57"

# 电话号码格式化
phone = "13812345678"
formatted_phone = format_phone_number(phone, "+86", "international")
# 结果: "+86 138 1234 5678"
```

### 编码转换

```python
from crawlo.cleaners import detect_encoding, to_utf8

# 检测编码
data = b'\xe4\xb8\xad\xe6\x96\x87'  # UTF-8编码的"中文"
encoding = detect_encoding(data)
# 结果: "utf-8"

# 转换为UTF-8
utf8_str = to_utf8(data)
# 结果: "中文"
```

## 在爬虫中的应用

```python
from crawlo import Spider, Request, Item, Field
from crawlo.cleaners import clean_text, format_currency, extract_numbers

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
```

## TextCleaner 类方法

- `TextCleaner.remove_html_tags()`: 移除HTML标签
- `TextCleaner.decode_html_entities()`: 解码HTML实体字符
- `TextCleaner.remove_extra_whitespace()`: 移除多余空白字符
- `TextCleaner.remove_special_chars()`: 移除特殊字符
- `TextCleaner.normalize_unicode()`: 标准化Unicode字符
- `TextCleaner.clean_text()`: 综合文本清洗
- `TextCleaner.extract_numbers()`: 提取数字
- `TextCleaner.extract_emails()`: 提取邮箱地址
- `TextCleaner.extract_urls()`: 提取URL

## DataFormatter 类方法

- `DataFormatter.format_number()`: 格式化数字
- `DataFormatter.format_currency()`: 格式化货币
- `DataFormatter.format_percentage()`: 格式化百分比
- `DataFormatter.format_phone_number()`: 格式化电话号码
- `DataFormatter.format_chinese_id_card()`: 格式化中国身份证号码
- `DataFormatter.capitalize_words()`: 单词首字母大写

## EncodingConverter 类方法

- `EncodingConverter.detect_encoding()`: 检测数据编码
- `EncodingConverter.to_utf8()`: 转换为UTF-8编码的字符串
- `EncodingConverter.convert_encoding()`: 编码转换

这些工具使得在爬虫项目中处理各种复杂的数据清洗和格式化需求变得简单而可靠。