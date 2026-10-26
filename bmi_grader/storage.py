"""제출 기록 저장 (SQLite)."""

import json
import sqlite3
from datetime import datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    name TEXT NOT NULL,
    code TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending / graded / error
    model TEXT,
    result_json TEXT,
    run_log TEXT,
    error TEXT,
    graded_at TEXT,
    teacher_json TEXT  -- 교사가 확정·수정한 점수 {key: score, ..., "note": str}
);
CREATE INDEX IF NOT EXISTS idx_submissions_student ON submissions(student_id);
"""


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Storage:
    def __init__(self, path):
        self.path = path
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def _connect(self):
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def add_submission(self, student_id, name, code):
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO submissions (student_id, name, code, submitted_at) VALUES (?, ?, ?, ?)",
                (student_id, name, code, _now()),
            )
            return cur.lastrowid

    def save_result(self, submission_id, model, result, run_log):
        with self._connect() as conn:
            conn.execute(
                "UPDATE submissions SET status='graded', model=?, result_json=?, run_log=?, error=NULL, graded_at=? "
                "WHERE id=?",
                (model, json.dumps(result, ensure_ascii=False), run_log, _now(), submission_id),
            )

    def save_error(self, submission_id, model, error):
        with self._connect() as conn:
            conn.execute(
                "UPDATE submissions SET status='error', model=?, error=?, graded_at=? WHERE id=?",
                (model, error, _now(), submission_id),
            )

    def save_teacher_scores(self, submission_id, teacher):
        with self._connect() as conn:
            conn.execute(
                "UPDATE submissions SET teacher_json=? WHERE id=?",
                (json.dumps(teacher, ensure_ascii=False) if teacher else None, submission_id),
            )

    def delete_submission(self, submission_id):
        with self._connect() as conn:
            conn.execute("DELETE FROM submissions WHERE id=?", (submission_id,))

    def count_for_student(self, student_id):
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM submissions WHERE student_id=?", (student_id,)).fetchone()
            return row[0]

    def name_for_student(self, student_id):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT name FROM submissions WHERE student_id=? ORDER BY id LIMIT 1", (student_id,)
            ).fetchone()
            return row["name"] if row else None

    def get(self, submission_id):
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM submissions WHERE id=?", (submission_id,)).fetchone()
            return _decode(row) if row else None

    def all(self):
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM submissions ORDER BY student_id, id").fetchall()
            return [_decode(r) for r in rows]

    def latest_per_student(self):
        """학생별 가장 최근 제출만."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM submissions WHERE id IN (SELECT MAX(id) FROM submissions GROUP BY student_id) "
                "ORDER BY student_id"
            ).fetchall()
            return [_decode(r) for r in rows]


def _decode(row):
    item = dict(row)
    item["result"] = json.loads(item["result_json"]) if item["result_json"] else None
    item["teacher"] = json.loads(item["teacher_json"]) if item["teacher_json"] else None
    return item
