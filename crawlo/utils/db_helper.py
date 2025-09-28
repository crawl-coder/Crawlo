# -*- coding: utf-8 -*-
import json
import re
import pprint
from typing import Any, Union, List, Dict, Tuple, Optional
from datetime import date, time, datetime

from crawlo.utils.log import get_logger

logger = get_logger(__name__)

# 正则表达式缓存
_REGEXPS: Dict[str, "re.Pattern"] = {}


def make_insert_sql(
    table: str,
    data: Dict[str, Any],
    auto_update: bool = False,
    update_columns: Tuple = (),
    insert_ignore: bool = False,
) -> str:
    """
    生成 MySQL INSERT 或 REPLACE 语句。

    Args:
        table (str): 表名
        data (dict): 表数据，JSON 格式字典
        auto_update (bool): 是否使用 REPLACE INTO（完全覆盖已存在记录）
        update_columns (tuple or list): 冲突时需更新的列名；指定后 auto_update 失效
        insert_ignore (bool): 是否使用 INSERT IGNORE，忽略重复数据

    Returns:
        str: 生成的 SQL 语句
    """
    keys = [f"`{key}`" for key in data.keys()]
    keys_str = list2str(keys).replace("'", "")

    values = [format_sql_value(value) for value in data.values()]
    values_str = list2str(values)

    if update_columns:
        if not isinstance(update_columns, (tuple, list)):
            update_columns = (update_columns,)
        update_clause = ", ".join(f"`{key}`=VALUES(`{key}`)" for key in update_columns)
        ignore_flag = " IGNORE" if insert_ignore else ""
        sql = f"INSERT{ignore_flag} INTO `{table}` {keys_str} VALUES {values_str} ON DUPLICATE KEY UPDATE {update_clause}"

    elif auto_update:
        sql = f"REPLACE INTO `{table}` {keys_str} VALUES {values_str}"

    else:
        ignore_flag = " IGNORE" if insert_ignore else ""
        sql = f"INSERT{ignore_flag} INTO `{table}` {keys_str} VALUES {values_str}"

    return sql.replace("None", "null")


def make_update_sql(
    table: str,
    data: Dict[str, Any],
    condition: str,
) -> str:
    """
    生成 MySQL UPDATE 语句。

    Args:
        table (str): 表名
        data (dict): 更新字段的键值对，键为列名，值为新值
        condition (str): WHERE 条件，如 "id = 1"

    Returns:
        str: 生成的 SQL 语句
    """
    key_values: List[str] = []
    for key, value in data.items():
        formatted_value = format_sql_value(value)
        if isinstance(formatted_value, str):
            key_values.append(f"`{key}`={repr(formatted_value)}")
        elif formatted_value is None:
            key_values.append(f"`{key}`=null")
        else:
            key_values.append(f"`{key}`={formatted_value}")

    key_values_str = ", ".join(key_values)
    sql = f"UPDATE `{table}` SET {key_values_str} WHERE {condition}"
    return sql


def make_batch_sql(
    table: str,
    datas: List[Dict[str, Any]],
    auto_update: bool = False,
    update_columns: Tuple = (),
    update_columns_value: Tuple = (),
) -> Optional[Tuple[str, List[List[Any]]]]:
    """
    生成批量插入 SQL 及对应值列表。

    支持 INSERT IGNORE、REPLACE INTO 和 ON DUPLICATE KEY UPDATE。

    Args:
        table (str): 表名
        datas (list of dict): 数据列表，如 [{'col1': val1}, ...]
        auto_update (bool): 使用 REPLACE INTO 替代 INSERT
        update_columns (tuple or list): 主键冲突时要更新的列名
        update_columns_value (tuple): 更新列对应的固定值，如 ('%s',) 或 ('default',)

    Returns:
        tuple[str, list[list]] | None: (SQL语句, 值列表)；若数据为空则返回 None
    """
    if not datas:
        return None

    # 提取所有唯一字段名
    keys = list({key for data in datas for key in data})
    values_list = []

    for data in datas:
        if not isinstance(data, dict):
            continue  # 跳过非字典数据

        row = []
        for key in keys:
            raw_value = data.get(key)
            try:
                formatted_value = format_sql_value(raw_value)
                row.append(formatted_value)
            except Exception as e:
                logger.error(f"{key}: {raw_value} (类型: {type(raw_value)}) -> {e}")
        values_list.append(row)

    keys_str = ", ".join(f"`{key}`" for key in keys)
    placeholders_str = ", ".join(["%s"] * len(keys))

    if update_columns:
        if not isinstance(update_columns, (tuple, list)):
            update_columns = (update_columns,)

        if update_columns_value:
            update_pairs = [
                f"`{key}`={value}"
                for key, value in zip(update_columns, update_columns_value)
            ]
        else:
            update_pairs = [
                f"`{key}`=VALUES(`{key}`)" for key in update_columns
            ]
        update_clause = ", ".join(update_pairs)
        sql = f"INSERT INTO `{table}` ({keys_str}) VALUES ({placeholders_str}) ON DUPLICATE KEY UPDATE {update_clause}"

    elif auto_update:
        sql = f"REPLACE INTO `{table}` ({keys_str}) VALUES ({placeholders_str})"

    else:
        sql = f"INSERT IGNORE INTO `{table}` ({keys_str}) VALUES ({placeholders_str})"

    return sql, values_list


