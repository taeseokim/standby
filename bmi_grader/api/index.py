"""BMI 수행평가 제출·실시간 채점 API (Vercel Python 함수, FastAPI).

학생: POST /api/submit (저장 + 테스트 실행) → POST /api/grade (AI 채점)
교사: /api/teacher/... (x-teacher-password 헤더 필요)
"""

import hmac
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import Depends, FastAPI, Header, HTTPException  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from lib import db  # noqa: E402
from lib.grader import format_run_log, grade, run_student_code, run_tests  # noqa: E402
from lib.rubric import (  # noqa: E402
    ACHIEVEMENT_LEVELS,
    ASSIGNMENT_STEPS,
    ASSIGNMENT_TITLE,
    BMI_STAGES,
    CRITERIA,
    CRITERIA_KEYS,
    MAX_SCORE,
    NO_SUBMISSION_SCORE,
)

OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5-mini")
TEACHER_PASSWORD = os.environ.get("TEACHER_PASSWORD", "")
ACCESS_CODE = os.environ.get("ACCESS_CODE", "")  # 설정하면 학생이 제출할 때 입력해야 하는 수업 코드
MAX_SUBMISSIONS = int(os.environ.get("MAX_SUBMISSIONS", "1"))
SHOW_RESULT_TO_STUDENT = os.environ.get("SHOW_RESULT_TO_STUDENT", "true").lower() in ("1", "true", "yes", "on")
STUDENT_ID_PATTERN = os.environ.get("STUDENT_ID_PATTERN", r"^\d{4,8}$")
MAX_CODE_CHARS = 20000

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

_openai = None


def openai_client():
    global _openai
    if _openai is None:
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")
        from openai import OpenAI

        _openai = OpenAI(timeout=100, max_retries=1)
    return _openai


def grade_and_save(row):
    """AI 채점 후 저장. 성공하면 결과, 실패하면 None."""
    try:
        result = grade(row["code"], row["run_log"], openai_client(), OPENAI_MODEL)
    except Exception as exc:  # API·네트워크 오류는 기록해 두고 교사 화면에서 재채점한다.
        db.update(row["id"], {"status": "error", "model": OPENAI_MODEL, "error": f"{type(exc).__name__}: {exc}",
                              "graded_at": db.now_iso()})
        return None
    db.update(row["id"], {"status": "graded", "model": OPENAI_MODEL, "result": result, "error": None,
                          "graded_at": db.now_iso()})
    return result


def student_view(result):
    """학생에게 보여줄 부분만 (교사용 메모 제외)."""
    return {
        "total": result["total"],
        "achievement_level": result["achievement_level"],
        "criteria": {key: result[key] for key in CRITERIA_KEYS},
        "student_feedback": result["student_feedback"],
    }


# ---------------------------------------------------------------- 공개
@app.get("/api/config")
def config():
    return {
        "title": ASSIGNMENT_TITLE,
        "steps": ASSIGNMENT_STEPS,
        "stages": [{"upper": upper, "name": name} for upper, name in BMI_STAGES],
        "criteria": [{"key": key, "name": name, "levels": levels} for key, name, levels in CRITERIA],
        "achievement_levels": list(ACHIEVEMENT_LEVELS),
        "max_score": MAX_SCORE,
        "no_submission_score": NO_SUBMISSION_SCORE,
        "max_submissions": MAX_SUBMISSIONS,
        "show_result": SHOW_RESULT_TO_STUDENT,
        "access_code_required": bool(ACCESS_CODE),
    }


@app.get("/api/health")
def health():
    """배포 상태 확인: DB 연결, 학생 코드 실행기, OpenAI 키 설정 여부."""
    try:
        db.ping()
        database = "ok"
    except Exception as exc:
        database = f"error: {type(exc).__name__}"
    try:
        run = run_student_code("print(float(input()) * 2)", "1.5\n")
        runner = "ok" if run["ok"] and run["output"].strip() == "3.0" else f"error: {run['status']} {run['output'][:200]}"
    except Exception as exc:
        runner = f"error: {type(exc).__name__}: {exc}"
    return {"database": database, "code_runner": runner, "openai_key": bool(os.environ.get("OPENAI_API_KEY")),
            "model": OPENAI_MODEL}


class SubmitIn(BaseModel):
    student_id: str
    name: str
    code: str
    access_code: str = ""


