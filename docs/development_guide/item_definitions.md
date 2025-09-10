# 数据项定义

在 Crawlo 框架中，[Item](file:///d%3A/dowell/projects/Crawlo/crawlo/items/items.py#L15-L103) 类用于定义结构化数据，类似于 Django 的 Model 或 Pydantic 的 BaseModel。Item 提供了字段定义、数据验证和类型检查等功能。

## 基本概念

Item 是数据容器，用于存储从网页中提取的结构化数据。每个 Item 类定义了一组字段，这些字段描述了要提取的数据的结构和类型。

## 定义 Item

要定义一个 Item，需要继承 [crawlo.items.Item](file:///d%3A/dowell/projects/Crawlo/crawlo/items/items.py#L15-L103) 类，并使用 [Field](file:///d%3A/dowell/projects/Crawlo/crawlo/items/fields.py#L10-L52) 对象定义字段：

```python
from crawlo.items import Item, Field

class ProductItem(Item):
    name = Field(description="产品名称")
    price = Field(field_type=float, description="产品价格")
    in_stock = Field(field_type=bool, default=True, description="是否有库存")
```

## Field 字段

[Field](file:///d%3A/dowell/projects/Crawlo/crawlo/items/fields.py#L10-L52) 类用于定义 Item 的字段属性和验证规则。

### Field 参数

- `nullable` (bool): 字段是否允许为空，默认为 `True`
- `default` (Any): 字段的默认值
- `field_type` (Type): 字段的数据类型
- `max_length` (int): 字段的最大长度（仅对字符串有效）
- `description` (str): 字段的描述信息

### Field 示例

```python
class ExampleItem(Item):
    # 基本字符串字段
    title = Field(description="标题")
    
    # 带类型的字段
    price = Field(field_type=float, description="价格")
    
    # 带默认值的字段
    status = Field(default="active", description="状态")
    
    # 不允许为空的字段
    required_field = Field(nullable=False, description="必填字段")
    
    # 带最大长度限制的字段
    description = Field(max_length=500, description="描述信息")
```

## 使用 Item

### 创建 Item 实例

```python
# 使用关键字参数创建 Item
item = ProductItem(
    name="智能手机",
    price=2999.99,
    in_stock=True
)

# 访问字段值
print(item['name'])  # 智能手机
print(item['price'])  # 2999.99
```

### 修改 Item 字段

```python
# 修改字段值
item['name'] = "高端智能手机"
item['price'] = 3999.99

# 注意：不能通过属性访问字段
# item.name = "错误方式"  # 这会抛出异常
```

### 验证机制

Item 会在设置字段值时自动进行验证：

```python
class UserItem(Item):
    age = Field(field_type=int, nullable=False, description="年龄")
    email = Field(max_length=100, description="邮箱")

# 正确的使用方式
user = UserItem()
user['age'] = 25
user['email'] = "user@example.com"

# 类型错误会抛出异常
# user['age'] = "not_a_number"  # TypeError

# 超过最大长度会抛出异常
# user['email'] = "a" * 150  # ValueError

# 必填字段为空会抛出异常
# user2 = UserItem()
# user2['age'] = None  # ValueError
```

## Item 方法

### to_dict()

将 Item 转换为字典：

```python
item = ProductItem(name="产品", price=100.0)
data = item.to_dict()
print(data)  # {'name': '产品', 'price': 100.0, 'in_stock': True}
```

### copy()

创建 Item 的深拷贝：

```python
original = ProductItem(name="产品", price=100.0)
copied = original.copy()
```

## 最佳实践

1. **明确字段类型**：为每个字段指定明确的类型，便于数据验证和处理
2. **合理设置默认值**：为可选字段设置合理的默认值
3. **添加描述信息**：为字段添加描述信息，便于文档生成和团队协作
4. **使用验证机制**：充分利用 Field 的验证功能确保数据质量
5. **避免动态字段**：在 Item 类中明确定义所有需要的字段，避免运行时动态添加