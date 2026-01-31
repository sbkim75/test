import os
from PIL import Image
from reportlab.pdfgen import canvas

def create_pdf_from_images(root_folder, output_pdf):
    image_list = []

    # 파일 확장자 리스트
    valid_extensions = ['.jpg', '.png' ,'.gif']

    # 최상위 폴더 안의 파일들을 정렬된 순서로 나열합니다.
    for file_name in sorted(os.listdir(root_folder)):
        file_path = os.path.join(root_folder, file_name)
        if os.path.isdir(file_path):
            # 서브 폴더가 있는 경우
            for sub_file_name in sorted(os.listdir(file_path)):
                if any(sub_file_name.endswith(ext) for ext in valid_extensions):
                    sub_file_path = os.path.join(file_path, sub_file_name)
                    image_list.append(sub_file_path)
        else:
            # 서브 폴더가 없는 경우
            if any(file_name.endswith(ext) for ext in valid_extensions):
                image_list.append(file_path)

    # 이미지가 없는 경우 예외 처리
    if not image_list:
        raise ValueError("No images found to include in the PDF.")
    
    # PDF 생성
    first_image = Image.open(image_list[0])
    c = canvas.Canvas(output_pdf, pagesize=first_image.size)
    
    for image_path in image_list:
        img = Image.open(image_path)
        img_width, img_height = img.size
        
        c.setPageSize((img_width, img_height))
        c.drawImage(image_path, 0, 0, img_width, img_height)
        c.showPage()
    
    c.save()


# 사용 예시
def get_subfolders(path):
    subfolders = [f.path for f in os.scandir(path) if f.is_dir()]
    return subfolders

# 원하는 경로를 지정하세요
target_path = r"Z:\새 폴더"

subfolder_list = get_subfolders(target_path)

print("하위 폴더 목록:")
for folder in subfolder_list:
    output_pdf = folder+".pdf"
    print(folder)
    create_pdf_from_images(folder, output_pdf)
# root_folder = f'Z:\\새 폴더\\거미입니다만 문제라도14권'  # 이미지를 포함한 최상위 폴더
# output_pdf = f'Z:\\새 폴더\\거미입니다만 문제라도14권.pdf'  # 생성될 PDF 파일 이름
# create_pdf_from_images(root_folder, output_pdf)

