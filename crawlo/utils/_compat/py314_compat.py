"""
Python 3.14 版本兼容工具集
============================
提供版本守卫的兼容层访问 Python 3.14+ 新特性。

当前仅 ``get_task_info`` 被 ``crawlo.core.scheduling.task_manager`` 使用；
其余符号保留为公共 API 供未来接入。
"""

import asyncio

# ============================================================
# 3.14 子解释器支持（PEP 734）
# ============================================================
try:
    from concurrent.interpreters import InterpreterPoolExecutor
    HAS_SUBINTERPRETERS = True
except ImportError:
    from concurrent.futures import ProcessPoolExecutor as _FallbackExecutor
    HAS_SUBINTERPRETERS = False
    InterpreterPoolExecutor = _FallbackExecutor


def get_executor(max_workers: int = None):
    """获取最佳可用的并行执行器（3.14+ 返回子解释器池，低版本回退到进程池）。"""
    return InterpreterPoolExecutor(max_workers=max_workers)


# ============================================================
# 3.14 模板字符串支持（PEP 750）
# ============================================================
def render_template(template_str: str, **kwargs) -> str:
    """渲染模板字符串，使用 ``str.format`` 替换 ``{name}`` 占位符。

    待 PEP 750 t-string 在正式 CPython 发布后可切换到原生实现。
    """
    return template_str.format(**kwargs)


# ============================================================
# asyncio.Task 内省工具
# ============================================================
def get_task_info(task: asyncio.Task) -> dict:
    """获取 asyncio.Task 的详细内省信息（name / done / cancelled / stack / coroutine）。"""
    info = {
        'name': task.get_name() if hasattr(task, 'get_name') else str(task),
        'done': task.done(),
        'cancelled': task.cancelled(),
    }

    try:
        info['stack'] = task.get_stack(limit=5)
    except Exception as e:
        info['stack'] = []
    try:
        coro = task.get_coro()
        if coro:
            info['coroutine'] = str(coro)
            info['cr_frame'] = str(getattr(coro, 'cr_frame', None))
    except Exception as e:
        pass

    return info


__all__ = [
    'HAS_SUBINTERPRETERS',
    'InterpreterPoolExecutor',
    'get_executor',
    'render_template',
    'get_task_info',
]
