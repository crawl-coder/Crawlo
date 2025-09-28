# Crawlo 高级工具示例项目

本项目展示了 Crawlo 框架中各种高级工具的使用方法，包括工厂模式、批处理工具、受控爬虫混入类、大规模配置工具和大规模爬虫辅助工具。

## 🚀 快速开始

```bash
# 克隆项目
cd advanced_tools_example

# 查看可用示例
python run.py help

# 运行特定示例
python run.py factory          # 工厂模式示例
python run.py batch            # 批处理工具示例
python run.py controlled       # 受控爬虫混入类示例
python run.py large_scale_config  # 大规模配置工具示例
python run.py large_scale_helper  # 大规模爬虫辅助工具示例
```

## 📁 项目结构

```
advanced_tools_example/
├── advanced_tools_example/     # 项目包
│   ├── spiders/               # 爬虫模块
│   │   ├── factory_example.py        # 工厂模式示例
│   │   ├── batch_example.py          # 批处理工具示例
│   │   ├── controlled_example.py     # 受控爬虫混入类示例
│   │   ├── large_scale_config_example.py  # 大规模配置工具示例
│   │   └── large_scale_helper_example.py  # 大规模爬虫辅助工具示例
│   ├── items.py               # 数据项定义
│   ├── middlewares.py         # 中间件
│   ├── pipelines.py           # 管道
│   └── settings.py            # 配置
├── run.py                     # 爬虫运行脚本
├── demo_tools.py             # 独立工具演示脚本
├── crawlo.cfg                 # Crawlo配置文件
├── logs/                      # 日志目录
└── output/                    # 输出目录
```

## 🛠️ 高级工具详解

### 1. 工厂模式相关模块

**文件**: `spiders/factory_example.py`

**功能**: 
- 组件创建和依赖注入
- 单例模式支持
- 统一的组件管理机制

**使用场景**:
- 需要统一管理组件创建过程
- 需要依赖注入功能
- 需要单例组件实例

**实际案例参考**:
参考 `examples/ofweek_standalone/ofweek_standalone/spiders/OfweekSpider.py` 中的数据处理逻辑，可以使用工厂模式来创建不同的数据处理器实例，实现组件的统一管理和依赖注入。

**运行示例**:
```bash
python run.py factory
```

### 2. 批处理工具

**文件**: `spiders/batch_example.py`

**功能**:
- 大规模数据处理
- 并发控制
- 内存使用优化

**使用场景**:
- 处理大量数据项
- 需要控制并发数量
- 内存敏感的数据处理任务

**实际案例参考**:
在 `OfweekSpider.py` 中，可以使用批处理工具来优化数据存储，将大量爬取到的数据批量保存到数据库，而不是逐个处理，从而提高效率并减少数据库连接开销。

**运行示例**:
```bash
python run.py batch
```

### 3. 受控爬虫混入类

**文件**: `spiders/controlled_example.py`

**功能**:
- 控制大规模请求生成
- 防止内存溢出
- 动态并发控制

**使用场景**:
- 需要生成大量请求的爬虫
- 内存受限的环境
- 需要精确控制并发的场景

**实际案例参考**:
在 `OfweekSpider.py` 中，原本需要生成1851页的请求URL，使用受控爬虫混入类可以防止一次性生成过多请求导致内存溢出，并根据系统负载动态调节请求生成速度。

**运行示例**:
```bash
python run.py controlled
```

### 4. 大规模配置工具

**文件**: `spiders/large_scale_config_example.py`

**功能**:
- 针对不同场景的优化配置
- 简化配置过程
- 提高爬取效率和稳定性

**配置类型**:
- **保守型**: 资源受限环境
- **平衡型**: 一般生产环境
- **激进型**: 高性能服务器
- **内存优化型**: 内存受限但要处理大量请求

**使用场景**:
- 处理数万+请求的大规模爬取
- 不同性能环境的适配
- 快速配置优化

**实际案例参考**:
在 `OfweekSpider.py` 中，可以根据不同的运行环境（开发环境、测试环境、生产环境）应用不同的配置，例如在开发环境中使用保守配置，在生产环境中使用激进配置。

**运行示例**:
```bash
python run.py large_scale_config
```

### 5. 大规模爬虫辅助工具

**文件**: `spiders/large_scale_helper_example.py`

**功能**:
- 批量数据处理
- 进度管理和断点续传
- 内存使用优化
- 多种数据源支持

**组件**:
- **LargeScaleHelper**: 批量迭代大量数据
- **ProgressManager**: 进度管理
- **MemoryOptimizer**: 内存优化
- **DataSourceAdapter**: 数据源适配器

**使用场景**:
- 处理数万+ URL的爬虫
- 需要断点续传的功能
- 内存敏感的大规模处理任务

**实际案例参考**:
在 `OfweekSpider.py` 中，可以使用大规模爬虫辅助工具来实现断点续传功能，当爬虫意外中断后可以从上次中断的位置继续爬取，避免重复工作。

**运行示例**:
```bash
python run.py large_scale_helper
```

## 🧪 独立工具演示

除了通过爬虫运行示例外，还可以使用独立的演示脚本：

```bash
# 演示所有工具
python demo_tools.py

# 演示特定工具
python demo_tools.py factory
python demo_tools.py batch
python demo_tools.py controlled
python demo_tools.py large_scale_config
python demo_tools.py large_scale_helper
```

## 📚 工具使用指南

每个示例文件都包含了详细的使用说明和最佳实践建议，可以直接查看源代码了解具体实现。

每个爬虫文件中都包含了与 `OfweekSpider.py` 的对比案例，说明了如何在实际项目中应用这些高级工具。

## 🤝 支持

如需更多帮助，请参考：
- [Crawlo 官方文档](https://crawlo.readthedocs.io/)
- [GitHub Issues](https://github.com/crawlo/crawlo/issues)