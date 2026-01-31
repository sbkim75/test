import argparse
import os
import sys
from pathlib import Path

# 지원하는 전자책 파일 확장자
EXTENSIONS = ["cbz", "zip", "rar", "cbr", "tar.gz", "7zip", "7z", "cb7", "cbt", "pdf", "epub", "txt"]

class KavitaLocal:
    def __init__(self, root_path=None, recursive=True):
        """
        Windows 환경에서 로컬 디렉토리의 책을 검색하는 클래스

        Args:
            root_path: 검색할 경로 (기본값: 현재 디렉토리)
            recursive: 하위 디렉토리 포함 여부 (기본값: True)
        """
        self.root_path = Path(root_path) if root_path else Path.cwd()
        self.recursive = recursive
        self.books = []

    def is_book_file(self, filename):
        """파일이 전자책 파일인지 확인"""
        ext = filename.lower().split('.')[-1]
        return ext in EXTENSIONS

    def get_file_size(self, filepath):
        """파일 크기를 읽기 쉬운 형식으로 반환"""
        size = os.path.getsize(filepath)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

    def search_books(self):
        """디렉토리에서 책 파일 검색"""
        print(f"\n{'='*80}")
        print(f"검색 경로: {self.root_path.absolute()}")
        print(f"재귀 검색: {'예' if self.recursive else '아니오'}")
        print(f"{'='*80}\n")

        if not self.root_path.exists():
            print(f"오류: 경로를 찾을 수 없습니다 - {self.root_path}")
            return

        if self.recursive:
            # 재귀적으로 모든 하위 디렉토리 검색
            for root, dirs, files in os.walk(self.root_path):
                for filename in files:
                    if self.is_book_file(filename):
                        filepath = os.path.join(root, filename)
                        self.add_book(filepath, filename, root)
        else:
            # 현재 디렉토리만 검색
            for item in self.root_path.iterdir():
                if item.is_file() and self.is_book_file(item.name):
                    self.add_book(str(item), item.name, str(self.root_path))

        self.display_results()

    def add_book(self, filepath, filename, directory):
        """책 정보를 리스트에 추가"""
        try:
            book_info = {
                'filename': filename,
                'filepath': filepath,
                'directory': directory,
                'extension': filename.split('.')[-1].lower(),
                'size': self.get_file_size(filepath)
            }
            self.books.append(book_info)
        except Exception as e:
            print(f"오류: {filename} - {str(e)}")

    def display_results(self):
        """검색 결과 출력"""
        if not self.books:
            print("책 파일을 찾을 수 없습니다.\n")
            return

        print(f"총 {len(self.books)}개의 책 파일을 찾았습니다.\n")

        # 디렉토리별로 그룹화
        books_by_dir = {}
        for book in self.books:
            dir_path = book['directory']
            if dir_path not in books_by_dir:
                books_by_dir[dir_path] = []
            books_by_dir[dir_path].append(book)

        # 디렉토리별로 출력
        for idx, (directory, books) in enumerate(sorted(books_by_dir.items()), 1):
            rel_path = os.path.relpath(directory, self.root_path)
            if rel_path == '.':
                rel_path = '(현재 디렉토리)'

            print(f"\n[{idx}] {rel_path}")
            print(f"    경로: {directory}")
            print(f"    파일 수: {len(books)}개")
            print(f"    {'-'*76}")

            for book in sorted(books, key=lambda x: x['filename']):
                print(f"    📚 {book['filename']}")
                print(f"       형식: {book['extension'].upper()}, 크기: {book['size']}")

        print(f"\n{'='*80}")
        self.display_statistics()

    def display_statistics(self):
        """통계 정보 출력"""
        if not self.books:
            return

        # 확장자별 통계
        ext_count = {}
        for book in self.books:
            ext = book['extension']
            ext_count[ext] = ext_count.get(ext, 0) + 1

        print("\n📊 파일 형식별 통계:")
        for ext, count in sorted(ext_count.items(), key=lambda x: x[1], reverse=True):
            print(f"   {ext.upper()}: {count}개")
        print(f"{'='*80}\n")

    def export_list(self, output_file='books_list.txt'):
        """검색 결과를 텍스트 파일로 저장"""
        if not self.books:
            print("저장할 책 정보가 없습니다.")
            return

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"책 검색 결과\n")
                f.write(f"검색 경로: {self.root_path.absolute()}\n")
                f.write(f"검색 일시: {Path(output_file).stat().st_mtime}\n")
                f.write(f"총 파일 수: {len(self.books)}개\n")
                f.write(f"{'='*80}\n\n")

                # 디렉토리별로 그룹화
                books_by_dir = {}
                for book in self.books:
                    dir_path = book['directory']
                    if dir_path not in books_by_dir:
                        books_by_dir[dir_path] = []
                    books_by_dir[dir_path].append(book)

                for directory, books in sorted(books_by_dir.items()):
                    f.write(f"\n디렉토리: {directory}\n")
                    f.write(f"{'-'*80}\n")

                    for book in sorted(books, key=lambda x: x['filename']):
                        f.write(f"  파일명: {book['filename']}\n")
                        f.write(f"  형식: {book['extension'].upper()}, 크기: {book['size']}\n")
                        f.write(f"  전체 경로: {book['filepath']}\n\n")

            print(f"✅ 검색 결과가 '{output_file}' 파일로 저장되었습니다.")

        except Exception as e:
            print(f"❌ 파일 저장 중 오류 발생: {str(e)}")


def main():
    parser = argparse.ArgumentParser(
        description='Windows 환경에서 현재 디렉토리의 전자책 파일을 검색합니다.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 현재 디렉토리에서 검색 (재귀)
  python kavita_local.py

  # 특정 경로에서 검색
  python kavita_local.py --path "C:\\Users\\UserName\\Documents\\Books"

  # 현재 디렉토리만 검색 (하위 폴더 제외)
  python kavita_local.py --no-recursive

  # 검색 결과를 파일로 저장
  python kavita_local.py --export books.txt

지원 파일 형식:
  cbz, zip, rar, cbr, 7z, cb7, cbt, pdf, epub, txt
        """
    )

    parser.add_argument(
        '--path',
        type=str,
        default=None,
        help='검색할 디렉토리 경로 (기본값: 현재 디렉토리)'
    )

    parser.add_argument(
        '--no-recursive',
        action='store_true',
        help='하위 디렉토리를 검색하지 않음'
    )

    parser.add_argument(
        '--export',
        type=str,
        default=None,
        metavar='FILE',
        help='검색 결과를 텍스트 파일로 저장'
    )

    args = parser.parse_args()

    try:
        # KavitaLocal 인스턴스 생성
        kavita = KavitaLocal(
            root_path=args.path,
            recursive=not args.no_recursive
        )

        # 책 검색
        kavita.search_books()

        # 결과 저장 (옵션)
        if args.export:
            kavita.export_list(args.export)

    except KeyboardInterrupt:
        print("\n\n프로그램이 사용자에 의해 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
