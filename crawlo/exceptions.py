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


class PipelineInitError(Exception):
    pass


class InvalidOutputError(Exception):
    pass


class RequestMethodError(Exception):
    pass


class IgnoreRequestError(Exception):
    def __init__(self, msg):
        self.msg = msg
        super(IgnoreRequestError, self).__init__(msg)


class ItemDiscard(Exception):
    def __init__(self, msg):
        self.msg = msg
        super(ItemDiscard, self).__init__(msg)


class NotConfigured(Exception):
    pass


class NotConfiguredError(Exception):
    pass


class ExtensionInitError(Exception):
    pass


class ReceiverTypeError(Exception):
    pass


class SpiderCreationError(Exception):
    """爬虫实例化失败异常"""
    pass


class ItemValidationError(Exception):
    """Item 字段验证错误"""
    pass
