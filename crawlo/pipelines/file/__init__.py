# -*- coding: utf-8 -*-
"""文件型输出管道子包"""

from .csv import CsvPipeline, CsvDictPipeline
from .json import JsonLinesPipeline, JsonArrayPipeline

__all__ = [
    'CsvPipeline',
    'CsvDictPipeline',
    'JsonLinesPipeline',
    'JsonArrayPipeline',
]
