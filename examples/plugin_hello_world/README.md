# Crawlo 插件示例：plugin_hello_world

展示 Crawlo 的插件机制（P1-B1）：一个第三方包无需修改框架源码，
即可注册自定义 **中间件 + 管道 + 扩展**，并通过配置短名称直接启用。

## 目录结构

```text
plugin_hello_world/
├── README.md
├── __init__.py         # 包入口（re-export register_plugins）
├── hello_plugin/
│   ├── __init__.py      # 注册 API：register_* 三个调用
│   ├── middleware.py    # 自定义中间件（日志 + 请求计数）
│   ├── pipeline.py      # 自定义管道（item 统计）
│   └── extension.py     # 自定义扩展（spider 生命周期钩子）
└── settings.py          # 用短名称启用插件的配置
```

## 两种启用方式

### 方式一：注册表 API（推荐，插件包自注册）

```python
# 你的代码（或插件包的 __init__.py 被 import 时）
from plugin_hello_world.hello_plugin import register_plugins
register_plugins()

# 然后配置里直接用短名称：
# MIDDLEWARES = {"hello_mw": 100}
# PIPELINES   = {"hello_pipe": 300}
# EXTENSIONS  = ["hello_ext"]
```

### 方式二：字符串路径（无需注册，与内置组件一致）

```python
# MIDDLEWARES = {"plugin_hello_world.hello_plugin.middleware.HelloMiddleware": 100}
# PIPELINES   = {"plugin_hello_world.hello_plugin.pipeline.HelloPipeline": 300}
# EXTENSIONS  = ["plugin_hello_world.hello_plugin.extension.HelloExtension"]
```

## 运行方式

把本目录加入 PYTHONPATH 后，在项目配置中启用插件即可：

```bash
PYTHONPATH=examples \
python -m crawlo.cli run <你的爬虫>
```

注意：`examples/plugin_hello_world/` 目录本身是插件包，包名是
`plugin_hello_world`，所以 PYTHONPATH 指向 `examples/`（包的父目录）。

插件类只需满足框架的最小契约：

| 组件 | 必须实现 |
|---|---|
| 中间件 | `create_instance(crawler)` + `process_request/process_response/process_exception` |
| 管道 | `from_crawler(crawler)` + `process_item(item, spider)` |
| 扩展 | `create_instance(crawler)`（可选 `spider_opened/spider_closed/item_successful/...` 事件钩子） |

## 解析优先级

`load_object` 解析顺序：完整路径 import → 类型前缀（`middleware:hello_mw`）→ 注册表短名称。
同名冲突时完整路径优先。
