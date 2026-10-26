"""BMI 비만도 판정 프로그램 수행평가 제출·자동채점 (Streamlit).

실행: streamlit run app.py
"""

import io
import os
import re

import pandas as pd
import streamlit as st

from grader import build_run_log, criteria_levels, grade, total_score
from rubric import (
    ACHIEVEMENT_LEVELS,
    ASSIGNMENT_TEXT,
    CRITERIA_KEYS,
    CRITERIA_NAMES,
    MAX_SCORE,
    NO_SUBMISSION_SCORE,
)
from storage import Storage

MAX_CODE_CHARS = 20000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def setting(name, default=None):
    """환경변수 → .streamlit/secrets.toml 순서로 설정값을 읽는다."""
    value = os.environ.get(name)
    if value:
        return value
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def setting_bool(name, default):
    value = setting(name)
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


OPENAI_MODEL = setting("OPENAI_MODEL", "gpt-5-mini")
TEACHER_PASSWORD = setting("TEACHER_PASSWORD")
MAX_SUBMISSIONS = int(setting("MAX_SUBMISSIONS", 1))  # 학생 1명당 제출 가능 횟수
SHOW_RESULT_TO_STUDENT = setting_bool("SHOW_RESULT_TO_STUDENT", True)
RUN_STUDENT_CODE = setting_bool("RUN_STUDENT_CODE", True)
STUDENT_ID_PATTERN = setting("STUDENT_ID_PATTERN", r"^\d{4,8}$")
DB_PATH = setting("DB_PATH", os.path.join(BASE_DIR, "submissions.db"))


@st.cache_resource
def get_storage():
    return Storage(DB_PATH)


