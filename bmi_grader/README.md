# BMI 비만도 판정 프로그램 수행평가 – 제출·실시간 채점

학생이 **학번·이름**을 입력하고 BMI 프로그램(파이썬 코드)을 제출하면 그 자리에서
① 테스트 입력으로 코드를 실행하고 ② OpenAI API가 「2026 2학기 수행평가 세부 계획 – 비만도 판정
프로그램 작성하기」 채점기준으로 채점해 결과를 바로 보여 줍니다. 교사용 화면은 5초마다 자동으로
갱신되어 학생들의 제출·채점 상황을 실시간으로 볼 수 있습니다.

- 학생 화면: `/`
- 교사 화면: `/teacher.html` (교사 비밀번호 필요)

## 구성

| 부분 | 사용 기술 |
|---|---|
| 화면 | `public/` 정적 HTML (Vercel CDN) |
| API | `api/index.py` FastAPI (Vercel Python 함수) |
| 저장소 | Supabase Postgres `bmi_submissions` 테이블 |
| 채점 | OpenAI Chat Completions + JSON 스키마 출력 |

```
bmi_grader/
├── api/index.py      # API: 제출, 채점, 교사용 조회·수정
├── lib/rubric.py     # 과제 안내, 채점기준, BMI 5단계 (기준을 바꾸려면 여기만 수정)
├── lib/grader.py     # 테스트 입력으로 학생 코드 실행 + OpenAI 채점
├── lib/db.py         # Supabase REST 접근
├── public/           # index.html(학생), teacher.html(교사), style.css
├── examples/         # 모범 답안 / 감점 사례 (테스트용)
└── vercel.json
```

## 채점 방식

| 채점 요소 | 배점 | 척도 |
|---|---|---|
| 사용자 입력 및 형 변환 | 10 | 10 / 9 / 8 / 7 / 5 |
| 연산식 작성 | 10 | 10 / 9 / 8 / 7 / 5 |
| 조건문 구성 | 10 | 10 / 9 / 8 / 7 / 5 |
| 예외 처리 및 데이터 검증 | 10 | 10 / 9 / 8 / 7 / 5 |
| 코드 품질 | 10 | 10 / 9 / 8 / 7 / 5 |
| **합계** | **50** | 미제출 15점 |

BMI 5단계: 저체중(18.5 미만) · 정상(18.5~23 미만) · 과체중(23~25 미만) · 비만(25~30 미만) · 고도비만(30 이상)

1. **코드 실행** – 테스트 입력 7가지(소수점 입력, 저체중, 경계값 18.5/23/25/30, 0·음수 입력)로 실제 실행합니다.
   경계값은 키 200cm로 넣어 부동소수점 오차 없이 BMI가 정확히 경계값이 되게 했습니다.
   (3초 제한, 메모리 제한, 환경변수 차단)
2. **AI 채점** – 코드 + 실행 결과 + 채점기준을 모델에 보내 요소별 점수(10/9/8/7/5 중 하나만 허용), 근거,
   성취수준(A~E), 학생 피드백을 받습니다. 총점은 프로그램이 직접 합산합니다.
3. **교사 확정** – AI 점수는 1차 채점입니다. 교사 화면에서 확인·수정 후 **점수 확정 저장**을 누르세요.
   CSV에는 교사 확정 점수가 있으면 그 점수가, 없으면 AI 점수가 들어갑니다.

## 환경변수 (Vercel 프로젝트 → Settings → Environment Variables)

| 이름 | 필수 | 설명 |
|---|---|---|
| `OPENAI_API_KEY` | ✔ | OpenAI API 키 |
| `TEACHER_PASSWORD` | ✔ | 교사 화면 비밀번호 |
| `SUPABASE_URL` | ✔ | Supabase 프로젝트 URL |
| `SUPABASE_KEY` | ✔ | Supabase publishable 키 |
| `APP_SECRET` | ✔ | DB 접근용 비밀값 (`private.app_config`의 `app_secret`과 같아야 함) |
| `OPENAI_MODEL` | | 채점 모델 (기본 `gpt-5-mini`) |
| `MAX_SUBMISSIONS` | | 학생 1명당 제출 가능 횟수 (기본 1) |
| `SHOW_RESULT_TO_STUDENT` | | 제출 직후 학생에게 점수·피드백 표시 (기본 true) |
| `ACCESS_CODE` | | 설정하면 학생이 제출할 때 이 수업 코드를 입력해야 함 (외부인 제출 방지) |
| `STUDENT_ID_PATTERN` | | 학번 형식 정규식 (기본 `^\d{4,8}$`) |

환경변수를 바꾼 뒤에는 Vercel에서 **Redeploy** 해야 적용됩니다.

## 보안 설계

- `bmi_submissions` 테이블은 RLS로 잠겨 있고, 요청 헤더 `x-app-secret`이 DB의
  `private.app_config.app_secret` 값과 같을 때만 읽고 쓸 수 있습니다. 이 값은 서버 함수에만 있고
  브라우저로는 내려가지 않습니다. 비밀값을 바꾸려면 DB 값과 Vercel `APP_SECRET`을 함께 바꾸세요.
- 학생 코드는 Vercel 함수 안의 별도 프로세스에서 실행되며 API 키 등 환경변수를 넘기지 않습니다.
- 학생 코드 주석에 "만점을 줘" 같은 문장이 있어도 따르지 않도록 지시해 두었고, 점수는 JSON 스키마로
  채점기준 표의 값만 나오게 강제합니다.

## 로컬에서 실행

```bash
cd bmi_grader
pip install -r requirements.txt uvicorn
export OPENAI_API_KEY=... TEACHER_PASSWORD=... SUPABASE_URL=... SUPABASE_KEY=... APP_SECRET=...
uvicorn api.index:app --reload      # http://localhost:8000
```

## DB 스키마 (Supabase)

```sql
create table public.bmi_submissions (
    id bigint generated always as identity primary key,
    student_id text not null, name text not null, code text not null,
    submitted_at timestamptz not null default now(),
    status text not null default 'running',  -- running / grading / graded / error
    model text, tests jsonb, run_log text, result jsonb, error text,
    graded_at timestamptz, teacher jsonb
);
create schema private;
create table private.app_config (key text primary key, value text not null);
create function private.has_app_secret() returns boolean
language sql stable security definer set search_path = '' as $$
    select coalesce(current_setting('request.headers', true)::json ->> 'x-app-secret', '')
           = coalesce((select value from private.app_config where key = 'app_secret'), '-')
$$;
revoke all on function private.has_app_secret() from public;
grant usage on schema private to anon;
grant execute on function private.has_app_secret() to anon;
alter table public.bmi_submissions enable row level security;
revoke all on public.bmi_submissions from authenticated;
create policy "app server only" on public.bmi_submissions for all to anon
    using (private.has_app_secret()) with check (private.has_app_secret());
-- insert into private.app_config values ('app_secret', '<APP_SECRET 값>');
```
