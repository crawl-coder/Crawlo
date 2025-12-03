# -*- coding: utf-8 -*-
import json
import re
from typing import Any, Union, List, Dict, Tuple, Optional
from datetime import date, time, datetime
from enum import Enum

from crawlo.logging import get_logger

logger = get_logger(__name__)


class SQLStatementType(Enum):
    """SQL语句类型枚举"""
    INSERT = "INSERT"
    REPLACE = "REPLACE"
    UPDATE = "UPDATE"
    BATCH_INSERT = "BATCH_INSERT"
    BATCH_REPLACE = "BATCH_REPLACE"


class SQLBuilder:
    """SQL语句构建器"""
    
    @staticmethod
    def format_value(value: Any) -> Union[str, int, float, None]:
        """
        格式化 SQL 字段值，防止注入并兼容类型。

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

    @staticmethod
    def list_to_tuple_str(datas: List[Any]) -> str:
        """
        将列表转为 SQL 元组字符串格式。

        Args:
            datas (list): 输入列表

        Returns:
            str: 对应的元组字符串表示
        """
        if not datas:
            return "()"
        if len(datas) == 1:
            # 处理单元素元组，确保末尾有逗号
            return f"({datas[0]},)"
        return str(tuple(datas))

    @staticmethod
    def _build_key_value_pairs(data: Dict[str, Any]) -> Tuple[List[str], List[Any]]:
        """
        构建键值对列表

        Args:
            data (dict): 数据字典

        Returns:
            tuple: (键列表, 值列表)
        """
        keys = [f"`{key}`" for key in data.keys()]
        values = [SQLBuilder.format_value(value) for value in data.values()]
        return keys, values

    @staticmethod
    def _build_update_clause(update_columns: Union[Tuple, List], keys: List[str] = None) -> str:
        """
        构建更新子句，兼容不同版本的 MySQL 语法

        Args:
            update_columns (tuple or list): 更新列名
            keys (list): 所有列名列表，用于VALUES()语法

        Returns:
            str: 更新子句
        """
        if not isinstance(update_columns, (tuple, list)):
            update_columns = (update_columns,)
        
        # 如果提供了keys，则使用VALUES()语法以获得更好的兼容性
        if keys:
            return ", ".join(f"`{key}`=VALUES(`{key}`)" for key in update_columns)
        else:
            # 使用新的语法：INSERT ... VALUES (...) AS alias ... UPDATE ... alias.col
            # 确保使用 excluded 别名而不是 VALUES() 函数
            return ", ".join(f"`{key}`=`excluded`.`{key}`" for key in update_columns)

    @staticmethod
    def make_insert(
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
        keys, values = SQLBuilder._build_key_value_pairs(data)
        keys_str = SQLBuilder.list_to_tuple_str(keys).replace("'", "")
        values_str = SQLBuilder.list_to_tuple_str(values)

        if update_columns:
            # 为了更好的MySQL版本兼容性，使用VALUES()语法而不是AS alias语法
            update_clause = SQLBuilder._build_update_clause(update_columns, keys)
            ignore_flag = " IGNORE" if insert_ignore else ""
            # 使用VALUES()函数以获得更好的兼容性
            sql = f"INSERT{ignore_flag} INTO `{table}` {keys_str} VALUES {values_str} ON DUPLICATE KEY UPDATE {update_clause}"

        elif auto_update:
            sql = f"REPLACE INTO `{table}` {keys_str} VALUES {values_str}"

        else:
            ignore_flag = " IGNORE" if insert_ignore else ""
            sql = f"INSERT{ignore_flag} INTO `{table}` {keys_str} VALUES {values_str}"

        return sql.replace("None", "null")

    @staticmethod
    def make_update(
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
            formatted_value = SQLBuilder.format_value(value)
            if isinstance(formatted_value, str):
                key_values.append(f"`{key}`={repr(formatted_value)}")
            elif formatted_value is None:
                key_values.append(f"`{key}`=null")
            else:
                key_values.append(f"`{key}`={formatted_value}")

        key_values_str = ", ".join(key_values)
        sql = f"UPDATE `{table}` SET {key_values_str} WHERE {condition}"
        return sql

    @staticmethod
    def make_batch(
        table: str,
        datas: List[Dict[str, Any]],
        auto_update: bool = False,
        update_columns: Tuple = (),
        update_columns_value: Tuple = (),
    ) -> Optional[Tuple[str, List[List[Any]]]]:
        """
        生成批量插入 SQL 及对应值列表。

        Args:
            table (str): 表名
            datas (list of dict): 数据列表
            auto_update (bool): 使用 REPLACE INTO 替代 INSERT
            update_columns (tuple or list): 主键冲突时要更新的列名
            update_columns_value (tuple): 更新列对应的固定值

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
                    formatted_value = SQLBuilder.format_value(raw_value)
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
                # 当提供了固定值时，使用这些值进行更新
                update_pairs = [
                    f"`{key}`={value}"
                    for key, value in zip(update_columns, update_columns_value)
                ]
            else:
                # 使用VALUES()函数以获得更好的兼容性
                update_pairs = [
                    f"`{key}`=VALUES(`{key}`)" for key in update_columns
                ]
            update_clause = ", ".join(update_pairs)
            # 移除 AS `excluded` 语法以提高MySQL版本兼容性
            sql = f"INSERT INTO `{table}` ({keys_str}) VALUES ({placeholders_str}) ON DUPLICATE KEY UPDATE {update_clause}"

        elif auto_update:
            sql = f"REPLACE INTO `{table}` ({keys_str}) VALUES ({placeholders_str})"

        else:
            sql = f"INSERT IGNORE INTO `{table}` ({keys_str}) VALUES ({placeholders_str})"

        return sql, values_list