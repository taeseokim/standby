# ============================================================
# 업앤다운 숫자 맞추기 게임 — 예시 답안 A (모범 답안)
# 예상 점수: 50점 / 50점
#   정답 생성 및 비교 로직 10 | 반복문 제어 및 종료 10 | 시도 횟수 카운트 10
#   예외 처리 및 안정성 10 | 코드 품질 10
# ============================================================
import random

MIN_NUMBER = 1      # 정답 범위의 최솟값
MAX_NUMBER = 100    # 정답 범위의 최댓값

print("=== 업앤다운 숫자 맞추기 게임 ===")
print(f"{MIN_NUMBER}부터 {MAX_NUMBER}까지 숫자 중 하나를 맞혀 보세요!")

while True:  # 게임 전체 반복 (재시작용)
    answer = random.randint(MIN_NUMBER, MAX_NUMBER)  # 정답 생성 (1과 100 포함)
    attempts = 0                                     # 새 게임마다 시도 횟수 초기화

    while True:  # 정답을 맞힐 때까지 반복
        user_input = input(f"숫자를 입력하세요 ({MIN_NUMBER}~{MAX_NUMBER}): ")

        # 숫자가 아닌 입력은 경고 후 다시 입력 (시도 횟수에 넣지 않음)
        if not user_input.strip().lstrip("-").isdigit():
            print("숫자만 입력해 주세요.")
            continue

        guess = int(user_input)

        # 범위를 벗어난 입력은 경고 후 다시 입력 (시도 횟수에 넣지 않음)
        if guess < MIN_NUMBER or guess > MAX_NUMBER:
            print(f"{MIN_NUMBER}~{MAX_NUMBER} 사이의 숫자만 입력할 수 있어요. 다시 입력하세요.")
            continue

        attempts += 1  # 올바른 입력만 시도 횟수에 더함

        if guess < answer:
            print("UP! 더 큰 수입니다.")
        elif guess > answer:
            print("DOWN! 더 작은 수입니다.")
        else:
            print(f"정답입니다! {attempts}번 만에 맞혔습니다.")
            break  # 정답이면 바로 반복 종료

    # 재시작 여부 확인 (y, Y 모두 허용)
    again = input("다시 하시겠습니까? (Y/N): ").strip().upper()
    if again != "Y":
        print("게임을 종료합니다. 즐거웠어요!")
        break
