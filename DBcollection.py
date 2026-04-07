import requests
import json


def fetch_iba_cocktails():
    # 오픈소스 저장소의 IBA 칵테일 정제 데이터 (Raw JSON URL)
    url = "https://raw.githubusercontent.com/rasmusab/iba-cocktails/master/iba-web/iba-cocktails-web.json"

    print("데이터를 다운로드하는 중...")
    response = requests.get(url)

    if response.status_code == 200:
        cocktails = response.json()

        # 윈도우 환경에서 프랑스어 악센트 등 특수문자가 깨지지 않도록 utf-8 인코딩을 명시하여 저장
        with open('iba_cocktails_complete.json', 'w', encoding='utf-8') as f:
            json.dump(cocktails, f, ensure_ascii=False, indent=4)

        print(f"성공! 총 {len(cocktails)}개의 칵테일 레시피가 'iba_cocktails_complete.json' 파일로 저장되었습니다.")

        # 데이터 구조 샘플 출력
        print("\n[데이터 스키마 샘플 확인]")
        print(json.dumps(cocktails[0], ensure_ascii=False, indent=2))

    else:
        print(f"다운로드 실패: HTTP 상태 코드 {response.status_code}")


if __name__ == "__main__":
    fetch_iba_cocktails()