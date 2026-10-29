import random
a = random.randint(1, 99)
c = 0
while True:
    b = int(input())
    if b > a:
        print("UP")
    elif b < a:
        print("DOWN")
    else:
        print("정답")
