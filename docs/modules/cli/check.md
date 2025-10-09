# check 命令

`check` 命令用于检查项目配置和爬虫实现，帮助发现潜在问题和错误。

## 命令语法

```bash
crawlo check [spider_name] [options]
```

### 参数说明

- `spider_name` - 要检查的爬虫名称（可选，不指定则检查整个项目）
- `options` - 可选参数

## 使用示例

### 基本使用

```bash
# 检查整个项目
crawlo check

# 检查特定爬虫
crawlo check myspider

# 指定项目目录
crawlo check --project-dir /path/to/project
```

### 详细检查

```bash
# 显示详细信息
crawlo check --verbose

# 只显示错误
crawlo check --errors-only

# 生成检查报告
crawlo check --output report.txt
```

## 检查内容

### 1. 配置检查

```bash
# 检查配置文件
crawlo check --check-config

# 检查环境变量
crawlo check --check-env
```

检查的配置项包括：
- 项目名称和版本
- 并发配置
- 下载器配置
- 队列和过滤器配置
- 日志配置
- 管道和中间件配置

### 2. 爬虫检查

```bash
# 检查爬虫实现
crawlo check --check-spiders

# 检查特定爬虫
crawlo check myspider --check-spider
```

检查的爬虫项包括：
- 爬虫名称唯一性
- 继承关系正确性
- 解析方法实现
- 请求和数据项处理

### 3. 依赖检查

```bash
# 检查依赖项
crawlo check --check-deps

# 检查版本兼容性
crawlo check --check-versions
```

## 配置选项

`check` 命令支持以下选项：

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| --project-dir | string | 当前目录 | 项目目录路径 |
| --config | string | 'settings.py' | 配置文件路径 |
| --verbose | flag | - | 显示详细信息 |
| --quiet | flag | - | 静默模式，只显示错误 |
| --errors-only | flag | - | 只显示错误信息 |
| --warnings-only | flag | - | 只显示警告信息 |
| --check-config | flag | True | 检查配置文件 |
| --check-spiders | flag | True | 检查爬虫实现 |
| --check-deps | flag | False | 检查依赖项 |
| --check-env | flag | False | 检查环境变量 |
| --output | string | None | 输出报告文件路径 |
| --format | string | 'text' | 输出格式 (text, json, xml) |

## 检查报告

### 文本格式（默认）

```bash
$ crawlo check
检查项目: myproject
配置检查: 通过
爬虫检查: 
  - news_spider: 通过
  - product_spider: 警告 - 缺少描述文档
依赖检查: 通过

总计: 3 项检查, 0 个错误, 1 个警告
```

### JSON 格式

```bash
$ crawlo check --format json
{
  "project": "myproject",
  "timestamp": "2023-01-01T12:00:00Z",
  "checks": [
    {
      "type": "config",
      "status": "passed",
      "details": []
    },
    {
      "type": "spider",
      "name": "news_spider",
      "status": "passed",
      "details": []
    },
    {
      "type": "spider",
      "name": "product_spider",
      "status": "warning",
      "details": ["缺少描述文档"]
    }
  ],
  "summary": {
    "total": 3,
    "errors": 0,
    "warnings": 1
  }
}
```

## 常见检查项

### 配置检查项

```python
# 检查配置项类型
CONCURRENCY = 16        # ✅ 正确
CONCURRENCY = "16"      # ❌ 错误，应该是整数

# 检查必需配置项
PROJECT_NAME = "myproject"  # ✅ 必需
# PROJECT_NAME 缺失      # ❌ 错误，缺少必需项

# 检查配置值范围
DOWNLOAD_DELAY = 0.5    # ✅ 正确范围
DOWNLOAD_DELAY = -1     # ❌ 错误，不能为负数
```

### 爬虫检查项

```python
# 检查爬虫名称
class MySpider(Spider):
    name = "my_spider"  # ✅ 正确
    
class AnotherSpider(Spider):
    # name 缺失          # ❌ 错误，缺少名称

# 检查方法实现
class MySpider(Spider):
    def parse(self, response):
        pass  # ✅ 正确实现
        
class BadSpider(Spider):
    # 缺少 parse 方法   # ❌ 错误，缺少必需方法
```

### 依赖检查项

```bash
# 检查必需依赖
requests>=2.25.0    # ✅ 版本满足要求
requests>=3.0.0     # ❌ 版本不满足要求

# 检查可选依赖
selenium>=4.0.0     # ✅ 可选依赖，如果使用则需要
# selenium 缺失      # ⚠️ 警告，如果配置中使用了则需要
```

## 最佳实践

### 1. 开发阶段检查

```bash
# 开发过程中定期检查
crawlo check --verbose

# 提交前检查
crawlo check --errors-only
```

### 2. CI/CD 集成

```bash
# 在 CI/CD 流程中使用
# .github/workflows/ci.yml
- name: Check Project
  run: |
    pip install -r requirements.txt
    crawlo check --errors-only
```

### 3. 配置验证

```bash
# 部署前验证配置
crawlo check --check-config --check-env

# 生产环境配置检查
crawlo check --config production_settings.py
```

## 自定义检查规则

### 添加自定义检查器

```python
# custom_checker.py
from crawlo.check import BaseChecker

class CustomChecker(BaseChecker):
    def check(self, project):
        """自定义检查逻辑"""
        issues = []
        
        # 检查自定义规则
        if not project.settings.get('CUSTOM_SETTING'):
            issues.append({
                'type': 'error',
                'message': '缺少自定义配置项'
            })
        
        return issues
```

### 注册自定义检查器

```python
# settings.py
CUSTOM_CHECKERS = [
    'myproject.checkers.CustomChecker'
]
```

## 故障排除

### 常见问题

1. **配置文件错误**
   ```bash
   # 错误: Configuration file not found
   # 解决: 检查配置文件路径
   crawlo check --config settings.py
   
   # 错误: Invalid configuration syntax
   # 解决: 检查配置文件语法
   python -m py_compile settings.py
   ```

2. **爬虫实现错误**
   ```bash
   # 错误: Spider class not found
   # 解决: 检查爬虫类定义和继承
   grep -r "class.*Spider" spiders/
   
   # 错误: Missing required method
   # 解决: 实现必需的方法
   ```

3. **依赖问题**
   ```bash
   # 错误: Missing dependency
   # 解决: 安装缺失的依赖
   pip install -r requirements.txt
   
   # 错误: Version conflict
   # 解决: 更新或降级依赖版本
   pip install package==required_version
   ```

### 调试技巧

```bash
# 显示详细检查过程
crawlo check --verbose

# 只关注特定类型的检查
crawlo check --check-config --verbose

# 生成详细的检查报告
crawlo check --output detailed_report.json --format json --verbose
```