@st.cache_resource
def get_client():
    from openai import OpenAI

    api_key = setting("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def grade_and_save(storage, submission_id, code):
    """채점하고 결과를 저장한다. 성공하면 결과 dict, 실패하면 None."""
    client = get_client()
    if client is None:
        storage.save_error(submission_id, OPENAI_MODEL, "OPENAI_API_KEY가 설정되지 않았습니다.")
        return None
    try:
        graded = grade(code, client, OPENAI_MODEL, run_code=RUN_STUDENT_CODE)
    except Exception as exc:  # API 오류·네트워크 오류 등은 기록해 두고 교사 화면에서 재채점한다.
        storage.save_error(submission_id, OPENAI_MODEL, f"{type(exc).__name__}: {exc}")
        return None
    storage.save_result(submission_id, OPENAI_MODEL, graded["result"], graded["run_log"])
    return graded["result"]


def final_scores(item):
    """교사 확정 점수가 있으면 그것을, 없으면 AI 점수를 쓴다. {key: score}"""
    if item["teacher"]:
        return {key: item["teacher"][key] for key in CRITERIA_KEYS}
    if item["result"]:
        return {key: item["result"][key]["score"] for key in CRITERIA_KEYS}
    return None


def show_result(result, show_teacher_notes=False):
    rows = [
        {"채점 요소": CRITERIA_NAMES[key], "점수": f"{result[key]['score']} / 10", "근거": result[key]["reason"]}
        for key in CRITERIA_KEYS
    ]
    col1, col2 = st.columns(2)
    col1.metric("총점", f"{result['total']} / {MAX_SCORE}")
    col2.metric("성취수준", result["achievement_level"])
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.info(result["student_feedback"])
    if show_teacher_notes:
        st.markdown(f"**잘한 점**: {result['strengths']}")
        st.markdown(f"**보완할 점**: {result['improvements']}")


def read_uploaded_code(uploaded):
    raw = uploaded.getvalue()
    for encoding in ("utf-8-sig", "cp949"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


# ---------------------------------------------------------------- 학생 화면
def student_page():
    storage = get_storage()
    st.title("📏 BMI 비만도 판정 프로그램 수행평가")
    with st.expander("과제 안내 (먼저 읽어 보세요)", expanded=True):
        st.markdown(ASSIGNMENT_TEXT)
        st.caption(
            f"채점: 사용자 입력 및 형 변환 · 연산식 작성 · 조건문 구성 · 예외 처리 및 데이터 검증 · 코드 품질 "
            f"(각 10점, 총 {MAX_SCORE}점) / 제출 가능 횟수: {MAX_SUBMISSIONS}회"
        )

    with st.form("submit_form"):
        col1, col2 = st.columns(2)
        student_id = col1.text_input("학번", placeholder="예: 20315").strip()
        name = col2.text_input("이름", placeholder="예: 홍길동").strip()
        uploaded = st.file_uploader("파이썬 파일(.py) 올리기 — 또는 아래 칸에 코드를 붙여 넣으세요", type=["py"])
        pasted = st.text_area("코드 붙여넣기", height=360, placeholder="# 여기에 작성한 파이썬 코드를 붙여 넣으세요")
        agree = st.checkbox("본인이 직접 작성한 코드이며, 제출 후에는 수정할 수 없음을 확인합니다.")
        submitted = st.form_submit_button("제출하기", type="primary")

    if not submitted:
        return

    code = read_uploaded_code(uploaded) if uploaded else pasted
    errors = []
    if not re.fullmatch(STUDENT_ID_PATTERN, student_id):
        errors.append("학번을 숫자로 정확히 입력하세요.")
    if not name:
        errors.append("이름을 입력하세요.")
    if code is None:
        errors.append("파일 글자 인코딩을 읽을 수 없습니다. UTF-8로 저장해서 다시 올려 주세요.")
    elif not code.strip():
        errors.append("제출할 코드가 비어 있습니다.")
    elif len(code) > MAX_CODE_CHARS:
        errors.append(f"코드가 너무 깁니다. ({MAX_CODE_CHARS:,}자 이하)")
    if not agree:
        errors.append("확인 항목에 체크하세요.")
    if not errors:
        previous_name = storage.name_for_student(student_id)
        if previous_name and previous_name != name:
            errors.append("이 학번으로 이미 다른 이름의 제출 기록이 있습니다. 학번과 이름을 확인하고, 문제가 있으면 선생님께 말씀하세요.")
        elif storage.count_for_student(student_id) >= MAX_SUBMISSIONS:
            errors.append(f"제출 가능 횟수({MAX_SUBMISSIONS}회)를 모두 사용했습니다.")
    if errors:
        for message in errors:
            st.error(message)
        return

    submission_id = storage.add_submission(student_id, name, code)
    with st.spinner("제출되었습니다. 채점 중입니다... (30초 정도 걸릴 수 있어요)"):
        result = grade_and_save(storage, submission_id, code)

    st.success(f"{student_id} {name} 학생, 제출이 완료되었습니다.")
    if result is None:
        st.warning("자동 채점 중 문제가 생겼습니다. 제출은 정상 저장되었으니 선생님이 다시 채점합니다.")
    elif SHOW_RESULT_TO_STUDENT:
        st.subheader("채점 결과 (AI 1차 채점 · 최종 점수는 선생님 확인 후 확정)")
        show_result(result)
    else:
        st.info("채점 결과는 선생님 확인 후 안내됩니다.")


# ---------------------------------------------------------------- 교사 화면
def build_table(items, roster):
    rows = []
    for item in items:
        scores = final_scores(item)
        row = {"제출번호": item["id"], "학번": item["student_id"], "이름": item["name"], "제출시각": item["submitted_at"]}
        for key in CRITERIA_KEYS:
            row[CRITERIA_NAMES[key]] = scores[key] if scores else None
        row["총점"] = total_score(scores) if scores else None
        row["성취수준"] = (item["teacher"] or {}).get("level") or (item["result"] or {}).get("achievement_level")
        row["상태"] = {"graded": "채점완료", "error": "오류", "pending": "채점대기"}[item["status"]]
        row["교사확정"] = "O" if item["teacher"] else ""
        row["교사메모"] = (item["teacher"] or {}).get("note", "")
        rows.append(row)
    submitted_ids = {item["student_id"] for item in items}
    for student_id, name in roster:
        if student_id not in submitted_ids:
            rows.append({"학번": student_id, "이름": name, "총점": NO_SUBMISSION_SCORE, "상태": "미제출"})
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["학번", "제출번호"], na_position="last").reset_index(drop=True)
    return df


def parse_roster(text):
    roster = []
    for line in text.splitlines():
        parts = [p.strip() for p in re.split(r"[,\t]", line) if p.strip()]
        if parts and parts[0].isdigit():
            roster.append((parts[0], parts[1] if len(parts) > 1 else ""))
    return roster


def teacher_page():
    storage = get_storage()
    st.title("🧑‍🏫 교사용 채점 관리")
    if not TEACHER_PASSWORD:
        st.error("TEACHER_PASSWORD가 설정되지 않아 교사 화면을 열 수 없습니다. README를 참고해 설정하세요.")
        return
    if not st.session_state.get("teacher_ok"):
        password = st.text_input("교사 비밀번호", type="password")
        if st.button("로그인"):
            if password == TEACHER_PASSWORD:
                st.session_state.teacher_ok = True
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")
        return

    if get_client() is None:
        st.warning("OPENAI_API_KEY가 설정되지 않아 자동 채점이 동작하지 않습니다.")
    st.caption(f"채점 모델: {OPENAI_MODEL} · 학생당 제출 {MAX_SUBMISSIONS}회 · 코드 실행 {'켜짐' if RUN_STUDENT_CODE else '꺼짐'}")

    show_all = st.toggle("모든 제출 보기 (끄면 학생별 최근 제출만)", value=False)
    items = storage.all() if show_all else storage.latest_per_student()

    with st.expander("학생 명단 (미제출자 확인용, 선택)"):
        roster_text = st.text_area(
            "한 줄에 '학번,이름' 형식으로 붙여 넣으세요. 엑셀에서 두 열을 복사해 붙여 넣어도 됩니다.",
            key="roster", height=150,
        )
    roster = parse_roster(roster_text)
    df = build_table(items, roster)

    graded = [i for i in items if i["status"] == "graded"]
    failed = [i for i in items if i["status"] != "graded"]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("제출 학생", len({i["student_id"] for i in items}))
    col2.metric("채점 완료", len(graded))
    col3.metric("오류/대기", len(failed))
    scores = [total_score(final_scores(i)) for i in graded]
    col4.metric("평균 점수", f"{sum(scores) / len(scores):.1f}" if scores else "-")

    st.dataframe(df, hide_index=True, use_container_width=True)

    col1, col2 = st.columns(2)
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    col1.download_button(
        "CSV 내려받기 (엑셀용)", buffer.getvalue().encode("utf-8-sig"), "bmi_수행평가_결과.csv", "text/csv"
    )
    if failed and col2.button(f"오류/대기 {len(failed)}건 다시 채점"):
        progress = st.progress(0.0)
        for n, item in enumerate(failed, start=1):
            grade_and_save(storage, item["id"], item["code"])
            progress.progress(n / len(failed))
        st.rerun()

    if not items:
        return
    st.divider()
    st.subheader("제출물 상세")
    options = {f"#{i['id']} {i['student_id']} {i['name']} ({i['submitted_at']})": i["id"] for i in items}
    item = storage.get(options[st.selectbox("제출물 선택", list(options))])

    st.code(item["code"], language="python")
    if item["status"] == "error":
        st.error(f"채점 오류: {item['error']}")
    if item["result"]:
        st.markdown("#### AI 채점 결과")
        show_result(item["result"], show_teacher_notes=True)
    with st.expander("테스트 실행 결과"):
        st.text(item["run_log"] or build_run_log(item["code"]))

    st.markdown("#### 교사 확정 점수")
    current = final_scores(item) or {key: 10 for key in CRITERIA_KEYS}
    with st.form(f"teacher_form_{item['id']}"):
        teacher = {}
        cols = st.columns(len(CRITERIA_KEYS))
        for col, key in zip(cols, CRITERIA_KEYS):
            levels = criteria_levels(key)
            score_options = [score for score, _ in levels]
            teacher[key] = col.selectbox(
                CRITERIA_NAMES[key], score_options, index=score_options.index(current[key]),
                help="\n".join(f"{s}점: {d}" for s, d in levels),
            )
        level_options = list(ACHIEVEMENT_LEVELS)
        current_level = (item["teacher"] or {}).get("level") or (item["result"] or {}).get("achievement_level") or "A"
        teacher["level"] = st.selectbox("성취수준", level_options, index=level_options.index(current_level))
        teacher["note"] = st.text_input("메모", value=(item["teacher"] or {}).get("note", ""))
        if st.form_submit_button("점수 확정 저장", type="primary"):
            storage.save_teacher_scores(item["id"], teacher)
            st.success(f"저장했습니다. 총점 {total_score(teacher)}점")
            st.rerun()

    col1, col2, col3 = st.columns(3)
    if col1.button("AI로 다시 채점"):
        with st.spinner("채점 중..."):
            grade_and_save(storage, item["id"], item["code"])
        st.rerun()
    if item["teacher"] and col2.button("교사 확정 취소"):
        storage.save_teacher_scores(item["id"], None)
        st.rerun()
    if col3.button("이 제출 삭제 (재제출 허용)"):
        st.session_state.confirm_delete = item["id"]
    if st.session_state.get("confirm_delete") == item["id"]:
        st.warning("정말 삭제할까요? 되돌릴 수 없습니다.")
        if st.button("삭제 확인", type="primary"):
            storage.delete_submission(item["id"])
            st.session_state.confirm_delete = None
            st.rerun()


def main():
    st.set_page_config(page_title="BMI 수행평가", page_icon="📏", layout="wide")
    page = st.sidebar.radio("화면", ["학생 제출", "교사용"])
    if page == "학생 제출":
        student_page()
    else:
        teacher_page()


main()
