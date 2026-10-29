# ============================================================
# 업앤다운 숫자 맞추기 게임 — 예시 답안 B (우수)
# 예상 점수: 48점 / 50점
#   정답 생성 및 비교 로직 10 | 반복문 제어 및 종료 10 | 시도 횟수 카운트 10
#   예외 처리 및 안정성 9  ← 범위 밖 입력도 시도 횟수에 더함
#   코드 품질 9            ← 재시작할 때 대문자 Y만 받음, 주석이 적음
# ============================================================
import random

print("=== 업앤다운 게임 ===")

while True:
    answer = random.randint(1, 100)
    count = 0

    while True:
        guess = int(input("1~100 사이 숫자를 입력하세요: "))
        count += 1  # 범위 검사 전에 횟수를 더해서, 잘못된 입력도 횟수에 들어감

        if guess < 1 or guess > 100:
            print("1부터 100까지만 입력할 수 있어요.")
            continue

        if guess < answer:
            print("UP")
        elif guess > answer:
            print("DOWN")
        else:
            print(f"정답! {count}번 만에 맞혔어요.")
            break

    again = input("다시 할까요? (Y/N): ")
    if again != "Y":
        print("게임 끝!")
        break
