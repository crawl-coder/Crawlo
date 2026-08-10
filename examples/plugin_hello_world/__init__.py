"""plugin_hello_world：Crawlo 插件示例包。

用法（把 examples/plugin_hello_world 加入 PYTHONPATH 后）：

    from plugin_hello_world import register_plugins
    register_plugins()
"""

from plugin_hello_world.hello_plugin import (
    HelloExtension,
    HelloMiddleware,
    HelloPipeline,
    register_plugins,
)

__all__ = [
    "HelloExtension",
    "HelloMiddleware",
    "HelloPipeline",
    "register_plugins",
]
