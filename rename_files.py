import argparse
import os
import shutil
from pathlib import Path
from datetime import datetime

def get_target_files(folder: Path, extensions):
    files = []
    for f in folder.iterdir():
        if f.is_file() and f.suffix.lower() in extensions:
            files.append(f)
    return files

def get_new_name_and_folder(file: Path, ctime: float):
    dt = datetime.fromtimestamp(ctime)
    new_name = dt.strftime('%Y%m%d_%H%M%S') + file.suffix.lower()
    month_folder = dt.strftime('%Y_%m')
    return new_name, month_folder

def process_folder(folder_path):
    """フォルダ内のファイルを作成日時でリネームし、月別フォルダに移動する"""
    folder = Path(folder_path)
    if not folder.is_dir():
        print(f'指定フォルダが存在しません: {folder}')
        return

    # 対象拡張子（画像・動画・文書など汎用ファイル）
    extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff',
                  '.mp4', '.mov', '.avi', '.mkv', '.pdf', '.docx', '.xlsx', '.pptx', '.txt', '.csv', '.zip', '.rar'}

    files = get_target_files(folder, extensions)
    print(f'検出ファイル数: {len(files)}')
    moved, skipped = 0, 0
    skipped_files = []

    for file in files:
        ctime = os.path.getctime(file)
        new_name, month_folder = get_new_name_and_folder(file, ctime)
        dest_dir = folder / month_folder
        dest_dir.mkdir(exist_ok=True)
        dest_path = dest_dir / new_name
        if dest_path.exists():
            print(f'[警告] {dest_path} が既に存在するためスキップ')
            skipped += 1
            skipped_files.append(str(file))
            continue
        try:
            shutil.move(str(file), str(dest_path))
            print(f'[移動] {file.name} -> {dest_path}')
            moved += 1
        except Exception as e:
            print(f'[エラー] {file} の移動に失敗: {e}')
            skipped += 1
            skipped_files.append(str(file))

    print(f'完了: {moved}件移動, {skipped}件スキップ')
    if skipped_files:
        print('スキップされたファイル:')
        for f in skipped_files:
            print(f'  {f}')

def main():
    parser = argparse.ArgumentParser(description='ファイルを作成日時でリネームし、月別フォルダに移動します。')
    parser.add_argument('folder', type=str, help='対象フォルダのパス')
    args = parser.parse_args()
    process_folder(args.folder)

if __name__ == '__main__':
    main()
