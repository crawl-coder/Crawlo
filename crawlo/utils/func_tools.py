# -*- coding: UTF-8 -*-
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

    def _set_meta(obj: T) -> T:
        """统一设置请求的depth元数据"""
        if isinstance(obj, Request):
            obj.meta.setdefault('depth', response.meta.get('depth', 0))
        return obj

    # 类型检查前置
    if not (isgenerator(func) or isasyncgen(func)):
        raise TransformTypeError(
            f'Callback must return generator or async generator, got {type(func).__name__}'
        )

    try:
        if isgenerator(func):
            # 同步生成器处理
            for item in func:
                yield _set_meta(item)
        else:
            # 异步生成器处理
            async for item in func:
                yield _set_meta(item)

    except Exception as e:
        yield e

# #!/usr/bin/python
# # -*- coding:UTF-8 -*-
# from typing import Callable, Union
# from inspect import isgenerator, isasyncgen
# from crawlo import Response, Request, Item
# from crawlo.exceptions import TransformTypeError
#
#
# T = Union[Request, Item]
#
#
# async def transform(func: Callable, response: Response):
#     def set_request(t: T) -> T:
#         if isinstance(t, Request):
#             t.meta['depth'] = response.meta['depth']
#         return t
#     try:
#         if isgenerator(func):
#             for f in func:
#                 yield set_request(f)
#         elif isasyncgen(func):
#             async for f in func:
#                 yield set_request(f)
#         else:
#             raise TransformTypeError(
#                 f'callback return type error: {type(func)} must be `generator` or `async generator`'
#             )
#     except Exception as exp:
#         yield exp

