import json
import re
from pprint import pformat
from datetime import date, time, datetime

from crawlo.utils.log import get_logger


logger = get_logger(__name__)


def make_insert_sql(
        table, data, auto_update=False, update_columns=(), insert_ignore=False
):
    """
    @summary: 适用于mysql
    ---------
    @param table:
    @param data: 表数据 json格式
    @param auto_update: 使用的是replace into， 为完全覆盖已存在的数据
    @param update_columns: 需要更新的列 默认全部，当指定值时，auto_update设置无效，当duplicate key冲突时更新指定的列
    @param insert_ignore: 数据存在忽略
    ---------
    @result:
    """

    keys = ["`{}`".format(key) for key in data.keys()]
    keys = list2str(keys).replace("'", "")

    values = [format_sql_value(value) for value in data.values()]
    values = list2str(values)

    if update_columns:
        if not isinstance(update_columns, (tuple, list)):
            update_columns = [update_columns]
        update_columns_ = ", ".join(
            ["{key}=values({key})".format(key=key) for key in update_columns]
        )
        sql = (
                "insert%s into `{table}` {keys} values {values} on duplicate key update %s"
                % (" ignore" if insert_ignore else "", update_columns_)
        )

    elif auto_update:
        sql = "replace into `{table}` {keys} values {values}"
    else:
        sql = "insert%s into `{table}` {keys} values {values}" % (
            " ignore" if insert_ignore else ""
        )

    sql = sql.format(table=table, keys=keys, values=values).replace("None", "null")
    return sql


def make_update_sql(table, data, condition):
    """
    @summary: 适用于mysql， oracle数据库时间需要to_date 处理（TODO）
    ---------
    @param table:
    @param data: 表数据 json格式
    @param condition: where 条件
    ---------
    @result:
    """
    key_values = []

    for key, value in data.items():
        value = format_sql_value(value)
        if isinstance(value, str):
            key_values.append("`{}`={}".format(key, repr(value)))
        elif value is None:
            key_values.append("`{}`={}".format(key, "null"))
        else:
            key_values.append("`{}`={}".format(key, value))

    key_values = ", ".join(key_values)

    sql = "update `{table}` set {key_values} where {condition}"
    sql = sql.format(table=table, key_values=key_values, condition=condition)
    return sql


def make_batch_sql(
        table, datas, auto_update=False, update_columns=(), update_columns_value=()
):
    """
    @summary: 生成批量的SQL
    ---------
    @param table:
    @param datas: 表数据 [{...}]
    @param auto_update: 使用的是replace into，为完全覆盖已存在的数据
    @param update_columns: 需要更新的列，默认全部，当指定值时，auto_update设置无效，当duplicate key冲突时更新指定的列
    @param update_columns_value: 需要更新的列的值，默认为datas里边对应的值，注意如果值为字符串类型需要主动加单引号，如 update_columns_value=("'test'",)
    ---------
    @result:
    """
    if not datas:
        return

    keys = list(set([key for data in datas for key in data]))
    # values_placeholder = ["%s"] * len(keys)
    values = []
    for data in datas:
        # 检查 data 是否是字典类型
        if not isinstance(data, dict):
            # 如果 data 不是字典，记录错误日志并打印 data 的内容和类型
            # logger.error(f"期望的数据类型是字典，但实际得到: {data} (类型: {type(data)})")
            continue  # 跳过非字典类型的 data，继续处理下一个数据

        value = []
        for key in keys:
            # 从字典中获取当前 key 对应的值
            current_data = data.get(key)
            try:
                # 对值进行格式化处理
                current_data = format_sql_value(current_data)
                value.append(current_data)  # 将处理后的值添加到列表中
            except Exception as e:
                # 如果格式化失败，记录错误日志
                logger.error(f"{key}: {current_data} (类型: {type(current_data)}) -> {e}")

        # 将处理后的值列表添加到 values 中
        values.append(value)
    keys_str = ", ".join(["`{}`".format(key) for key in keys])
    placeholders_str = ", ".join(["%s"] * len(keys))

    if update_columns:
        if not isinstance(update_columns, (tuple, list)):
            update_columns = [update_columns]
        if update_columns_value:
            update_columns_ = ", ".join(
                [
                    "`{key}`={value}".format(key=key, value=value)
                    for key, value in zip(update_columns, update_columns_value)
                ]
            )
        else:
            # 修改这里，使用 VALUES() 函数来引用插入的值
            update_columns_ = ", ".join(
                ["`{key}`=VALUES(`{key}`)".format(key=key) for key in update_columns]
            )

        sql = f"INSERT INTO `{table}` ({keys_str}) VALUES ({placeholders_str}) ON DUPLICATE KEY UPDATE {update_columns_}"
    elif auto_update:
        sql = "REPLACE INTO `{table}` ({keys}) VALUES ({values_placeholder})".format(
            table=table, keys=keys_str, values_placeholder=placeholders_str
        )
    else:
        sql = "INSERT IGNORE INTO `{table}` ({keys}) VALUES ({values_placeholder})".format(
            table=table, keys=keys_str, values_placeholder=placeholders_str
        )
    return sql, values