def format_sql_value(value: Any) -> Union[str, int, float, None]:
    """
    格式化 SQL 字段值，防止注入并兼容类型。

    处理字符串、数字、布尔、日期、列表/元组、字典等类型，不可序列化类型抛出异常。

    Args:
        value (Any): 待处理的值

    Returns:
        str | int | float | None: 格式化后的值，None 表示 SQL 的 NULL
    """
    if value is None:
        return None

    if isinstance(value, str):
        return value.strip()

    elif isinstance(value, (list, tuple, dict)):
        try:
            return json.dumps(value, ensure_ascii=False, default=str)
        except Exception as e:
            raise ValueError(f"Failed to serialize container to JSON: {value}, error: {e}")

    elif isinstance(value, bool):
        return int(value)

    elif isinstance(value, (int, float)):
        return value

    elif isinstance(value, (date, time, datetime)):
        return str(value)

    else:
        raise TypeError(f"Unsupported value type: {type(value)}, value: {value}")


def list2str(datas: List[Any]) -> str:
    """
    将列表转为 SQL 元组字符串格式。

    例如：[1, 2] → "(1, 2)"，单元素不带逗号：[1] → "(1)"

    Args:
        datas (list): 输入列表

    Returns:
        str: 对应的元组字符串表示
    """
    data_str = str(tuple(datas))
    return re.sub(r",\)$", ")", data_str)


def get_info(
    html: Union[str, Any],
    regexps: Union[str, List[str]],
    allow_repeat: bool = True,
    fetch_one: bool = False,
    split: Optional[str] = None,
) -> Union[str, List[str], Tuple]:
    """
    从 HTML 文本中提取信息，支持正则匹配和多模式 fallback。

    Args:
        html (str): HTML 内容或可转为字符串的类型
        regexps (str or list of str): 正则表达式，按顺序尝试匹配
        allow_repeat (bool): 是否允许重复结果
        fetch_one (bool): 是否只提取第一个匹配项（返回元组）
        split (str, optional): 若提供，则将结果用该字符连接成字符串

    Returns:
        str | list | tuple: 匹配结果，根据参数返回字符串、列表或元组
    """
    if isinstance(regexps, str):
        regexps = [regexps]

    infos = []
    for regex in regexps:
        if not regex:
            continue

        if regex not in _REGEXPS:
            _REGEXPS[regex] = re.compile(regex, re.S)

        if fetch_one:
            match = _REGEXPS[regex].search(str(html))
            infos = match.groups() if match else ("",)
            break
        else:
            found = _REGEXPS[regex].findall(str(html))
            if found:
                infos = found
                break

    if fetch_one:
        return infos[0] if len(infos) == 1 else infos

    if not allow_repeat:
        infos = sorted(set(infos), key=infos.index)

    return split.join(infos) if split else infos


def get_json(json_str: Union[str, Any]) -> Dict:
    """
    安全解析 JSON 字符串，兼容非标准格式（如单引号、缺少引号键）。

    尝试修复常见格式错误后再解析。

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
            keys = get_info(cleaned, r'(\w+):')
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


def dumps_json(
    data: Union[str, dict, list, Any],
    indent: int = 4,
    sort_keys: bool = False,
    ensure_ascii: bool = False,
    skip_keys: bool = True,
    default_repr: bool = False,
) -> str:
    """
    格式化任意对象为可读字符串，优先使用 JSON，失败时降级为 pprint 或 repr。

    支持自动处理 datetime、ObjectId 等不可序列化类型。

    Args:
        data (Any): 输入数据，支持字符串、字典、列表等
        indent (int): JSON 缩进空格数
        sort_keys (bool): 是否对字典键排序
        ensure_ascii (bool): 是否转义非 ASCII 字符（False 可保留中文）
        skip_keys (bool): 遇到非法键时是否跳过（而非报错）
        default_repr (bool): 是否在最终失败时使用 repr() 降级

    Returns:
        str: 格式化后的字符串，适合日志输出或打印
    """
    try:
        if isinstance(data, str):
            if not data.strip():
                return '""'
            data = get_json(data)

        return json.dumps(
            data,
            ensure_ascii=ensure_ascii,
            indent=indent,
            skipkeys=skip_keys,
            sort_keys=sort_keys,
            default=str,
        )

    except (UnicodeDecodeError, ValueError, TypeError, OverflowError) as e:
        try:
            return pprint.pformat(data, indent=indent, width=80, compact=True)
        except Exception:
            if default_repr:
                return repr(data)
            return f"<无法序列化的对象: {type(data).__name__}>"