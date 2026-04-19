# CHANGELOG

所有重要的 Crawlo 框架变更都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
项目版本遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [Unreleased]

## [0.2.0] - 2026-04-19

### 新增功能

#### MySQL 数据存在性检查工具
- 新增 `crawlo/tools/mysql_exists_checker.py` - MySQL 数据存在性检查工具
- 用途：在爬虫列表页采集时，提前判断数据是否已存在于数据库中
- 特点：
  - 简单易用：只需传入 SQL 语句即可判断存在性
  - 自动配置：自动从 settings 获取数据库连接信息
  - 资源安全：自动管理连接池生命周期
  - 协程集成：与框架异步协程无缝配合
- API：
  - `MySQLExistsChecker` - 主要类，支持上下文管理器
  - `check_exists()` - 便捷函数
  - `exists(sql, params)` - 检查单条数据
  - `batch_exists(sql, params_list)` - 批量检查
  - `count(sql, params)` - 统计记录数

使用示例：
```python
from crawlo.tools import MySQLExistsChecker

class MySpider(Spider):
    async def parse_list(self, response):
        for item in response.json():
            # 检查数据是否已存在
            sql = "SELECT 1 FROM articles WHERE url = %s LIMIT 1"
            checker = MySQLExistsChecker(self.settings)
            exists = await checker.exists(sql, (item['url'],))
            
            if not exists:
                yield Request(item['detail_url'], callback=self.parse_detail)
```

### 设计缺陷修复

#### 错误处理体系
- 创建 `crawlo/error_types.py` - 集中错误类型分类配置
- 新增 `ErrorClassifier` 类，支持 5 类错误分类
- 统一异常体系到 `crawlo/exceptions.py`
- 30+ 异常类型完整继承体系

#### 并发监控
- TaskManager 并发统计集成到 StatsCollector
- 新增监控指标：
  - `concurrency_limit` - 并发限制
  - `max_concurrent_seen` - 峰值并发数
  - `concurrency_utilization` - 并发利用率 (%)
  - `avg_response_time_ms` - 平均响应时间 (ms)

#### 中间件生命周期管理
- MiddlewareManager 新增 `async open()` 方法
- MiddlewareManager 新增 `async close()` 方法
- 支持同步和异步生命周期钩子
- 反向关闭顺序（与初始化相反）
- 幂等性保证（重复 open 安全）

#### 性能优化
- 请求生成算法优化：
  - 队列有空间时使用 `asyncio.gather` 并发入队
  - 队列空间不足时动态调整生成间隔
  - 添加超时保护（最多等待 1 秒）

### 文档
- 新增 `docs/design-defects-fix.md` - 设计缺陷修复完整记录
- 新增 `docs/core-api-reference.md` - 核心组件 API 参考
- 中间件开发指南和示例

### 测试

**新增测试文件**
- `tests/test_error_handling.py` - 错误处理测试 (21个测试)
- `tests/test_middleware_lifecycle.py` - 中间件生命周期测试 (9个测试)
- `tests/test_concurrency_control.py` - 并发控制测试 (11个测试)
- `tests/test_mysql_exists_checker.py` - MySQL 检查器测试 (14个测试)
- `tests/comprehensive_test_suite.py` - 自动化测试套件
- `tests/TEST_REPORT.md` - 完整测试报告

**测试结果**
- 核心测试：58 passed
- 端到端测试：通过
- 综合评分：96/100

---

## [0.1.0] - 2026-01-15

### Initial Release

- 基础爬虫框架
- 异步请求处理
- 调度器和队列系统
- 中间件支持
- 数据管道
- 扩展系统
- 日志系统

---

**发布日期**: 2026-04-19  
**维护者**: Crawlo Team  
**反馈**: https://github.com/crawl-coder/Crawlo/issues
