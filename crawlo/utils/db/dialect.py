# -*- coding: utf-8 -*-
"""
SQL 方言描述器
==============
定义各数据库的 SQL 语法差异，子类通过声明式配置减少 SQL 构建代码。

设计文档：docs/internal/db-pipelines-design.md §2.4
"""

from typing import List, Dict, Optional


class SQLDialect:
    """SQL 方言基类 — 子类通过声明式配置消除 SQL 构建重复代码"""

    # ── 必须覆盖 ──
    placeholder: str = '%s'            # 参数占位符: MySQL='%s', PG='${i}', SQLite='?'
    quote_char: str = '"'              # 标识符引号: MySQL='`', PG='"', SQLite='"'

    # ── 可选覆盖 ──
    insert_template: str = 'INSERT INTO {table} ({cols}) VALUES ({vals})'
    upsert_template: Optional[str] = None    # UPSERT 语法模板
    insert_ignore_template: Optional[str] = None  # INSERT IGNORE 语法
    replace_template: Optional[str] = None   # REPLACE 语法

    # ── 辅助方法 ──

    @classmethod
    def quote(cls, name: str) -> str:
        """为标识符添加引号"""
        q = cls.quote_char
        return f'{q}{name}{q}'

    @classmethod
    def build_cols_str(cls, cols: List[str]) -> str:
        """构建带引号的列名字符串"""
        return ', '.join(cls.quote(col) for col in cols)

    @classmethod
    def build_placeholder(cls, col_index: int) -> str:
        """构建单个占位符（从 0 开始计数）"""
        return cls.placeholder

    @classmethod
    def build_placeholders(cls, count: int) -> str:
        """构建多个占位符"""
        return ', '.join(cls.build_placeholder(i) for i in range(count))

    @classmethod
    def build_insert(cls, table: str, cols: List[str]) -> str:
        """构建基础 INSERT 语句"""
        return cls.insert_template.format(
            table=cls.quote(table),
            cols=cls.build_cols_str(cols),
            vals=cls.build_placeholders(len(cols)),
        )

    @classmethod
    def build_upsert(
        cls,
        table: str,
        data: Dict,
        conflict_cols: tuple = (),
        update_cols: tuple = (),
    ) -> tuple:
        """
        构建 UPSERT SQL 语句（INSERT ... ON DUPLICATE KEY UPDATE / ON CONFLICT ...）
        返回 (sql, params) 元组
        """
        if cls.upsert_template is None:
            if cls.replace_template is not None:
                return cls.build_replace(table, data)
            return cls.build_insert(table, list(data.keys())), tuple(data.values())

        cols = list(data.keys())
        params = tuple(data.values())
        sql = cls.upsert_template.format(
            table=cls.quote(table),
            cols=cls.build_cols_str(cols),
            vals=cls.build_placeholders(len(cols)),
            conflict_cols=cls.build_cols_str(list(conflict_cols)),
            updates=', '.join(
                f'{cls.quote(c)} = EXCLUDED.{cls.quote(c)}'
                for c in update_cols
            ) if update_cols else '',
        )
        return sql, params

    @classmethod
    def build_insert_ignore(
        cls, table: str, data: Dict, conflict_cols: tuple = ()
    ) -> tuple:
        """构建 INSERT IGNORE SQL 语句"""
        if cls.insert_ignore_template is None:
            return cls.build_insert(table, list(data.keys())), tuple(data.values())

        cols = list(data.keys())
        params = tuple(data.values())
        sql = cls.insert_ignore_template.format(
            table=cls.quote(table),
            cols=cls.build_cols_str(cols),
            vals=cls.build_placeholders(len(cols)),
            conflict_cols=cls.build_cols_str(list(conflict_cols)),
        )
        return sql, params

    @classmethod
    def build_replace(cls, table: str, data: Dict) -> tuple:
        """构建 REPLACE INTO SQL 语句"""
        if cls.replace_template is None:
            return cls.build_insert(table, list(data.keys())), tuple(data.values())

        cols = list(data.keys())
        params = tuple(data.values())
        sql = cls.replace_template.format(
            table=cls.quote(table),
            cols=cls.build_cols_str(cols),
            vals=cls.build_placeholders(len(cols)),
        )
        return sql, params


class MySQLDialect(SQLDialect):
    """MySQL 方言"""
    placeholder = '%s'
    quote_char = '`'
    upsert_template = (
        'INSERT INTO {table} ({cols}) VALUES ({vals}) '
        'ON DUPLICATE KEY UPDATE {updates}'
    )
    insert_ignore_template = 'INSERT IGNORE INTO {table} ({cols}) VALUES ({vals})'
    replace_template = 'REPLACE INTO {table} ({cols}) VALUES ({vals})'


class PostgreSQLDialect(SQLDialect):
    """
    PostgreSQL 方言

    占位符使用 $1, $2（非 MySQL 的 %s）
    ON CONFLICT 必须显式指定冲突列
    """

    placeholder = '%s'  # asyncpg 使用 %s 占位符，内部自动转为 $1, $2
    quote_char = '"'
    upsert_template = (
        'INSERT INTO {table} ({cols}) VALUES ({vals}) '
        'ON CONFLICT ({conflict_cols}) DO UPDATE SET {updates}'
    )
    insert_ignore_template = (
        'INSERT INTO {table} ({cols}) VALUES ({vals}) '
        'ON CONFLICT DO NOTHING'
    )

    @classmethod
    def build_placeholder(cls, col_index: int) -> str:
        """PostgreSQL 使用 $1, $2 风格占位符"""
        return f'${col_index + 1}'


class SQLiteDialect(SQLDialect):
    """SQLite 方言"""
    placeholder = '?'
    quote_char = '"'
    insert_ignore_template = 'INSERT OR IGNORE INTO {table} ({cols}) VALUES ({vals})'
    replace_template = 'INSERT OR REPLACE INTO {table} ({cols}) VALUES ({vals})'


class ClickHouseDialect(SQLDialect):
    """
    ClickHouse 方言

    ClickHouse 无传统 UPSERT，依赖 ReplacingMergeTree 引擎后台去重。
    仅提供基础 INSERT 模板。
    """
    placeholder = '%s'
    quote_char = '`'
    insert_template = 'INSERT INTO {table} ({cols}) VALUES ({vals})'
