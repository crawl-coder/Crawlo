#!/usr/bin/python
# -*- coding:UTF-8 -*-
import os
import sys
from importlib import import_module
from inspect import iscoroutinefunction
from typing import Callable

from crawlo.settings.setting_manager import SettingManager


def _get_closest(path='.'):
    path = os.path.abspath(path)
    return path


def _init_env():
    closest = _get_closest()
    if closest:
        sys.path.append(closest)
        # project_dir = os.path.dirname(closest)
        # sys.path.append(project_dir)


def get_settings(settings='settings'):
    _settings = SettingManager()
    _init_env()
    _settings.set_settings(settings)
    return _settings


def merge_settings(spider, settings):
    if hasattr(spider, 'custom_settings'):
        custom_settings = getattr(spider, 'custom_settings')
        settings.update_attributes(custom_settings)


def load_class(_path):
    if not isinstance(_path, str):
        if callable(_path):
            return _path
        else:
            raise TypeError(f"args expect str or object, got {_path}")

    module_name, class_name = _path.rsplit('.', 1)
    module = import_module(module_name)

    try:
        cls = getattr(module, class_name)
    except AttributeError:
        raise NameError(f"Module {module_name!r} has no class named {class_name!r}")
    return cls


async def common_call(func: Callable, *args, **kwargs):
    if iscoroutinefunction(func):
        return await func(*args, **kwargs)
    else:
        return func(*args, **kwargs)
