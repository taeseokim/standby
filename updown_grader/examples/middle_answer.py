# 업앤다운 게임
import random

answer = random.randint(1, 100)
count = 0

while True:
    guess = int(input("숫자를 입력하세요(1~100): "))
    count += 1  # 범위 밖 입력도 횟수에 들어감
    if guess < 1 or guess > 100:
        print("1~100 사이 숫자만 입력하세요.")
        continue
    if guess < answer:
        print("UP")
    elif guess > answer:
        print("DOWN")
    else:
        print(f"정답! {count}번 만에 맞혔어요.")
        break
