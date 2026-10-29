# ============================================================
# 업앤다운 숫자 맞추기 게임 — 예시 답안 D (미흡)
# 예상 점수: 35점 / 50점
#   정답 생성 및 비교 로직 7 ← UP과 DOWN이 반대로 출력됨
#   반복문 제어 및 종료 8    ← 정답을 맞혀도 break가 없어 계속 반복됨
#   시도 횟수 카운트 8       ← 반복문 안에서 count = 0으로 다시 초기화됨
#   예외 처리 및 안정성 5    ← 범위 검사가 전혀 없음
#   코드 품질 7              ← 입력 안내 문구와 주석이 없음
# ============================================================
import random

answer = random.randint(1, 100)

while True:
    count = 0
    guess = int(input())
    count += 1
    if guess > answer:
        print("UP")
    elif guess < answer:
        print("DOWN")
    else:
        print("정답", count, "번")
