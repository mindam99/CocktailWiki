import json

# 1. 원본 읽기
with open('iba_cocktails_complete.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 2. 한글 필드 추가
for cocktail in data:
    cocktail['name_ko'] = ""
    cocktail['method_ko'] = ""  # 원본의 'method' 대응
    if 'ingredients' in cocktail:
        for item in cocktail['ingredients']:
            item['ingredient_ko'] = ""

# 3. 작업용 파일로 저장
with open('iba_cocktails_translated.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print("작업 파일(iba_cocktails_translated.json) 생성 완료!")