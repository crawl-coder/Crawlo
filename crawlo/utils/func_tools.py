#!/usr/bin/python
# -*- coding:UTF-8 -*-
from typing import Callable
from inspect import isgenerator, isasyncgen
from crawlo.exceptions import TransformTypeError


async def transform(func: Callable):
    if isgenerator(func):
        for f in func:
            yield f
    elif isasyncgen(func):
        async for f in func:
            yield f
    else:
        raise TransformTypeError(
            f'callback return type error: {type(func)} must be `generator` or `async generator`'
        )

