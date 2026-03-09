# -*- coding: utf-8 -*-
import json
import re
from typing import Any, Union, List, Dict, Tuple, Optional

from crawlo.logging import get_logger

logger = get_logger(__name__)

# 正则表达式缓存
_REGEXPS: Dict[str, "re.Pattern"] = {}


def extract_text_by_regex(
    text: Union[str, Any],
    patterns: Union[str, List[str]],
    allow_repeat: bool = True,
    fetch_one: bool = False,
    join_with: Optional[str] = None,
) -> Union[str, List[str], Tuple]:
    """
    从文本中提取信息，支持正则匹配和多模式 fallback。

    Args:
        text (str): 文本内容或可转为字符串的类型
        patterns (str or list of str): 正则表达式模式，按顺序尝试匹配
        allow_repeat (bool): 是否允许重复结果
        fetch_one (bool): 是否只提取第一个匹配项（返回元组）
        join_with (str, optional): 若提供，则将结果用该字符连接成字符串

    Returns:
        str | list | tuple: 匹配结果，根据参数返回字符串、列表或元组
    """
    if isinstance(patterns, str):
        patterns = [patterns]

    results = []
    for pattern in patterns:
        if not pattern:
            continue

        if pattern not in _REGEXPS:
            _REGEXPS[pattern] = re.compile(pattern, re.S)

        if fetch_one:
            match = _REGEXPS[pattern].search(str(text))
            results = match.groups() if match else ("",)
            break
        else:
            found = _REGEXPS[pattern].findall(str(text))
            if found:
                results = found
                break

    if fetch_one:
        return results[0] if len(results) == 1 else results

    if not allow_repeat:
        results = sorted(set(results), key=results.index)

    return join_with.join(results) if join_with else results


def parse_json_safely(json_str: Union[str, Any]) -> Dict:
    """
    安全解析 JSON 字符串，兼容非标准格式（如单引号、缺少引号键）。

    Args:
        json_str (str): JSON 字符串

    Returns:
        dict: 解析后的字典，失败返回空字典
    """
    if not json_str:
        return {}

    try:
        return json.loads(json_str)
    except Exception as e1:
        try:
            cleaned = json_str.strip().replace("'", '"')
            # 使用新的函数名
            keys = extract_text_by_regex(cleaned, r'(\w+):')
            for key in keys:
                cleaned = cleaned.replace(f"{key}:", f'"{key}":')
            return json.loads(cleaned) if cleaned else {}
        except Exception as e2:
            logger.error(
                f"JSON 解析失败\n"
                f"原始内容: {json_str}\n"
                f"错误1: {e1}\n"
                f"修复后: {cleaned}\n"
                f"错误2: {e2}"
            )
        return {}