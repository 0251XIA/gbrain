"""
GBrain 数据库模块 - SQLite + sqlite-vec 向量搜索
"""

import json
import sqlite3
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from .config import DATA_PATH, VECTOR_DIM


class Database:
    """SQLite + sqlite-vec 数据库封装"""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = DATA_PATH / "gbrain.db"
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self):
        """初始化数据库和向量扩展"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row

        # 加载 sqlite-vec 扩展
        try:
            self.conn.execute("SELECT vec_version()")
        except sqlite3.OperationalError:
            try:
                self.conn.execute("SELECT load_extension('vec0')")
            except:
                pass

        self._create_tables()

    def _create_tables(self):
        """创建表结构"""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS pages (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT DEFAULT '通用',
                tags TEXT DEFAULT '[]',
                links TEXT DEFAULT '[]',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS page_vectors (
                page_id TEXT PRIMARY KEY,
                embedding BLOB,
                FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                properties TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                properties TEXT DEFAULT '{}',
                FOREIGN KEY (source_id) REFERENCES entities(id),
                FOREIGN KEY (target_id) REFERENCES entities(id)
            );

            CREATE TABLE IF NOT EXISTS qa_records (
                id TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT,
                archived INTEGER DEFAULT 0,
                pending INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_pages_category ON pages(category);
            CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
            CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_id);
            CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_id);
        """)
        self.conn.commit()

    @contextmanager
    def get_cursor(self):
        cursor = self.conn.cursor()
        try:
            yield cursor
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cursor.close()

    def insert_page(self, page_id: str, title: str, content: str,
                    category: str = "通用", tags: list = None,
                    links: list = None, embedding: bytes = None) -> bool:
        try:
            with self.get_cursor() as c:
                c.execute(
                    """INSERT OR REPLACE INTO pages
                       (id, title, content, category, tags, links, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                    (page_id, title, content, category,
                     json.dumps(tags or []),
                     json.dumps(links or []))
                )
                if embedding:
                    c.execute(
                        """INSERT OR REPLACE INTO page_vectors (page_id, embedding)
                           VALUES (?, ?)""",
                        (page_id, embedding)
                    )
            return True
        except Exception as e:
            print(f"插入页面失败: {e}")
            return False

    def get_page(self, page_id: str) -> Optional[dict]:
        with self.get_cursor() as c:
            c.execute("SELECT * FROM pages WHERE id = ?", (page_id,))
            row = c.fetchone()
            if row:
                return dict(row)
        return None

    def get_all_pages(self) -> list[dict]:
        with self.get_cursor() as c:
            c.execute("SELECT * FROM pages ORDER BY updated_at DESC")
            return [dict(row) for row in c.fetchall()]

    def delete_page(self, page_id: str) -> bool:
        try:
            with self.get_cursor() as c:
                c.execute("DELETE FROM pages WHERE id = ?", (page_id,))
            return True
        except:
            return False

    def init_vector_index(self):
        try:
            with self.get_cursor() as c:
                c.execute(f"""
                    CREATE VIRTUAL TABLE IF NOT EXISTS page_embeddings
                    USING vec0(page_id TEXT PRIMARY KEY, embedding float[{VECTOR_DIM}])
                """)
            return True
        except Exception as e:
            print(f"向量索引初始化失败: {e}")
            return False

    def insert_vector(self, page_id: str, embedding: list[float]) -> bool:
        try:
            import struct
            embedding_bytes = struct.pack(f'{len(embedding)}f', *embedding)
            with self.get_cursor() as c:
                c.execute(
                    """INSERT OR REPLACE INTO page_embeddings (page_id, embedding)
                       VALUES (?, ?)""",
                    (page_id, embedding_bytes)
                )
            return True
        except Exception as e:
            print(f"向量插入失败: {e}")
            return False

    def search_vectors(self, query_embedding: list[float],
                       top_k: int = 5) -> list[tuple]:
        try:
            import struct
            query_bytes = struct.pack(f'{len(query_embedding)}f', *query_embedding)
            with self.get_cursor() as c:
                c.execute("""
                    SELECT page_id, distance
                    FROM page_embeddings
                    ORDER BY distance
                    LIMIT ?
                """, (top_k,))
                return [(row[0], row[1]) for row in c.fetchall()]
        except Exception as e:
            print(f"向量搜索失败: {e}")
            return []

    def insert_entity(self, entity_id: str, name: str,
                      entity_type: str, properties: dict = None) -> bool:
        try:
            with self.get_cursor() as c:
                c.execute(
                    """INSERT OR REPLACE INTO entities
                       (id, name, entity_type, properties) VALUES (?, ?, ?, ?)""",
                    (entity_id, name, entity_type, json.dumps(properties or {}))
                )
            return True
        except:
            return False

    def insert_relation(self, source_id: str, target_id: str,
                        relation_type: str, properties: dict = None) -> bool:
        try:
            with self.get_cursor() as c:
                c.execute(
                    """INSERT INTO relations (source_id, target_id, relation_type, properties)
                       VALUES (?, ?, ?, ?)""",
                    (source_id, target_id, relation_type, json.dumps(properties or {}))
                )
            return True
        except:
            return False

    def get_entity(self, entity_id: str) -> Optional[dict]:
        with self.get_cursor() as c:
            c.execute("SELECT * FROM entities WHERE id = ?", (entity_id,))
            row = c.fetchone()
            if row:
                return dict(row)
        return None

    def get_all_entities(self) -> list[dict]:
        with self.get_cursor() as c:
            c.execute("SELECT * FROM entities")
            return [dict(row) for row in c.fetchall()]

    def get_relations(self, entity_id: str = None,
                       relation_type: str = None) -> list[dict]:
        with self.get_cursor() as c:
            if entity_id:
                c.execute(
                    """SELECT * FROM relations
                       WHERE source_id = ? OR target_id = ?""",
                    (entity_id, entity_id)
                )
            elif relation_type:
                c.execute("SELECT * FROM relations WHERE relation_type = ?",
                         (relation_type,))
            else:
                c.execute("SELECT * FROM relations")
            return [dict(row) for row in c.fetchall()]

    def insert_qa(self, qa_id: str, question: str,
                  answer: str = None, pending: bool = False) -> bool:
        try:
            with self.get_cursor() as c:
                c.execute(
                    """INSERT INTO qa_records (id, question, answer, pending)
                       VALUES (?, ?, ?, ?)""",
                    (qa_id, question, answer, 1 if pending else 0)
                )
            return True
        except:
            return False

    def get_pending_qa(self) -> list[dict]:
        with self.get_cursor() as c:
            c.execute("""SELECT * FROM qa_records
                       WHERE pending = 1 ORDER BY created_at DESC""")
            return [dict(row) for row in c.fetchall()]

    def archive_qa(self, qa_id: str) -> bool:
        try:
            with self.get_cursor() as c:
                c.execute(
                    """UPDATE qa_records SET archived = 1, pending = 0
                       WHERE id = ?""",
                    (qa_id,)
                )
            return True
        except:
            return False

    def close(self):
        if self.conn:
            self.conn.close()
