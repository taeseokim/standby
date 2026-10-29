# 업앤다운 숫자 맞추기 게임 (모범 답안 예시)
import random

MIN_NUMBER = 1
MAX_NUMBER = 100


def read_guess():
    """1~100 사이 정수를 입력받을 때까지 다시 묻는다. 잘못된 입력은 시도 횟수에 넣지 않는다."""
    while True:
        text = input(f"{MIN_NUMBER}~{MAX_NUMBER} 사이 숫자를 입력하세요: ")
        if not text.strip().lstrip("-").isdigit():
            print("숫자만 입력하세요.")
            continue
        guess = int(text)
        if guess < MIN_NUMBER or guess > MAX_NUMBER:
            print(f"{MIN_NUMBER}부터 {MAX_NUMBER}까지의 숫자만 입력할 수 있습니다. 다시 입력하세요.")
            continue
        return guess


def play_one_game():
    answer = random.randint(MIN_NUMBER, MAX_NUMBER)  # 정답 만들기 (양 끝 포함)
    attempts = 0  # 시도 횟수
    while True:
        guess = read_guess()
        attempts += 1
        if guess < answer:
            print("UP!")
        elif guess > answer:
            print("DOWN!")
        else:
            print(f"정답입니다! {attempts}번 만에 맞혔습니다.")
            break


print("=== 업앤다운 숫자 맞추기 게임 ===")
while True:
    play_one_game()
    again = input("다시 하시겠습니까? (Y/N): ").strip().upper()
    if again != "Y":
        print("게임을 종료합니다. 고마워요!")
        break
