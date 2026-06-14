"""
Python 3.14 版本兼容工具集
============================
提供版本守卫的兼容层访问 Python 3.14+ 新特性。
"""

import sys
import asyncio

# ============================================================
# 3.14 子解释器支持（PEP 734）
# ============================================================
try:
    from concurrent.interpreters import InterpreterPoolExecutor
    HAS_SUBINTERPRETERS = True
    """当前环境是否支持 concurrent.interpreters (Python 3.14+)"""
except ImportError:
    from concurrent.futures import ProcessPoolExecutor as _FallbackExecutor
    HAS_SUBINTERPRETERS = False
    InterpreterPoolExecutor = _FallbackExecutor


def get_executor(max_workers: int = None):
    """
    获取最佳可用的并行执行器。

    在 Python 3.14+ 上返回 InterpreterPoolExecutor（子解释器，进程内隔离），
    在更低版本上返回 ProcessPoolExecutor（多进程）。

    Args:
        max_workers: 最大工作线程/进程数，None 为自动

    Returns:
        concurrent.futures.Executor 实例
    """
    return InterpreterPoolExecutor(max_workers=max_workers)


# ============================================================
# 3.14 模板字符串支持（PEP 750）
# ============================================================
if sys.version_info >= (3, 14):
    from string.templatelib import Template as _Py314Template
    from string.templatelib import Interpolation

    def render_template(template_str: str, **kwargs) -> str:
        """
        使用 Python 3.14+ t-string 机制处理模板。
        通过 compile/eval 模拟 t-string 行为。

        Args:
            template_str: 模板字符串，包含 {name} 占位符
            **kwargs: 模板变量

        Returns:
            渲染后的字符串
        """
        # 构建 t-string 表达式
        compiled = compile(
            f"t'''{template_str}'''",
            '<template>',
            'eval'
        )
        # 注入变量
        local_vars = kwargs
        result = eval(compiled, {}, local_vars)
        # 转换为字符串
        return ''.join(str(part) if not hasattr(part, 'value')
                       else str(part.value) for part in result)
else:
    def render_template(template_str: str, **kwargs) -> str:
        """
        回退方案：使用 str.format() 处理模板（Python < 3.14）。

        Args:
            template_str: 模板字符串，包含 {name} 占位符
            **kwargs: 模板变量

        Returns:
            渲染后的字符串
        """
        return template_str.format(**kwargs)


# ============================================================
# 3.14 asyncio 内省增强
# ============================================================
def get_task_info(task: asyncio.Task) -> dict:
    """
    获取 asyncio.Task 的详细内省信息。

    当前返回基础信息（name、done、cancelled），以及调用栈和协程信息。

    Args:
        task: asyncio.Task 实例

    Returns:
        包含任务详细信息的字典
    """
    info = {
        'name': task.get_name() if hasattr(task, 'get_name') else str(task),
        'done': task.done(),
        'cancelled': task.cancelled(),
    }

    # 增强内省：Task.get_stack() / Task.get_coro() 自 Python 3.7 起可用
    try:
        info['stack'] = task.get_stack(limit=5)
    except Exception:
        info['stack'] = []
    try:
        coro = task.get_coro()
        if coro:
            info['coroutine'] = str(coro)
            info['cr_frame'] = str(getattr(coro, 'cr_frame', None))
    except Exception:
        pass

    return info


# ============================================================
# 导入兼容性声明
# ============================================================
__all__ = [
    'HAS_SUBINTERPRETERS',
    'InterpreterPoolExecutor',
    'get_executor',
    'render_template',
    'get_task_info',
]
