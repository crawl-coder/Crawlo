# -*- coding: UTF-8 -*-
import asyncio
from typing import Union, AsyncGenerator, Generator
from inspect import isgenerator, isasyncgen
from crawlo import Response, Request, Item
from crawlo.exceptions import TransformTypeError

T = Union[Request, Item]


async def transform(
        func: Union[Generator[T, None, None], AsyncGenerator[T, None]],
        response: Response
) -> AsyncGenerator[Union[T, Exception], None]:
    """
    转换回调函数的输出为统一异步生成器

    Args:
        func: 同步或异步生成器函数
        response: 当前响应对象

    Yields:
        Union[T, Exception]: 生成请求/Item或异常对象

    Raises:
        TransformTypeError: 当输入类型不符合要求时
    """

    # 类型检查前置
    if not (isgenerator(func) or isasyncgen(func)):
        raise TransformTypeError(
            f'Callback must return generator or async generator, got {type(func).__name__}'
        )

    try:
        if isgenerator(func):
            # 同步生成器处理
            for item in func:
                yield item
        else:
            # 异步生成器处理
            async for item in func:
                yield item

    except Exception as e:
        # Python 3.8 中 CancelledError 是 Exception 子类
        # 通过 athrow() 传入后必须重新抛出，否则违反异步生成器协议：
        #   RuntimeError: generator didn't stop after athrow()
        if isinstance(e, asyncio.CancelledError):
            raise
        yield e