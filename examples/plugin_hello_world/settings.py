"""启用 plugin_hello_world 的配置片段（复制到你的 settings.py）。"""

# 方式一：短名称（需要先调用 register_plugins()）
MIDDLEWARES = {
    "hello_mw": 100,
}
PIPELINES = {
    "hello_pipe": 300,
}
EXTENSIONS = [
    "hello_ext",
]

# 方式二：完整字符串路径（无需注册，二选一）
# MIDDLEWARES = {"plugin_hello_world.hello_plugin.middleware.HelloMiddleware": 100}
# PIPELINES = {"plugin_hello_world.hello_plugin.pipeline.HelloPipeline": 300}
# EXTENSIONS = ["plugin_hello_world.hello_plugin.extension.HelloExtension"]
