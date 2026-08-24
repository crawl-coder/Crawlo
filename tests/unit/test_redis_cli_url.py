#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
CLI Redis URL 四级回退解析测试（v1.7.6 B5）

四级回退（CLI 工具专用，无 crawl 上下文）：
1. --redis-url 命令行参数（最高优先级）
2. CRAWLO_REDIS_URL 环境变量
3. REDIS_URL 环境变量
4. 默认值 redis://127.0.0.1:6379/0

run.py 走 settings 回退（有 crawl 上下文），此处只测纯 CLI 路径。
"""
import os

import pytest

from crawlo.utils.redis_cli import DEFAULT_REDIS_URL, resolve_redis_url


class TestResolveRedisUrl:

    def test_cli_flag_highest_priority(self, monkeypatch):
        """--redis-url 参数优先于所有环境变量"""
        monkeypatch.setenv("CRAWLO_REDIS_URL", "redis://env-crawl/0")
        monkeypatch.setenv("REDIS_URL", "redis://env-generic/0")
        url = resolve_redis_url(["cmd", "--redis-url", "redis://cli/0"])
        assert url == "redis://cli/0"

    def test_crawlo_env_over_generic(self, monkeypatch):
        """CRAWLO_REDIS_URL 优先于通用 REDIS_URL"""
        monkeypatch.setenv("CRAWLO_REDIS_URL", "redis://crawlo-env/1")
        monkeypatch.setenv("REDIS_URL", "redis://generic-env/2")
        assert resolve_redis_url() == "redis://crawlo-env/1"

    def test_generic_redis_url_fallback(self, monkeypatch):
        """无 CRAWLO 专用变量时走 REDIS_URL"""
        monkeypatch.delenv("CRAWLO_REDIS_URL", raising=False)
        monkeypatch.setenv("REDIS_URL", "redis://generic/3")
        assert resolve_redis_url() == "redis://generic/3"

    def test_default_value(self, monkeypatch):
        """全部未设置时走默认值"""
        monkeypatch.delenv("CRAWLO_REDIS_URL", raising=False)
        monkeypatch.delenv("REDIS_URL", raising=False)
        assert resolve_redis_url() == DEFAULT_REDIS_URL == "redis://127.0.0.1:6379/0"

    def test_settings_fallback_when_no_env(self, monkeypatch):
        """有 settings 上下文但无环境变量时走 settings REDIS_URL"""
        monkeypatch.delenv("CRAWLO_REDIS_URL", raising=False)
        monkeypatch.delenv("REDIS_URL", raising=False)
        settings = {"REDIS_URL": "redis://from-settings/0"}
        assert resolve_redis_url(settings=settings) == "redis://from-settings/0"

    def test_env_over_settings(self, monkeypatch):
        """环境变量优先于 settings（Docker/K8s 覆盖场景）"""
        monkeypatch.setenv("CRAWLO_REDIS_URL", "redis://env/0")
        settings = {"REDIS_URL": "redis://settings/0"}
        assert resolve_redis_url(settings=settings) == "redis://env/0"

    def test_cli_flag_over_settings(self, monkeypatch):
        """--redis-url 参数优先于 settings"""
        monkeypatch.delenv("CRAWLO_REDIS_URL", raising=False)
        monkeypatch.delenv("REDIS_URL", raising=False)
        settings = {"REDIS_URL": "redis://settings/0"}
        args = ["dead-letter", "list", "p", "s", "--redis-url", "redis://cli/9"]
        assert resolve_redis_url(args, settings=settings) == "redis://cli/9"

    def test_empty_args_list(self, monkeypatch):
        """空 args 走环境/默认"""
        monkeypatch.delenv("CRAWLO_REDIS_URL", raising=False)
        monkeypatch.delenv("REDIS_URL", raising=False)
        assert resolve_redis_url([]) == DEFAULT_REDIS_URL

    def test_partial_args_no_flag(self, monkeypatch):
        """有参数但无 --redis-url 标志"""
        monkeypatch.delenv("CRAWLO_REDIS_URL", raising=False)
        monkeypatch.setenv("REDIS_URL", "redis://env/5")
        assert resolve_redis_url(["dead-letter", "list", "p", "s"]) == "redis://env/5"
