a = int(input())
b = int(input())
c = b / a ** 2
if c < 18.5:
    print("저체중")
if c > 18.5 and c < 23:
    print("정상")
if c > 23 and c < 25:
    print("과체중")
if c > 25:
    print("비만")