def format_sql_value(value):
    """
    格式化 SQL 值
    """
    if value is None:
        return None  # 处理 NULL 值

    # 确保处理字符串
    if isinstance(value, str):
        return value.strip()  # 去除首尾空格

    # 处理列表或元组类型
    elif isinstance(value, (list, tuple)):
        try:
            return dumps_json(value)  # 将其转为 JSON 字符串
        except Exception as e:
            raise ValueError(f"Failed to serialize list/tuple to JSON: {value}, error: {e}")

    # 处理字典类型
    elif isinstance(value, dict):
        try:
            return dumps_json(value)  # 将其转为 JSON 字符串
        except Exception as e:
            raise ValueError(f"Failed to serialize dict to JSON: {value}, error: {e}")

    # 处理布尔类型
    elif isinstance(value, bool):
        return int(value)  # 转为整数

    # 确保数值类型优先匹配
    elif isinstance(value, (int, float)):
        return value  # 返回数值

    # 处理日期、时间类型
    elif isinstance(value, (date, time, datetime)):
        return str(value)  # 转换为字符串表示

    # 如果遇到无法处理的类型，抛出异常
    else:
        raise TypeError(f"Unsupported value type: {type(value)}, value: {value}")




def list2str(datas):
    """
    列表转字符串
    :param datas: [1, 2]
    :return: (1, 2)
    """
    data_str = str(tuple(datas))
    data_str = re.sub(r",\)$", ")", data_str)
    return data_str

_REGEXPS = {}

def get_info(html, regexps, allow_repeat=True, fetch_one=False, split=None):
    regexps = isinstance(regexps, str) and [regexps] or regexps

    infos = []
    for regex in regexps:
        if regex == "":
            continue

        if regex not in _REGEXPS.keys():
            _REGEXPS[regex] = re.compile(regex, re.S)

        if fetch_one:
            infos = _REGEXPS[regex].search(html)
            if infos:
                infos = infos.groups()
            else:
                continue
        else:
            infos = _REGEXPS[regex].findall(str(html))

        if len(infos) > 0:
            break

    if fetch_one:
        infos = infos if infos else ("",)
        return infos if len(infos) > 1 else infos[0]
    else:
        infos = allow_repeat and infos or sorted(set(infos), key=infos.index)
        infos = split.join(infos) if split else infos
        return infos


def get_json(json_str):
    """
    @summary: 取json对象
    ---------
    @param json_str: json格式的字符串
    ---------
    @result: 返回json对象
    """

    try:
        return json.loads(json_str) if json_str else {}
    except Exception as e1:
        try:
            json_str = json_str.strip()
            json_str = json_str.replace("'", '"')
            keys = get_info(json_str, r"(\w+):")
            for key in keys:
                json_str = json_str.replace(key, '"%s"' % key)

            return json.loads(json_str) if json_str else {}

        except Exception as e2:
            logger.error(
                """
                e1: %s
                format json_str: %s
                e2: %s
                """
                % (e1, json_str, e2)
            )

        return {}


def dumps_json(data, indent=4, sort_keys=False):
    """
    @summary: 格式化json 用于打印
    ---------
    @param data: json格式的字符串或json对象
    @param indent:
    @param sort_keys:
    ---------
    @result: 格式化后的字符串
    """
    try:
        if isinstance(data, str):
            data = get_json(data)

        data = json.dumps(
            data,
            ensure_ascii=False,
            indent=indent,
            skipkeys=True,
            sort_keys=sort_keys,
            default=str,
        )

    except Exception as e:
        data = pformat(data)

    return data