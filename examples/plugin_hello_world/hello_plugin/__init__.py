"""plugin_hello_world 插件包：注册中间件 / 管道 / 扩展。"""

from plugin_hello_world.hello_plugin.middleware import HelloMiddleware
from plugin_hello_world.hello_plugin.pipeline import HelloPipeline
from plugin_hello_world.hello_plugin.extension import HelloExtension

from crawlo.middleware import register_middleware
from crawlo.pipelines import register_pipeline
from crawlo.extensions import register_extension


def register_plugins() -> None:
    """注册全部插件（幂等，可重复调用）。"""
    register_middleware("hello_mw", HelloMiddleware)
    register_pipeline("hello_pipe", HelloPipeline)
    register_extension("hello_ext", HelloExtension)


__all__ = [
    "HelloMiddleware",
    "HelloPipeline",
    "HelloExtension",
    "register_plugins",
]
