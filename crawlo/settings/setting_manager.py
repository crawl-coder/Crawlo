#!/usr/bin/python
# -*- coding: UTF-8 -*-
import json
from copy import deepcopy
from importlib import import_module
from collections.abc import MutableMapping

from crawlo.settings import default_settings


class SettingManager(MutableMapping):

    def __init__(self, values=None):
        self.attributes = {}
        self.set_settings(default_settings)
        # 在初始化时合并配置
        self._merge_config(values)
        # 处理动态配置
        self._process_dynamic_config()

    def _merge_config(self, user_config):
        """合并默认配置和用户配置"""
        if not user_config:
            return

        # 合并中间件配置
        if 'MIDDLEWARES' in user_config:
            user_middlewares = user_config['MIDDLEWARES']
            
            # 检查用户配置是字典格式还是列表格式
            if isinstance(user_middlewares, dict):
                # 字典格式：{'middleware_path': priority}
                # 获取默认中间件（也可能是字典格式）
                default_middlewares = self.attributes.get('MIDDLEWARES', {})
                if isinstance(default_middlewares, dict):
                    # 合并字典格式的中间件配置
                    # 用户配置优先级更高，会覆盖默认配置
                    merged_middlewares = default_middlewares.copy()
                    merged_middlewares.update(user_middlewares)
                else:
                    # 默认是列表格式，转换为字典格式
                    merged_middlewares = {}
                    # 将默认列表转换为字典（优先级为0）
                    if isinstance(default_middlewares, (list, tuple)):
                        for middleware in default_middlewares:
                            if middleware and not str(middleware).strip().startswith('#'):
                                # 如果middleware是元组格式 (path, priority)，则使用其优先级
                                if isinstance(middleware, tuple) and len(middleware) == 2:
                                    merged_middlewares[middleware[0]] = middleware[1]
                                else:
                                    merged_middlewares[middleware] = 0
                    # 添加用户配置的中间件
                    merged_middlewares.update(user_middlewares)
                self.attributes['MIDDLEWARES'] = merged_middlewares
            else:
                # 列表格式：['middleware_path'] 或 [('middleware_path', priority)]
                default_middlewares = self.attributes.get('MIDDLEWARES', [])
                # 如果用户配置了非空列表，则合并
                if user_middlewares:
                    # 过滤掉空值和注释
                    user_middlewares = [middleware for middleware in user_middlewares if middleware and not middleware.strip().startswith('#')]
                    # 合并默认中间件和用户中间件，去重但保持顺序
                    merged_middlewares = default_middlewares[:]
                    for middleware in user_middlewares:
                        # 检查是否已存在，如果是元组格式也要正确处理
                        middleware_path = middleware[0] if isinstance(middleware, tuple) and len(middleware) == 2 else middleware
                        existing_index = None
                        for i, existing in enumerate(merged_middlewares):
                            existing_path = existing[0] if isinstance(existing, tuple) and len(existing) == 2 else existing
                            if existing_path == middleware_path:
                                existing_index = i
                                break
                        if existing_index is not None:
                            # 如果已存在，则替换
                            merged_middlewares[existing_index] = middleware
                        else:
                            merged_middlewares.append(middleware)
                    self.attributes['MIDDLEWARES'] = merged_middlewares

        # 合并管道配置
        if 'PIPELINES' in user_config:
            default_pipelines = self.attributes.get('PIPELINES', [])
            user_pipelines = user_config['PIPELINES']
            # 如果用户配置了空列表，则仍然使用默认配置
            if user_pipelines:
                # 过滤掉空值和注释
                user_pipelines = [pipeline for pipeline in user_pipelines if pipeline and not pipeline.strip().startswith('#')]
                # 合并默认管道和用户管道，去重但保持顺序
                merged_pipelines = default_pipelines[:]
                for pipeline in user_pipelines:
                    if pipeline not in merged_pipelines:
                        merged_pipelines.append(pipeline)
                self.attributes['PIPELINES'] = merged_pipelines



        # 合并扩展配置
        if 'EXTENSIONS' in user_config:
            default_extensions = self.attributes.get('EXTENSIONS', [])
            user_extensions = user_config['EXTENSIONS']
            # 如果用户配置了空列表，则仍然使用默认配置
            if user_extensions:
                # 过滤掉空值和注释
                user_extensions = [extension for extension in user_extensions if extension and not extension.strip().startswith('#')]
                # 合并默认扩展和用户扩展，去重但保持顺序
                merged_extensions = default_extensions[:]
                for extension in user_extensions:
                    if extension not in merged_extensions:
                        merged_extensions.append(extension)
                self.attributes['EXTENSIONS'] = merged_extensions

        # 更新其他用户配置
        for key, value in user_config.items():
            if key not in ['MIDDLEWARES', 'PIPELINES', 'EXTENSIONS']:
                self.attributes[key] = value
        
        # 特殊处理PIPELINES，确保去重管道在最前面（在所有配置更新后执行）
        dedup_pipeline = self.attributes.get('DEFAULT_DEDUP_PIPELINE')
        if dedup_pipeline:
            pipelines = self.attributes.get('PIPELINES', [])
            # 移除所有去重管道实例（如果存在）
            # 移除内存和Redis去重管道
            pipelines = [item for item in pipelines 
                       if item not in ('crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline', 
                                     'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline')]
            # 在开头插入去重管道
            pipelines.insert(0, dedup_pipeline)
            self.attributes['PIPELINES'] = pipelines

    def set_settings(self, module):
        if isinstance(module, str):
            module = import_module(module)
        
        # 收集模块中的所有配置项
        module_settings = {}
        for key in dir(module):
            if key.isupper():
                value = getattr(module, key)
                module_settings[key] = value
        
        # 使用合并逻辑而不是直接设置
        self._merge_config(module_settings)
        
        # 处理动态配置项（如LOG_FILE）
        self._process_dynamic_config()
        
    def _process_dynamic_config(self):
        """
        处理动态配置项
        某些配置项需要根据其他配置项的值进行动态计算
        """
        # 处理LOG_FILE配置
        if self.attributes.get('LOG_FILE') is None:
            project_name = self.attributes.get('PROJECT_NAME', 'crawlo')
            self.attributes['LOG_FILE'] = f'logs/{project_name}.log'

    def get(self, key, default=None):
        """安全获取值，不触发递归"""
        value = self.attributes.get(key, default)
        return value if value is not None else default

    def _get_merged_list(self, key, default=None):
        """这个方法已不再需要，因为配置合并已在配置加载时完成"""
        return self.attributes.get(key, default or [])

    def get_int(self, key, default=0):
        return int(self.get(key, default=default))

    def get_float(self, key, default=0.0):
        return float(self.get(key, default=default))

    def get_bool(self, key, default=False):
        got = self.get(key, default=default)
        if isinstance(got, bool):
            return got
        if isinstance(got, (int, float)):
            return bool(got)
        got_lower = str(got).strip().lower()
        if got_lower in ('1', 'true'):
            return True
        if got_lower in ('0', 'false'):
            return False
        raise ValueError(
            f"Unsupported value for boolean setting: {got}. "
            "Supported values are: 0/1, True/False, '0'/'1', 'True'/'False' (case-insensitive)."
        )

    def get_list(self, key, default=None):
        values = self.get(key, default or [])
        if isinstance(values, str):
            return [v.strip() for v in values.split(',') if v.strip()]
        try:
            return list(values)
        except TypeError:
            return [values]

    def get_dict(self, key, default=None):
        value = self.get(key, default or {})
        if isinstance(value, str):
            value = json.loads(value)
        try:
            return dict(value)
        except TypeError:
            return value

    def set(self, key, value):
        self.attributes[key] = value

    # 实现 MutableMapping 必须的方法
    def __getitem__(self, item):
        return self.attributes[item]

    def __setitem__(self, key, value):
        self.set(key, value)

    def __delitem__(self, key):
        del self.attributes[key]

    def __iter__(self):
        return iter(self.attributes)

    def __len__(self):
        return len(self.attributes)

    def __str__(self):
        return f'<Settings: {self.attributes}>'

    __repr__ = __str__

    def update_attributes(self, attributes):
        if attributes is not None:
            for key, value in attributes.items():
                self.set(key, value)

    def copy(self):
        return deepcopy(self)

    def __deepcopy__(self, memo):
        """
        自定义深度复制方法，避免复制logger等不可pickle的对象
        """
        # 创建一个新的实例
        cls = self.__class__
        new_instance = cls.__new__(cls)

        # 复制attributes字典，但排除不可pickle的对象
        new_attributes = {}
        for key, value in self.attributes.items():
            try:
                # 尝试深度复制值
                new_attributes[key] = deepcopy(value, memo)
            except Exception:
                # 如果复制失败，保留原始引用（对于logger等对象）
                new_attributes[key] = value

        # 设置新实例的attributes
        new_instance.attributes = new_attributes

        return new_instance