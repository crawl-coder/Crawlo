# -*- coding: utf-8 -*-
import json
from enum import Enum
from datetime import date, time, datetime
from typing import Any, Union, List, Dict, Tuple, Optional

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
        
        # 3. 组装 SQL，明确优先级：update_columns > auto_update > insert_ignore
        if update_columns and len(update_columns) > 0:
            # 【关键修复】当使用 ON DUPLICATE KEY UPDATE 时，不应该使用 IGNORE
            # 因为 ON DUPLICATE KEY UPDATE 本身就是处理重复的策略
            update_clause = SQLBuilder._build_update_clause(update_columns, use_values_func=not prefer_alias)
            if prefer_alias:
                sql = f"INSERT INTO {table_fmt} ({keys_str}) VALUES ({placeholders}) AS `excluded` ON DUPLICATE KEY UPDATE {update_clause}"
            else:
                sql = f"INSERT INTO {table_fmt} ({keys_str}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_clause}"
        elif auto_update:
            sql = f"REPLACE INTO {table_fmt} ({keys_str}) VALUES ({placeholders})"
        elif insert_ignore:
            sql = f"INSERT IGNORE INTO {table_fmt} ({keys_str}) VALUES ({placeholders})"
        else:
            sql = f"INSERT INTO {table_fmt} ({keys_str}) VALUES ({placeholders})"

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
        insert_ignore: bool = False,
        prefer_alias: bool = True,
    ) -> Optional[Tuple[str, List[Any]]]:
        """
        生成批量插入 SQL 及对应值列表（铺平为单个列表）。

        Args:
            table (str): 表名
            datas (list of dict): 数据列表
            auto_update (bool): 使用 REPLACE INTO 替代 INSERT
            update_columns (tuple or list): 主键冲突时要更新的列名
            insert_ignore (bool): 是否使用 INSERT IGNORE
            prefer_alias (bool): 是否使用别名语法

        Returns:
            tuple[str, list] | None: (SQL语句, 铺平的值列表)；若数据为空则返回 None
        """
        if not datas:
            return None

        # 1. 确定并排序所有列名
        all_keys = sorted(list(set().union(*(d.keys() for d in datas))))
        
        # 2. 构建多行占位符和铺平后的值列表 (关键：解决2014错误)
        flattened_values = []
        row_placeholders = []
        single_row_placeholder = "(" + ", ".join(["%s"] * len(all_keys)) + ")"
        
        for data in datas:
            if not isinstance(data, dict):
                continue  # 跳过非字典数据
            row_placeholders.append(single_row_placeholder)
            for key in all_keys:
                raw_value = data.get(key)
                try:
                    formatted_value = SQLBuilder.format_value(raw_value)
                    flattened_values.append(formatted_value)
                except Exception as e:
                    logger.error(f"{key}: {raw_value} (类型: {type(raw_value)}) -> {e}")
                    flattened_values.append(None)  # 如果格式化失败，添加None值

        all_rows_placeholders = ", ".join(row_placeholders)
        keys_str = ", ".join(f"`{k}`" for k in all_keys)

        # 3. 优先级逻辑修复
        if update_columns and len(update_columns) > 0:
            if not isinstance(update_columns, (tuple, list)):
                update_columns = (update_columns,)
            update_clause = SQLBuilder._build_update_clause(update_columns, use_values_func=not prefer_alias)
            alias_str = " AS `excluded`" if prefer_alias else ""
            sql = f"INSERT INTO `{table}` ({keys_str}) VALUES {all_rows_placeholders}{alias_str} ON DUPLICATE KEY UPDATE {update_clause}"
        elif auto_update:
            sql = f"REPLACE INTO `{table}` ({keys_str}) VALUES {all_rows_placeholders}"
        elif insert_ignore:
            sql = f"INSERT IGNORE INTO `{table}` ({keys_str}) VALUES {all_rows_placeholders}"
        else:
            sql = f"INSERT INTO `{table}` ({keys_str}) VALUES {all_rows_placeholders}"

        return sql, flattened_values
