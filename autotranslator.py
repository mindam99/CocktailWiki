import json
import time
from deep_translator import GoogleTranslator


def semi_auto_translate():
    print("번역기를 준비하는 중...")
    translator = GoogleTranslator(source='en', target='ko')

    # 원본 파일 불러오기
    try:
        with open('iba_cocktails_complete.json', 'r', encoding='utf-8') as f:
            cocktails = json.load(f)
    except FileNotFoundError:
        print("에러: 'iba_cocktails_complete.json' 파일이 없습니다.")
        return

    total = len(cocktails)
    print(f"총 {total}개의 칵테일 재료/레시피 자동 번역을 시작합니다 (약 1~2분 소요)...\n")

    for i, cocktail in enumerate(cocktails):
        # 1. 칵테일 이름: 수동 번역을 위해 빈칸으로 둠
        cocktail['name_ko'] = ""

        # 2. 레시피(조리법) 자동 번역
        method_en = cocktail.get('preparation') or cocktail.get('method') or ""
        if method_en:
            try:
                cocktail['method_ko'] = translator.translate(method_en)
            except Exception:
                cocktail['method_ko'] = ""

        # 3. 재료 자동 번역
        if 'ingredients' in cocktail:
            for item in cocktail['ingredients']:
                ing_en = item.get('ingredient') or item.get('special') or ""
                if ing_en:
                    try:
                        item['ingredient_ko'] = translator.translate(ing_en)
                    except Exception:
                        item['ingredient_ko'] = ""

        print(f"[{i + 1}/{total}] {cocktail['name']} ... 재료 및 조리법 번역 완료")

        # 구글 서버 차단 방지 (Rate Limit 대응)
        time.sleep(0.3)

    # 결과를 작업용 파일로 저장
    with open('iba_cocktails_translated.json', 'w', encoding='utf-8') as f:
        json.dump(cocktails, f, ensure_ascii=False, indent=4)

    print("\n🎉 반자동 번역 완료! 'iba_cocktails_translated.json' 파일이 생성되었습니다.")


if __name__ == "__main__":
    semi_auto_translate()