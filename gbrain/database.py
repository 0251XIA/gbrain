"""
GBrain 数据库模块 - SQLite + sqlite-vec 向量搜索
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from .config import DATA_PATH, VECTOR_DIM

logger = logging.getLogger(__name__)


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
        self._create_training_tables()

    def _create_training_tables(self):
        """创建培训模块表结构"""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS training_employees (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                position TEXT NOT NULL,
                join_date TEXT,
                role TEXT DEFAULT 'employee',
                wecom_openid TEXT DEFAULT '',
                dingtalk_userid TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS training_tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                task_type TEXT NOT NULL,
                content_source TEXT DEFAULT '[]',
                quiz_items TEXT DEFAULT '[]',
                content TEXT DEFAULT '',
                deadline TEXT,
                priority INTEGER DEFAULT 2,
                status TEXT DEFAULT 'draft',
                created_by TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS learning_progress (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                state TEXT DEFAULT 'not_started',
                started_at TEXT,
                completed_at TEXT,
                quiz_score REAL DEFAULT 0.0,
                quiz_attempts INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES training_employees(id),
                FOREIGN KEY (task_id) REFERENCES training_tasks(id)
            );

            CREATE TABLE IF NOT EXISTS quiz_results (
                id TEXT PRIMARY KEY,
                progress_id TEXT NOT NULL,
                employee_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                score REAL NOT NULL,
                passed INTEGER NOT NULL,
                answers TEXT DEFAULT '[]',
                submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (progress_id) REFERENCES learning_progress(id)
            );

            CREATE INDEX IF NOT EXISTS idx_employees_role ON training_employees(role);
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON training_tasks(status);
            CREATE INDEX IF NOT EXISTS idx_progress_employee ON learning_progress(employee_id);
            CREATE INDEX IF NOT EXISTS idx_progress_task ON learning_progress(task_id);
            CREATE INDEX IF NOT EXISTS idx_progress_state ON learning_progress(state);
        """)
        self.conn.commit()

    # ========== 培训模块数据访问 ==========

    def insert_employee(self, employee: dict) -> bool:
        """插入员工"""
        try:
            with self.get_cursor() as c:
                c.execute(
                    """INSERT OR REPLACE INTO training_employees
                       (id, name, department, position, join_date, role, wecom_openid, dingtalk_userid)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (employee['id'], employee['name'], employee['department'],
                     employee['position'], employee.get('join_date', ''),
                     employee.get('role', 'employee'),
                     employee.get('wecom_openid', ''),
                     employee.get('dingtalk_userid', ''))
                )
            return True
        except Exception as e:
            logger.error(f"插入员工失败: {e}")
            return False

    def get_employee(self, employee_id: str) -> Optional[dict]:
        """获取员工"""
        with self.get_cursor() as c:
            c.execute("SELECT * FROM training_employees WHERE id = ?", (employee_id,))
            row = c.fetchone()
            return dict(row) if row else None

    def get_all_employees(self) -> list[dict]:
        """获取所有员工"""
        with self.get_cursor() as c:
            c.execute("SELECT * FROM training_employees ORDER BY created_at DESC")
            return [dict(row) for row in c.fetchall()]

    def insert_training_task(self, task: dict) -> bool:
        """插入培训任务"""
        try:
            with self.get_cursor() as c:
                c.execute(
                    """INSERT OR REPLACE INTO training_tasks
                       (id, title, description, task_type, content_source, quiz_items, content, deadline, priority, status, created_by)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (task['id'], task['title'], task.get('description', ''),
                     task['task_type'], json.dumps(task.get('content_source', [])),
                     json.dumps(task.get('quiz_items', [])), task.get('content', ''),
                     task.get('deadline', ''), task.get('priority', 2),
                     task.get('status', 'draft'), task.get('created_by', ''))
                )
            return True
        except Exception as e:
            logger.error(f"插入培训任务失败: {e}")
            return False

    def get_training_task(self, task_id: str) -> Optional[dict]:
        """获取培训任务"""
        with self.get_cursor() as c:
            c.execute("SELECT * FROM training_tasks WHERE id = ?", (task_id,))
            row = c.fetchone()
            if row:
                result = dict(row)
                # 解析 JSON 字段
                result['content_source'] = json.loads(result.get('content_source', '[]'))
                result['quiz_items'] = json.loads(result.get('quiz_items', '[]'))
                return result
        return None

    def get_all_training_tasks(self, status: str = None) -> list[dict]:
        """获取所有培训任务"""
        with self.get_cursor() as c:
            if status:
                c.execute("SELECT * FROM training_tasks WHERE status = ? ORDER BY created_at DESC", (status,))
            else:
                c.execute("SELECT * FROM training_tasks ORDER BY created_at DESC")
            tasks = []
            for row in c.fetchall():
                result = dict(row)
                result['content_source'] = json.loads(result.get('content_source', '[]'))
                result['quiz_items'] = json.loads(result.get('quiz_items', '[]'))
                tasks.append(result)
            return tasks

    def update_training_task_status(self, task_id: str, status: str) -> bool:
        """更新任务状态"""
        try:
            with self.get_cursor() as c:
                c.execute(
                    "UPDATE training_tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (status, task_id)
                )
            return True
        except Exception as e:
            logger.error(f"更新任务状态失败: {e}")
            return False

    def delete_training_task(self, task_id: str) -> bool:
        """删除任务及其关联数据"""
        try:
            with self.get_cursor() as c:
                # 删除关联的学习进度
                c.execute("DELETE FROM learning_progress WHERE task_id = ?", (task_id,))
                # 删除关联的测验结果
                c.execute("DELETE FROM quiz_results WHERE task_id = ?", (task_id,))
                # 删除任务
                c.execute("DELETE FROM training_tasks WHERE id = ?", (task_id,))
            return True
        except Exception as e:
            logger.error(f"删除任务失败: {e}")
            return False

    def insert_learning_progress(self, progress: dict) -> bool:
        """插入学习进度"""
        try:
            with self.get_cursor() as c:
                c.execute(
                    """INSERT OR REPLACE INTO learning_progress
                       (id, employee_id, task_id, state, started_at, completed_at, quiz_score, quiz_attempts)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (progress['id'], progress['employee_id'], progress['task_id'],
                     progress.get('state', 'not_started'),
                     progress.get('started_at', ''),
                     progress.get('completed_at', ''),
                     progress.get('quiz_score', 0.0),
                     progress.get('quiz_attempts', 0))
                )
            return True
        except Exception as e:
            logger.error(f"插入学习进度失败: {e}")
            return False

    def get_learning_progress(self, progress_id: str) -> Optional[dict]:
        """获取学习进度"""
        with self.get_cursor() as c:
            c.execute("SELECT * FROM learning_progress WHERE id = ?", (progress_id,))
            row = c.fetchone()
            return dict(row) if row else None

    def get_employee_progress(self, employee_id: str) -> list[dict]:
        """获取员工所有学习进度"""
        with self.get_cursor() as c:
            c.execute(
                """SELECT lp.*, tt.title as task_title, tt.task_type, tt.deadline
                   FROM learning_progress lp
                   JOIN training_tasks tt ON lp.task_id = tt.id
                   WHERE lp.employee_id = ?
                   ORDER BY lp.created_at DESC""",
                (employee_id,)
            )
            return [dict(row) for row in c.fetchall()]

    def get_task_progress(self, task_id: str) -> list[dict]:
        """获取任务的所有学习进度"""
        with self.get_cursor() as c:
            c.execute(
                """SELECT lp.*, te.name as employee_name, te.department
                   FROM learning_progress lp
                   JOIN training_employees te ON lp.employee_id = te.id
                   WHERE lp.task_id = ?
                   ORDER BY lp.created_at DESC""",
                (task_id,)
            )
            return [dict(row) for row in c.fetchall()]

    ALLOWED_PROGRESS_KEYS = {'state', 'started_at', 'completed_at', 'quiz_score', 'quiz_attempts'}

    def update_learning_progress(self, progress_id: str, updates: dict) -> bool:
        """更新学习进度"""
        try:
            set_clauses = []
            values = []
            for key in ALLOWED_PROGRESS_KEYS:
                if key in updates:
                    set_clauses.append(f"{key} = ?")
                    values.append(updates[key])
            if not set_clauses:
                return False
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.append(progress_id)

            with self.get_cursor() as c:
                c.execute(
                    f"UPDATE learning_progress SET {', '.join(set_clauses)} WHERE id = ?",
                    values
                )
            return True
        except Exception as e:
            logger.error(f"更新学习进度失败: {e}")
            return False

    def insert_quiz_result(self, result: dict) -> bool:
        """插入测验结果"""
        try:
            with self.get_cursor() as c:
                c.execute(
                    """INSERT INTO quiz_results
                       (id, progress_id, employee_id, task_id, score, passed, answers)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (result['id'], result['progress_id'], result['employee_id'],
                     result['task_id'], result['score'], 1 if result['passed'] else 0,
                     json.dumps(result.get('answers', [])))
                )
            return True
        except Exception as e:
            logger.error(f"插入测验结果失败: {e}")
            return False

    def get_quiz_results(self, progress_id: str) -> list[dict]:
        """获取测验结果"""
        with self.get_cursor() as c:
            c.execute("SELECT * FROM quiz_results WHERE progress_id = ? ORDER BY submitted_at DESC",
                     (progress_id,))
            return [dict(row) for row in c.fetchall()]

    def get_dashboard_stats(self) -> dict:
        """获取看板统计数据"""
        with self.get_cursor() as c:
            # 员工总数
            c.execute("SELECT COUNT(*) as count FROM training_employees")
            total = c.fetchone()['count']

            # 已完成人数
            c.execute("""SELECT COUNT(DISTINCT employee_id) as count FROM learning_progress
                        WHERE state IN ('completed', 'mastered')""")
            completed = c.fetchone()['count']

            # 平均成绩
            c.execute("SELECT AVG(score) as avg FROM quiz_results WHERE passed = 1")
            row = c.fetchone()
            avg_score = row['avg'] if row['avg'] else 0.0

            return {
                'total_employees': total,
                'completed_count': completed,
                'completion_rate': completed / total if total > 0 else 0.0,
                'avg_quiz_score': round(avg_score, 1) if avg_score else 0.0
            }

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
            logger.error(f"插入页面失败: {e}")
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
            logger.error(f"向量索引初始化失败: {e}")
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
            logger.error(f"向量插入失败: {e}")
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
            logger.error(f"向量搜索失败: {e}")
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
