# -*- coding: utf-8 -*-
"""
Created on 2025/6/3 10:04 PM
---------
@summary:
---------
@author: crawl-coder
@email: 2251018029@qq.com
"""

from os.path import dirname, join
from sys import version_info

import setuptools

if version_info < (3, 6, 0):
    raise SystemExit("Sorry! Crawlo requires python 3.6.0 or later.")

with open(join(dirname(__file__), "Crawlo/VERSION"), "rb") as fh:
    version = fh.read().decode("ascii").strip()

with open("README.md", "r", encoding="utf8") as fh:
    long_description = fh.read()

packages = setuptools.find_packages()
packages.extend(
    [
        "crawlo",
        "crawlo.templates",
        "crawlo.templates.project_template",
        "crawlo.templates.project_template.spiders",
        "crawlo.templates.project_template.items",
    ]
)

requires = [
    "aiohttp>=3.12.6",
    "httpx>=0.28.1"
    "DBUtils>=2.0",
    "parsel>=1.10.0",
    "PyMySQL>=0.9.3",
    "redis>=2.10.6,<4.0.0",
    "ujson>=5.10.0",
    "ipython>=7.14.0",
    "cryptography>=3.3.2",
    "urllib3>=1.25.8",
    "loguru>=0.5.3",
    "pyperclip>=1.8.2",
    "terminal-layout>=2.1.3",
]

render_requires = [
    "webdriver-manager>=4.0.0",
    "playwright",
    "selenium>=3.141.0",
]

all_requires = [
    "bitarray>=1.5.3",
    "PyExecJS>=1.5.1",
    "pymongo>=3.10.1",
    "redis-py-cluster>=2.1.0",
] + render_requires

setuptools.setup(
    name="crawlo",
    version=version,
    author="crawl-coder",
    license="MIT",
    author_email="crawlo@qq.com",
    python_requires=">=3.6",
    description="feapder是一款支持异步的python爬虫框架",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=requires,
    extras_require={"all": all_requires, "render": render_requires},
    entry_points={"console_scripts": ["crawlo = crawlo.commands.cmdline:execute"]},
    url="https://github.com/crawl-coder/Crawlo.git",
    packages=packages,
    include_package_data=True,
    classifiers=["Programming Language :: Python :: 3"],
)