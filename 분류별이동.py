import os
import shutil
import yaml

# 분석 대상 경로
source_path = r"E:\리딩\책 - 보관\epub 보관"

# 이동 대상 경로
target_path = r"E:\READING\.ridi"


# 폴더 생성 함수
def create_folder(path):
    if not os.path.exists(path):
        os.makedirs(path)

# YAML 파일 분석 및 이동 함수
def process_yaml(yaml_file):
    # YAML 파일 읽기
    with open(yaml_file, 'r', encoding='utf-8') as file:
        content = yaml.safe_load(file)

    # <Genres> 태그 값 가져오기
    try:
        genre = content['meta']['Genres']
    except KeyError:
        print(f"Genres 태그가 없는 파일: {yaml_file}")
        return

    
    if genre != '':
        # "/"를 공백으로 바꾸기
        genre = genre.replace("/", ".")
        # ","를 기준으로 리스트 분할
        genres = genre.split(",")

        target_folder = os.path.join(target_path, *genres)
        yaml_dir = os.path.dirname(yaml_file)
        create_folder(target_folder)
    else:
        #장르가 공백이면 그냥 지나감
        print(f"Genres 비어있는 파일: {yaml_file}")
        return
        
    # YAML 파일이 있던 폴더 이름으로 새로운 폴더 생성
    new_dir_path = os.path.join(target_folder, os.path.basename(yaml_dir))
    create_folder(new_dir_path)
    # YAML 파일 이동 후 원래 폴더에 있는 모든 파일 이동
    for file in os.listdir(yaml_dir):
        shutil.move(os.path.join(yaml_dir, file), os.path.join(new_dir_path, file))
        print (f"{os.path.join(yaml_dir, file)} 에서 {os.path.join(new_dir_path, file)} 로 이동")
    # 원래 폴더 삭제
    os.rmdir(yaml_dir)

# 폴더 탐색 및 YAML 파일 처리
for root, dirs, files in os.walk(source_path):
    for file in files:
        if file.endswith(".yaml"):
            yaml_file = os.path.join(root, file)
            try:
                process_yaml(yaml_file)
            except Exception as e:
                print(f"Error: {e}")
                # YAML 파일 처리 중 에러가 발생할 경우 에러 메시지를 출력하고 무시합니다.

print("처리 완료!")
