# BMI 비만도 판정 프로그램 (모범 답안 예시)

def input_positive_number(prompt):
    """0보다 큰 실수를 입력받을 때까지 반복해서 물어본다."""
    while True:
        value = float(input(prompt))
        if value <= 0:
            print("0보다 큰 값을 입력하세요. 다시 입력해 주세요.")
        else:
            return value


height_cm = input_positive_number("키(cm)를 입력하세요: ")
weight_kg = input_positive_number("몸무게(kg)를 입력하세요: ")

# cm를 m로 바꾼 뒤 BMI = 몸무게 / 키(m)의 제곱
height_m = height_cm / 100
bmi = weight_kg / height_m ** 2

# 5단계 비만도 판정 (경계값은 위 단계에 포함)
if bmi < 18.5:
    stage = "저체중"
elif bmi < 23:
    stage = "정상"
elif bmi < 25:
    stage = "과체중"
elif bmi < 30:
    stage = "비만"
else:
    stage = "고도비만"

print(f"BMI: {bmi:.2f}")
print(f"판정 결과: {stage}")
