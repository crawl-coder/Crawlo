#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
检查点存储后端
提供 JSON 和 SQLite 两种存储方式，用于持久化爬取状态。
"""
import json
import os
import sqlite3
import tempfile
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set

from crawlo.logging import get_logger


class BaseStorage(ABC):
    """检查点存储后端基类"""

    @abstractmethod
    def save(self, data: Dict[str, Any]) -> bool:
        """保存检查点数据"""

    @abstractmethod
    def load(self) -> Optional[Dict[str, Any]]:
        """加载检查点数据"""

    @abstractmethod
    def exists(self) -> bool:
        """检查点是否存在"""

    @abstractmethod
    def clear(self) -> bool:
        """清除检查点"""


class JsonStorage(BaseStorage):
    """JSON 文件存储后端（默认，适合小规模场景）

    文件路径：.checkpoints/{project_name}/{spider_name}.json
    存储内容：序列化的请求列表 + 指纹集合 + 元数据
    """

    def __init__(self, spider_name: str, project_name: str = 'default', checkpoint_dir: Optional[str] = None):
        self.logger = get_logger('JsonStorage')

        if checkpoint_dir:
            self._dir = checkpoint_dir
        else:
            # 默认使用当前工作目录（项目根目录）下的 .checkpoints
            self._dir = os.path.join(os.getcwd(), '.checkpoints')

        self._dir = os.path.join(self._dir, project_name)
        self._path = os.path.join(self._dir, f'{spider_name}.json')

        # 确保目录存在
        os.makedirs(self._dir, exist_ok=True)

    def save(self, data: Dict[str, Any]) -> bool:
        """保存检查点到 JSON 文件（原子写入）"""
        try:
            # 将 set 转为 list 以便 JSON 序列化
            serializable = {
                'version': 1,
                'saved_at': time.time(),
                'project_name': data.get('project_name', ''),
                'spider_name': data.get('spider_name', ''),
                'pending_count': data.get('pending_count', 0),
                'fingerprints': list(data.get('fingerprints', set())),
                'requests': data.get('requests', []),
                'stats': data.get('stats', {}),
            }

            # 使用临时文件 + 原子重命名，防止写入中断导致文件损坏
            dir_name = os.path.dirname(self._path)
            fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix='.tmp')
            
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(serializable, f, ensure_ascii=False, indent=2)
                
                # 原子替换（POSIX 系统保证原子性）
                os.replace(tmp_path, self._path)
            except:
                # 如果失败，清理临时文件
                try:
                    os.unlink(tmp_path)
                except:
                    pass
                raise

            self.logger.debug(f"Checkpoint saved to {self._path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save checkpoint: {e}")
            return False

    def load(self) -> Optional[Dict[str, Any]]:
        """从 JSON 文件加载检查点"""
        try:
            if not os.path.exists(self._path):
                return None

            with open(self._path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 将 list 转回 set
            data['fingerprints'] = set(data.get('fingerprints', []))

            return data

        except Exception as e:
            self.logger.error(f"Failed to load checkpoint: {e}")
            return None

    def exists(self) -> bool:
        """检查点文件是否存在"""
        return os.path.exists(self._path)

    def clear(self) -> bool:
        """删除检查点文件"""
        try:
            if os.path.exists(self._path):
                os.unlink(self._path)
                self.logger.debug(f"Checkpoint cleared: {self._path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear checkpoint: {e}")
            return False


class SqliteStorage(BaseStorage):
    """SQLite 存储后端（适合大规模场景）

    文件路径：.checkpoints/{project_name}/{spider_name}.db
    三个表：pending_requests、fingerprints、metadata
    """

    def __init__(self, spider_name: str, project_name: str = 'default', checkpoint_dir: Optional[str] = None):
        self.logger = get_logger('SqliteStorage')

        if checkpoint_dir:
            self._dir = checkpoint_dir
        else:
            # 默认使用当前工作目录（项目根目录）下的 .checkpoints
            self._dir = os.path.join(os.getcwd(), '.checkpoints')

        self._dir = os.path.join(self._dir, project_name)
        self._path = os.path.join(self._dir, f'{spider_name}.db')

        # 确保目录存在
        os.makedirs(self._dir, exist_ok=True)

        # 初始化表
        self._init_tables()

    def _init_tables(self):
        """初始化数据库表"""
        try:
            with sqlite3.connect(self._path) as conn:
                c = conn.cursor()

                c.execute('''
                    CREATE TABLE IF NOT EXISTS metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                ''')

                c.execute('''
                    CREATE TABLE IF NOT EXISTS pending_requests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        priority INTEGER DEFAULT 0,
                        data TEXT NOT NULL
                    )
                ''')

                c.execute('''
                    CREATE TABLE IF NOT EXISTS fingerprints (
                        fingerprint TEXT PRIMARY KEY
                    )
                ''')

                conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to init tables: {e}")

    def save(self, data: Dict[str, Any]) -> bool:
        """保存检查点到 SQLite"""
        try:
            with sqlite3.connect(self._path) as conn:
                # 开启显式事务
                conn.execute('BEGIN TRANSACTION')
                c = conn.cursor()

                # 清空旧数据
                c.execute('DELETE FROM metadata')
                c.execute('DELETE FROM pending_requests')
                c.execute('DELETE FROM fingerprints')

                # 写入元数据
                metadata = {
                    'version': '1',
                    'saved_at': str(time.time()),
                    'project_name': data.get('project_name', ''),
                    'spider_name': data.get('spider_name', ''),
                    'pending_count': str(data.get('pending_count', 0)),
                }
                for k, v in metadata.items():
                    c.execute('INSERT INTO metadata (key, value) VALUES (?, ?)', (k, v))

                # 写入统计信息
                stats = data.get('stats', {})
                if stats:
                    c.execute('INSERT INTO metadata (key, value) VALUES (?, ?)',
                              ('stats', json.dumps(stats, ensure_ascii=False)))

                # 写入待处理请求
                requests = data.get('requests', [])
                for req_data in requests:
                    priority = req_data.get('priority', 0) if isinstance(req_data, dict) else 0
                    c.execute('INSERT INTO pending_requests (priority, data) VALUES (?, ?)',
                              (priority, json.dumps(req_data, ensure_ascii=False) if isinstance(req_data, dict) else str(req_data)))

                # 写入指纹
                fingerprints = data.get('fingerprints', set())
                for fp in fingerprints:
                    c.execute('INSERT OR IGNORE INTO fingerprints (fingerprint) VALUES (?)', (fp,))

                conn.commit()

            self.logger.debug(f"Checkpoint saved to {self._path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save checkpoint: {e}")
            return False

    def load(self) -> Optional[Dict[str, Any]]:
        """从 SQLite 加载检查点"""
        try:
            if not os.path.exists(self._path):
                return None

            with sqlite3.connect(self._path) as conn:
                c = conn.cursor()

                # 读取元数据
                c.execute('SELECT key, value FROM metadata')
                metadata = dict(c.fetchall())

                # 读取统计信息
                stats = {}
                if 'stats' in metadata:
                    try:
                        stats = json.loads(metadata['stats'])
                    except (json.JSONDecodeError, TypeError):
                        pass

                # 读取待处理请求
                c.execute('SELECT data FROM pending_requests ORDER BY priority ASC')
                requests = []
                for row in c.fetchall():
                    try:
                        requests.append(json.loads(row[0]))
                    except (json.JSONDecodeError, TypeError):
                        requests.append(row[0])

                # 读取指纹
                c.execute('SELECT fingerprint FROM fingerprints')
                fingerprints = set(row[0] for row in c.fetchall())

            return {
                'version': int(metadata.get('version', '1')),
                'saved_at': float(metadata.get('saved_at', '0')),
                'project_name': metadata.get('project_name', ''),
                'spider_name': metadata.get('spider_name', ''),
                'pending_count': int(metadata.get('pending_count', '0')),
                'requests': requests,
                'fingerprints': fingerprints,
                'stats': stats,
            }

        except Exception as e:
            self.logger.error(f"Failed to load checkpoint: {e}")
            return None

    def exists(self) -> bool:
        """检查点数据库是否存在"""
        return os.path.exists(self._path)

    def clear(self) -> bool:
        """删除检查点数据库"""
        try:
            if os.path.exists(self._path):
                os.unlink(self._path)
                self.logger.debug(f"Checkpoint cleared: {self._path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear checkpoint: {e}")
            return False
