"""제출 기록 저장 (Supabase REST).

테이블 bmi_submissions 는 RLS로 막혀 있고, 요청 헤더 x-app-secret 이 DB에 저장된 값과 같을 때만
읽고 쓸 수 있다. 이 헤더는 서버 함수만 알고 브라우저에는 절대 내려가지 않는다.
"""

import os
from datetime import datetime, timezone

import httpx

TABLE = "bmi_submissions"
LIST_COLUMNS = "id,student_id,name,submitted_at,status,model,result,error,graded_at,teacher"

_client = None


def _http():
    global _client
    if _client is None:
        _client = httpx.Client(
            base_url=os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1",
            headers={
                "apikey": os.environ["SUPABASE_KEY"],
                "x-app-secret": os.environ["APP_SECRET"],
                "Content-Type": "application/json",
            },
            timeout=20,
        )
    return _client


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _request(method, params=None, json=None, prefer=None):
    headers = {"Prefer": prefer} if prefer else None
    response = _http().request(method, f"/{TABLE}", params=params, json=json, headers=headers)
    response.raise_for_status()
    return response.json() if response.content else None


def insert(row):
    return _request("POST", json=row, prefer="return=representation")[0]


def update(submission_id, fields):
    _request("PATCH", params={"id": f"eq.{submission_id}"}, json=fields, prefer="return=minimal")


def delete(submission_id):
    _request("DELETE", params={"id": f"eq.{submission_id}"}, prefer="return=minimal")


def get(submission_id):
    rows = _request("GET", params={"id": f"eq.{submission_id}", "select": "*"})
    return rows[0] if rows else None


def list_all():
    return _request("GET", params={"select": LIST_COLUMNS, "order": "student_id.asc,id.asc"})


def for_student(student_id):
    return _request("GET", params={"student_id": f"eq.{student_id}", "select": "id,name", "order": "id.asc"})
