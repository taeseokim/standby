# 업앤다운 숫자 맞추기 게임 수행평가 – 제출·실시간 채점

학생이 **학번·이름**을 입력하고 업앤다운 게임 프로그램(파이썬 코드)을 제출하면 그 자리에서
① 테스트 입력으로 코드를 실행하고 ② OpenAI API가 「2026 2학기 수행평가 세부 계획 – 업앤다운 숫자 맞추기
게임 프로그램 작성하기」 채점기준으로 채점해 결과를 바로 보여 줍니다. 교사용 화면은 5초마다 자동으로
갱신됩니다. 구조는 `bmi_grader/`와 같습니다.

- 학생 화면: `/`
- 교사 화면: `/teacher.html` (교사 비밀번호 필요)

## 구성

| 부분 | 사용 기술 |
|---|---|
| 화면 | `public/` 정적 HTML (Vercel CDN) |
| API | `api/index.py` FastAPI (Vercel Python 함수) |
| 저장소 | Supabase Postgres `updown_submissions` 테이블 |
| 채점 | OpenAI Chat Completions + JSON 스키마 출력 |

```
updown_grader/
├── api/index.py      # API: 제출, 채점, 교사용 조회·수정
├── lib/rubric.py     # 과제 안내, 채점기준, 정답 범위 (기준을 바꾸려면 여기만 수정)
├── lib/grader.py     # 정답을 고정해 학생 코드 실행 + OpenAI 채점
├── lib/db.py         # Supabase REST 접근
├── public/           # index.html(학생), teacher.html(교사), style.css
├── examples/         # 모범 답안 / 감점 사례 (테스트용)
└── vercel.json
```

## 채점 방식

| 채점 요소 | 배점 | 척도 |
|---|---|---|
| 정답 생성 및 비교 로직 | 10 | 10 / 9 / 8 / 7 / 5 |
| 반복문 제어 및 종료 | 10 | 10 / 9 / 8 / 7 / 5 |
| 시도 횟수 카운트 | 10 | 10 / 9 / 8 / 7 / 5 |
| 예외 처리 및 안정성 | 10 | 10 / 9 / 8 / 7 / 5 |
| 코드 품질 | 10 | 10 / 9 / 8 / 7 / 5 |
| **합계** | **50** | 미제출 15점 |

정답 범위: 1~100 (양 끝 포함)

1. **정답 고정 실행** – 게임은 정답이 무작위라 그대로 실행하면 결과가 매번 다릅니다. 그래서 테스트할 때는
   `random.randint` / `randrange` / `choice`가 정해 둔 정답(예: 37)을 돌려주도록 바꿔 실행합니다.
   학생 코드가 호출한 범위(예: `randint(1, 99)`)도 기록해 범위 오차를 확인합니다.
2. **테스트 입력 8가지** – 기본 진행, 정답 바로 옆 숫자(36·38), 범위 끝 정답(100, 1), 범위 초과 입력(0·101·-5),
   재시작(y, Y), 문자 입력(참고). 각 게임 끝에는 재시작 질문용 `n`을 넣어 두었습니다. (3초 제한, 메모리 제한, 환경변수 차단)
   정답을 맞힌 뒤에도 루프가 돌면 남은 `n`을 숫자로 읽다가 오류가 나므로 무한 루프가 드러납니다.
3. **AI 채점** – 코드 + 실행 결과 + 채점기준을 모델에 보내 요소별 점수(10/9/8/7/5 중 하나만 허용), 근거,
   성취수준(A~E), 학생 피드백을 받습니다. 총점은 프로그램이 직접 합산합니다.
4. **교사 확정** – AI 점수는 1차 채점입니다. 교사 화면에서 확인·수정 후 **점수 확정 저장**을 누르세요.

## 환경변수 (Vercel 프로젝트 → Settings → Environment Variables)

| 이름 | 필수 | 설명 |
|---|---|---|
| `OPENAI_API_KEY` | ✔ | OpenAI API 키 |
| `TEACHER_PASSWORD` | ✔ | 교사 화면 비밀번호 |
| `SUPABASE_URL` | ✔ | Supabase 프로젝트 URL |
| `SUPABASE_KEY` | ✔ | Supabase publishable 키 |
| `APP_SECRET` | ✔ | DB 접근용 비밀값 (`private.app_config`의 `updown_app_secret`과 같아야 함) |
| `OPENAI_MODEL` | | 채점 모델 (기본 `gpt-5-mini`) |
| `MAX_SUBMISSIONS` | | 학생 1명당 제출 가능 횟수 (기본 1) |
| `SHOW_RESULT_TO_STUDENT` | | 제출 직후 학생에게 점수·피드백 표시 (기본 true) |
| `ACCESS_CODE` | | 설정하면 학생이 제출할 때 이 수업 코드를 입력해야 함 |
| `STUDENT_ID_PATTERN` | | 학번 형식 정규식 (기본 `^\d{4,8}$`) |

환경변수를 바꾼 뒤에는 Vercel에서 **Redeploy** 해야 적용됩니다.

## DB 스키마 (Supabase, BMI 채점기와 같은 프로젝트)

```sql
create table public.updown_submissions (
    id bigint generated always as identity primary key,
    student_id text not null, name text not null, code text not null,
    submitted_at timestamptz not null default now(),
    status text not null default 'running',  -- running / grading / graded / error
    model text, tests jsonb, run_log text, result jsonb, error text,
    graded_at timestamptz, teacher jsonb
);
create function private.has_updown_secret() returns boolean
language sql stable security definer set search_path = '' as $$
    select coalesce(current_setting('request.headers', true)::json ->> 'x-app-secret', '')
           = coalesce((select value from private.app_config where key = 'updown_app_secret'), '-')
$$;
revoke all on function private.has_updown_secret() from public;
grant execute on function private.has_updown_secret() to anon;
alter table public.updown_submissions enable row level security;
revoke all on public.updown_submissions from authenticated;
create policy "app server only" on public.updown_submissions for all to anon
    using (private.has_updown_secret()) with check (private.has_updown_secret());
-- insert into private.app_config values ('updown_app_secret', '<APP_SECRET 값>');
```

BMI 채점기와 비밀값을 따로 두어, 한쪽 비밀값이 바뀌어도 다른 쪽에 영향이 없습니다.

## 로컬에서 실행

```bash
cd updown_grader
pip install -r requirements.txt uvicorn
export OPENAI_API_KEY=... TEACHER_PASSWORD=... SUPABASE_URL=... SUPABASE_KEY=... APP_SECRET=...
uvicorn api.index:app --reload      # http://localhost:8000
```
