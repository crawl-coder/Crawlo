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
    def format_value(value: Any) -> Any:
        """
        预处理值，主要处理 JSON 序列化。
        不再进行字符串转义，转义交给 DB 驱动。

        Args:
            value (Any): 待处理的值

        Returns:
            Any: 处理后的值
        """
        if value is None:
            return None

        if isinstance(value, (list, tuple, dict)):
            try:
                return json.dumps(value, ensure_ascii=False, default=str)
            except Exception as e:
                raise ValueError(f"JSON serialization failed: {e}")

        # 对于日期、数字、布尔值，直接返回，驱动库通常能处理
        # 如果驱动库对日期支持不好，可以在这里 str(value)
        if isinstance(value, (date, time, datetime)):
            return str(value)
            
        return value

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
    def _build_update_clause(update_columns: Union[Tuple, List], use_values_func: bool = True) -> str:
        """构建 ON DUPLICATE KEY UPDATE 子句"""
        if not isinstance(update_columns, (tuple, list)):
            update_columns = (update_columns,)
        
        if use_values_func:
            return ", ".join(f"`{col}`=VALUES(`{col}`)" for col in update_columns)
        return ", ".join(f"`{col}`=`excluded`.`{col}`" for col in update_columns)

    @staticmethod
    def make_insert(
        table: str,
        data: Dict[str, Any],
        auto_update: bool = False,
        update_columns: Tuple = (),
        insert_ignore: bool = False,
        prefer_alias: bool = True,
    ) -> Tuple[str, List[Any]]:
        """
        生成参数化的 INSERT/REPLACE 语句。
        
        Returns:
            (sql, params): 返回 SQL 模版和参数列表
        """
        # 1. 提取键和处理后的值
        keys = list(data.keys())
        values = [SQLBuilder.format_value(data[k]) for k in keys]
        
        # 2. 构建 SQL 片段
        keys_str = ", ".join(f"`{k}`" for k in keys)
        placeholders = ", ".join(["%s"] * len(keys))
        
        table_fmt = f"`{table}`"
        
        # 3. 组装 SQL
        if update_columns:
            update_clause = SQLBuilder._build_update_clause(update_columns, use_values_func=not prefer_alias)
            ignore = " IGNORE" if insert_ignore else ""
            if prefer_alias:
                sql = f"INSERT{ignore} INTO {table_fmt} ({keys_str}) VALUES ({placeholders}) AS `excluded` ON DUPLICATE KEY UPDATE {update_clause}"
            else:
                sql = f"INSERT{ignore} INTO {table_fmt} ({keys_str}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_clause}"
            
        elif auto_update:
            sql = f"REPLACE INTO {table_fmt} ({keys_str}) VALUES ({placeholders})"
            
        else:
            ignore = " IGNORE" if insert_ignore else ""
            sql = f"INSERT{ignore} INTO {table_fmt} ({keys_str}) VALUES ({placeholders})"

        # 返回元组，而不是拼接好的字符串
        return sql, values

    @staticmethod
    def make_update(
        table: str,
        data: Dict[str, Any],
        condition: str,
        condition_args: Optional[List[Any]] = None
    ) -> Tuple[str, List[Any]]:
        """
        生成参数化的 UPDATE 语句。
        """
        set_clauses = []
        values = []
        
        for key, value in data.items():
            set_clauses.append(f"`{key}`=%s")
            values.append(SQLBuilder.format_value(value))
            
        set_str = ", ".join(set_clauses)
        
        # 警告：condition 仍然是原生字符串，调用者需确保 condition 安全
        # 更好的做法是 condition 也支持参数化，这里简单追加 condition_args
        sql = f"UPDATE `{table}` SET {set_str} WHERE {condition}"
        
        if condition_args:
            values.extend(condition_args)
            
        return sql, values

    @staticmethod
    def make_batch(
        table: str,
        datas: List[Dict[str, Any]],
        auto_update: bool = False,
        update_columns: Tuple = (),
        prefer_alias: bool = True,
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

        # 1. 确定所有列名，并排序以保证确定性
        all_keys = set()
        for d in datas:
            all_keys.update(d.keys())
        keys = sorted(list(all_keys)) # 排序，避免随机顺序
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
                    row.append(None)  # 如果格式化失败，添加None值
            values_list.append(row)

        keys_str = ", ".join(f"`{key}`" for key in keys)
        placeholders_str = ", ".join(["%s"] * len(keys))

        if update_columns:
            if not isinstance(update_columns, (tuple, list)):
                update_columns = (update_columns,)

            if update_columns:
                update_clause = SQLBuilder._build_update_clause(update_columns, use_values_func=not prefer_alias)
                if prefer_alias:
                    sql = f"INSERT INTO `{table}` ({keys_str}) VALUES ({placeholders_str}) AS `excluded` ON DUPLICATE KEY UPDATE {update_clause}"
                else:
                    sql = f"INSERT INTO `{table}` ({keys_str}) VALUES ({placeholders_str}) ON DUPLICATE KEY UPDATE {update_clause}"
            elif auto_update:
                sql = f"REPLACE INTO `{table}` ({keys_str}) VALUES ({placeholders_str})"
            else:
                sql = f"INSERT IGNORE INTO `{table}` ({keys_str}) VALUES ({placeholders_str})"

        elif auto_update:
            sql = f"REPLACE INTO `{table}` ({keys_str}) VALUES ({placeholders_str})"

        else:
            sql = f"INSERT IGNORE INTO `{table}` ({keys_str}) VALUES ({placeholders_str})"

        return sql, values_list