@app.post("/api/submit")
def submit(body: SubmitIn):
    student_id, name, code = body.student_id.strip(), body.name.strip(), body.code
    if ACCESS_CODE and not hmac.compare_digest(body.access_code.strip(), ACCESS_CODE):
        raise HTTPException(400, "수업 코드가 틀렸습니다. 선생님께 확인하세요.")
    if not re.fullmatch(STUDENT_ID_PATTERN, student_id):
        raise HTTPException(400, "학번을 숫자로 정확히 입력하세요.")
    if not name or len(name) > 20:
        raise HTTPException(400, "이름을 정확히 입력하세요.")
    if not code.strip():
        raise HTTPException(400, "제출할 코드가 비어 있습니다.")
    if len(code) > MAX_CODE_CHARS:
        raise HTTPException(400, f"코드가 너무 깁니다. ({MAX_CODE_CHARS:,}자 이하)")
    previous = db.for_student(student_id)
    if previous and previous[0]["name"] != name:
        raise HTTPException(400, "이 학번으로 이미 다른 이름의 제출 기록이 있습니다. 학번과 이름을 확인하고, 문제가 있으면 선생님께 말씀하세요.")
    if len(previous) >= MAX_SUBMISSIONS:
        raise HTTPException(400, f"제출 가능 횟수({MAX_SUBMISSIONS}회)를 모두 사용했습니다.")

    row = db.insert({"student_id": student_id, "name": name, "code": code, "status": "running"})
    tests = run_tests(code)
    db.update(row["id"], {"status": "grading", "tests": tests, "run_log": format_run_log(tests)})
    return {
        "id": row["id"],
        "tests": [{k: t[k] for k in ("name", "input", "expect", "status", "output", "match")} for t in tests],
    }


class GradeIn(BaseModel):
    id: int


@app.post("/api/grade")
def grade_submission(body: GradeIn):
    row = db.get(body.id)
    if not row or row["status"] != "grading":  # 이미 채점된 제출은 다시 볼 수 없게 한다.
        raise HTTPException(409, "채점할 수 없는 제출입니다.")
    result = grade_and_save(row)
    if result is None:
        return {"ok": False}
    return {"ok": True, "result": student_view(result) if SHOW_RESULT_TO_STUDENT else None}


# ---------------------------------------------------------------- 교사
def require_teacher(x_teacher_password: str = Header(default="")):
    if not TEACHER_PASSWORD:
        raise HTTPException(503, "TEACHER_PASSWORD가 설정되지 않았습니다.")
    if not hmac.compare_digest(x_teacher_password.encode(), TEACHER_PASSWORD.encode()):
        raise HTTPException(401, "비밀번호가 틀렸습니다.")


@app.get("/api/teacher/submissions", dependencies=[Depends(require_teacher)])
def teacher_list():
    return {
        "submissions": db.list_all(),
        "model": OPENAI_MODEL,
        "openai_ready": bool(os.environ.get("OPENAI_API_KEY")),
    }


@app.get("/api/teacher/submissions/{submission_id}", dependencies=[Depends(require_teacher)])
def teacher_get(submission_id: int):
    row = db.get(submission_id)
    if not row:
        raise HTTPException(404, "없는 제출입니다.")
    return row


@app.post("/api/teacher/submissions/{submission_id}/regrade", dependencies=[Depends(require_teacher)])
def teacher_regrade(submission_id: int):
    row = db.get(submission_id)
    if not row:
        raise HTTPException(404, "없는 제출입니다.")
    if not row["run_log"]:  # 테스트 실행 도중 끊긴 제출
        tests = run_tests(row["code"])
        row["tests"], row["run_log"] = tests, format_run_log(tests)
        db.update(submission_id, {"tests": tests, "run_log": row["run_log"]})
    db.update(submission_id, {"status": "grading"})
    result = grade_and_save(row)
    return {"ok": result is not None}


class TeacherScoresIn(BaseModel):
    scores: dict[str, int] | None = None  # None이면 교사 확정 취소
    level: str = ""
    note: str = ""


@app.put("/api/teacher/submissions/{submission_id}/teacher", dependencies=[Depends(require_teacher)])
def teacher_scores(submission_id: int, body: TeacherScoresIn):
    if body.scores is None:
        db.update(submission_id, {"teacher": None})
        return {"ok": True}
    allowed = {key: [score for score, _ in levels] for key, _, levels in CRITERIA}
    for key in CRITERIA_KEYS:
        if body.scores.get(key) not in allowed[key]:
            raise HTTPException(400, f"{key} 점수가 올바르지 않습니다.")
    if body.level not in ACHIEVEMENT_LEVELS:
        raise HTTPException(400, "성취수준이 올바르지 않습니다.")
    teacher = {**{key: body.scores[key] for key in CRITERIA_KEYS}, "level": body.level, "note": body.note[:500]}
    db.update(submission_id, {"teacher": teacher})
    return {"ok": True}


@app.delete("/api/teacher/submissions/{submission_id}", dependencies=[Depends(require_teacher)])
def teacher_delete(submission_id: int):
    db.delete(submission_id)
    return {"ok": True}


# 로컬 개발용: `uvicorn api.index:app` 으로 띄우면 public/ 도 함께 서비스한다. (Vercel에서는 CDN이 서비스)
if not os.environ.get("VERCEL"):
    from fastapi.staticfiles import StaticFiles

    _public = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
    app.mount("/", StaticFiles(directory=_public, html=True), name="public")
