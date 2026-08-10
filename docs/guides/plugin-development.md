# 插件开发指南（P1-B1/B2）

Crawlo 提供三类官方插件扩展点：**中间件 / 管道 / 扩展**。
第三方插件无需修改框架源码，注册后即可通过配置短名称启用。

## 1. 注册 API

```python
from crawlo.middleware import register_middleware, unregister_middleware
from crawlo.pipelines   import register_pipeline,   unregister_pipeline
from crawlo.extensions  import register_extension,  unregister_extension
```

统一签名：`register_xxx(name: str, cls: type) -> None`。
名称必须是非空字符串，类必须是类对象；重复注册同名的行为是**覆盖**（后者胜出）。

已存在的注册 API（下载器 / 队列后端）保持不变：

```python
from crawlo.downloader import register_downloader, unregister_downloader
from crawlo.queue import register_queue_backend, unregister_queue_backend
```

## 2. 双通道配置

注册后，配置里可直接写短名称：

```python
MIDDLEWARES = {"my_mw": 100}       # 短名称（需要先 register_middleware）
PIPELINES   = {"my_pipe": 300}
EXTENSIONS  = ["my_ext"]
```

也可以不注册，直接写完整字符串路径（与内置组件一致）：

```python
MIDDLEWARES = {"my_pkg.middleware.MyMiddleware": 100}
PIPELINES   = {"my_pkg.pipeline.MyPipeline": 300}
EXTENSIONS  = ["my_pkg.extension.MyExtension"]
```

若短名称跨类型重名，可用类型前缀显式指定：

```python
MIDDLEWARES = {"middleware:my_name": 100}
PIPELINES   = {"pipeline:my_name": 300}
EXTENSIONS  = ["extension:my_name"]
```

**解析优先级**（`crawlo.utils.misc.load_object`）：

1. 完整路径 import（含 `module:attr` 格式）；
2. 类型前缀（`middleware:name` / `pipeline:name` / `extension:name`）；
3. 注册表短名称。

## 3. 插件最小契约

| 组件 | 必须实现 | 可选 |
|---|---|---|
| 中间件 | `create_instance(crawler)` | `process_request` / `process_response` / `process_exception` |
| 管道 | `from_crawler(crawler)` | `process_item(item, spider)` / `open_spider` / `close_spider` |
| 扩展 | `create_instance(crawler)` | `spider_opened` / `spider_closed` / `item_successful` / `item_discard` / `response_received` / `request_scheduled` |

扩展的事件钩子由 `ExtensionManager` 自动订阅到 `CrawlerEvent`。

## 4. 完整示例

可运行的最小示例见 [examples/plugin_hello_world/](../../examples/plugin_hello_world/README.md)：

```bash
PYTHONPATH=examples python -m crawlo.cli run <你的爬虫>
```

示例同时演示短名称注册与字符串路径两种方式，并有一致性守护测试
（`tests/arch/test_plugin_example.py`）保证示例永不与框架脱节。

## 5. 调试与运维

- 注册成功会打印 INFO 日志：`Registered middleware: my_mw -> pkg.mod.Cls`；
- 查看当前全部注册项：`crawlo.plugin.get_registered_names()`；
- 注销：`unregister_*` 返回布尔值表示是否曾存在；
- 注册表是进程内全局（`crawlo.plugin` 模块），多爬虫共享。
