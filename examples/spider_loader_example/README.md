# Spider Loader 示例

这个示例演示了如何使用SPIDER_MODULES配置来自动发现和加载爬虫。

## 特性

1. **自动发现爬虫**: 通过SPIDER_MODULES配置自动发现和加载爬虫模块
2. **错误处理**: 支持SPIDER_LOADER_WARN_ONLY配置来控制加载错误的处理方式
3. **模块化设计**: 支持多个爬虫模块目录

## 配置

在[settings.py](file://d:\dowell\projects\Crawlo\examples\spider_loader_example\settings.py)中配置SPIDER_MODULES：

```python
SPIDER_MODULES = [
    'spider_loader_example.spiders',
    # 可以添加多个爬虫模块目录
    # 'spider_loader_example.more_spiders',
]

# 是否在爬虫加载出错时只警告而不报错
SPIDER_LOADER_WARN_ONLY = True
```

## 运行示例

```bash
python run.py
```

## 文件结构

```
spider_loader_example/
├── settings.py          # 配置文件
├── run.py              # 运行脚本
└── spiders/            # 爬虫目录
    └── example_spider.py  # 示例爬虫
```

## 核心组件

1. **SpiderLoader**: 爬虫加载器，负责发现和加载爬虫
2. **CrawlerProcess**: 爬虫进程管理器，支持从settings中读取SPIDER_MODULES配置
3. **interfaces.py**: 定义了ISpiderLoader接口规范
4. **utils/misc.py**: 提供了walk_modules等工具函数

## 改进点

相比于原始实现，这个版本具有以下改进：

1. **接口规范**: 定义了ISpiderLoader接口来规范爬虫加载器的行为
2. **设置驱动**: 通过settings配置SPIDER_MODULES和SPIDER_LOADER_WARN_ONLY
3. **错误处理**: 提供了warn_only选项来处理导入错误
4. **重复名称检查**: 检查并警告重复的spider名称
5. **模块遍历**: 使用walk_modules类似的机制来支持子模块
6. **请求匹配功能**: 添加了find_by_request方法来根据请求找到合适的spider