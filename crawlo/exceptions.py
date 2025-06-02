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


class NotConfiguredError(Exception):
    pass


class ExtensionInitError(Exception):
    pass


class ReceiverTypeError(Exception):
    pass
