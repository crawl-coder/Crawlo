#!/usr/bin/python
# -*- coding:UTF-8 -*-
class TransformTypeError(TypeError):
    pass


class OutputError(Exception):
    pass


class SpiderTypeError(TypeError):
    pass


class ItemInitError(Exception):
    pass


class ItemAttributeError(Exception):
    pass


class DecodeError(Exception):
    pass


class MiddlewareInitError(Exception):
    pass


class InvalidOutputError(Exception):
    pass


class RequestMethodError(Exception):
    pass


class PipelineInitError(Exception):
    pass


class IgnoreRequestError(Exception):
    pass


class ItemDiscard(Exception):
    pass
