import pytest
import tempfile
import shutil
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, Mock
import sys

# rename_files.py の関数をインポート
sys.path.insert(0, str(Path(__file__).parent.parent))
from rename_files import process_folder, get_target_files, get_new_name_and_folder, main

@pytest.fixture
def test_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        folder = Path(tmpdir)
        # テスト用ファイル作成とctimeマッピング
        ctime_map = {}
        dt1 = datetime(2024, 1, 1, 12, 0, 0).timestamp()
        dt2 = datetime(2024, 2, 2, 13, 30, 45).timestamp()
        dt3 = dt1
        names = [
            ("a.jpg", dt1),
            ("b.JPG", dt2),
            ("c.txt", dt3),
            ("d.exe", dt1),
        ]
        for name, ts in names:
            f = folder / name
            f.write_text("test")
            os.utime(f, (ts, ts))
            ctime_map[str(f)] = ts

        jan_folder = folder / "2024_01"
        jan_folder.mkdir(exist_ok=True)
        (jan_folder / "20240101_120000.jpg").write_text("exists")
        (jan_folder / "20240101_120000.txt").write_text("exists")

        yield folder, ctime_map

def run_script(folder, ctime_map):
    """os.path.getctime をモックしてprocess_folder を実行"""
    original_getctime = os.path.getctime

    def mock_getctime(path):
        return ctime_map.get(str(path), original_getctime(path))

    # rename_files モジュール内の os.path.getctime をパッチ
    with patch('rename_files.os.path.getctime', side_effect=mock_getctime):
        process_folder(str(folder))

def test_rename_and_move(test_dir):
    folder, ctime_map = test_dir
    run_script(folder, ctime_map)
    jan = folder / "2024_01"
    feb = folder / "2024_02"
    assert jan.exists()
    assert feb.exists()
    assert (feb / "20240202_133045.jpg").exists()
    assert (jan / "20240101_120000.jpg").exists()
    assert (jan / "20240101_120000.txt").exists()
    assert (folder / "d.exe").exists()

def test_skip_on_duplicate(test_dir):
    folder, ctime_map = test_dir
    run_script(folder, ctime_map)
    jan = folder / "2024_01"
    with open(jan / "20240101_120000.jpg") as f:
        assert f.read() == "exists"
    with open(jan / "20240101_120000.txt") as f:
        assert f.read() == "exists"

def test_ignore_non_target_extension(test_dir):
    folder, ctime_map = test_dir
    run_script(folder, ctime_map)
    assert (folder / "d.exe").exists()

def test_empty_folder():
    with tempfile.TemporaryDirectory() as tmpdir:
        folder = Path(tmpdir)
        process_folder(str(folder))
        assert list(folder.iterdir()) == []


class TestGetTargetFiles:
    """get_target_files 関数の直接ユニットテスト"""
    
    def test_get_target_files_empty_folder(self):
        """空フォルダの場合"""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            extensions = {'.jpg', '.png', '.txt'}
            result = get_target_files(folder, extensions)
            assert result == []
    
    def test_get_target_files_single_extension(self):
        """単一の拡張子のファイル"""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            (folder / "test1.jpg").write_text("test")
            (folder / "test2.jpg").write_text("test")
            (folder / "test.png").write_text("test")
            
            extensions = {'.jpg'}
            result = get_target_files(folder, extensions)
            assert len(result) == 2
            assert all(f.suffix.lower() == '.jpg' for f in result)
    
    def test_get_target_files_multiple_extensions(self):
        """複数の拡張子のファイル"""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            (folder / "image.jpg").write_text("test")
            (folder / "image.PNG").write_text("test")
            (folder / "doc.txt").write_text("test")
            (folder / "video.mp4").write_text("test")
            (folder / "script.py").write_text("test")
            
            extensions = {'.jpg', '.png', '.txt', '.mp4'}
            result = get_target_files(folder, extensions)
            assert len(result) == 4
    
    def test_get_target_files_case_insensitive(self):
        """拡張子の大文字小文字を区別しない"""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            (folder / "image1.JPG").write_text("test")
            (folder / "image2.Jpg").write_text("test")
            (folder / "image3.jpg").write_text("test")
            
            extensions = {'.jpg'}
            result = get_target_files(folder, extensions)
            assert len(result) == 3
    
    def test_get_target_files_ignores_directories(self):
        """ディレクトリは無視される"""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            (folder / "file.jpg").write_text("test")
            (folder / "subdir").mkdir()
            (folder / "subdir" / "nested.jpg").write_text("test")
            
            extensions = {'.jpg'}
            result = get_target_files(folder, extensions)
            # 最上位のファイルのみ
            assert len(result) == 1
            assert result[0].name == "file.jpg"


class TestGetNewNameAndFolder:
    """get_new_name_and_folder 関数の直接ユニットテスト"""
    
    def test_get_new_name_and_folder_basic(self):
        """基本的な日時フォーマット"""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            file = folder / "test.jpg"
            file.write_text("test")
            
            # 特定の日時のタイムスタンプ
            dt = datetime(2024, 3, 15, 14, 30, 45)
            ctime = dt.timestamp()
            
            new_name, month_folder = get_new_name_and_folder(file, ctime)
            
            assert new_name == "20240315_143045.jpg"
            assert month_folder == "2024_03"
    
    def test_get_new_name_and_folder_lowercase_extension(self):
        """拡張子が小文字に変換される"""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            file = folder / "test.PNG"
            file.write_text("test")
            
            dt = datetime(2024, 1, 1, 0, 0, 0)
            ctime = dt.timestamp()
            
            new_name, month_folder = get_new_name_and_folder(file, ctime)
            
            assert new_name == "20240101_000000.png"
            assert month_folder == "2024_01"
    
    @pytest.mark.parametrize("ext,expected_ext", [
        (".jpg", ".jpg"),
        (".JPG", ".jpg"),
        (".Jpg", ".jpg"),
        (".PNG", ".png"),
        (".txt", ".txt"),
        (".PDF", ".pdf"),
    ])
    def test_get_new_name_and_folder_extensions(self, ext, expected_ext):
        """様々な拡張子のパラメトライズドテスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            file = folder / f"test{ext}"
            file.write_text("test")
            
            dt = datetime(2024, 6, 15, 12, 0, 0)
            ctime = dt.timestamp()
            
            new_name, month_folder = get_new_name_and_folder(file, ctime)
            
            assert new_name.endswith(expected_ext)
            assert new_name == f"20240615_120000{expected_ext}"
    
    def test_get_new_name_and_folder_december(self):
        """12月の処理"""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            file = folder / "test.jpg"
            file.write_text("test")
            
            dt = datetime(2024, 12, 31, 23, 59, 59)
            ctime = dt.timestamp()
            
            new_name, month_folder = get_new_name_and_folder(file, ctime)
            
            assert new_name == "20241231_235959.jpg"
            assert month_folder == "2024_12"


class TestProcessFolderErrorHandling:
    """process_folder のエラーハンドリングテスト"""
    
    @patch('rename_files.shutil.move')
    @patch('rename_files.os.path.getctime')
    def test_shutil_move_failure(self, mock_getctime, mock_move, capsys):
        """shutil.move が失敗した場合のエラーハンドリング"""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            (folder / "test.jpg").write_text("test")
            
            # getctime をモック
            mock_getctime.return_value = datetime(2024, 1, 1, 12, 0, 0).timestamp()
            
            # shutil.move が例外を発生させる
            mock_move.side_effect = PermissionError("Permission denied")
            
            process_folder(str(folder))
            
            captured = capsys.readouterr()
            assert '[エラー]' in captured.out
            assert '移動に失敗' in captured.out
            assert 'スキップされたファイル' in captured.out
    
    def test_nonexistent_folder(self, capsys):
        """存在しないフォルダを指定した場合"""
        nonexistent = "/nonexistent/folder/path"
        
        process_folder(nonexistent)
        
        captured = capsys.readouterr()
        assert '指定フォルダが存在しません' in captured.out


class TestTimestampCollision:
    """タイムスタンプ衝突のテスト"""
    
    @patch('rename_files.os.path.getctime')
    def test_multiple_files_same_timestamp(self, mock_getctime):
        """同じタイムスタンプの複数ファイル（先着が優先）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            (folder / "file1.jpg").write_text("first")
            (folder / "file2.jpg").write_text("second")
            (folder / "file3.jpg").write_text("third")
            
            # すべて同じタイムスタンプ
            same_time = datetime(2024, 1, 1, 12, 0, 0).timestamp()
            mock_getctime.return_value = same_time
            
            process_folder(str(folder))
            
            target_folder = folder / "2024_01"
            target_file = target_folder / "20240101_120000.jpg"
            
            # 1つ目が移動され、2つ目と3つ目はスキップされる
            assert target_file.exists()
            # スキップされたファイルは元の場所に残る
            remaining_files = list(folder.glob("*.jpg"))
            assert len(remaining_files) == 2


class TestMain:
    """main 関数のテストスイート"""
    
    @patch('rename_files.process_folder')
    @patch('sys.argv', ['rename_files.py', '/test/folder'])
    def test_main_basic(self, mock_process):
        """基本的なCLI実行"""
        main()
        mock_process.assert_called_once_with('/test/folder')
    
    @patch('sys.argv', ['rename_files.py'])
    def test_main_missing_folder_arg(self):
        """必須引数が欠けている場合（SystemExit）"""
        with pytest.raises(SystemExit):
            main()
    
    @patch('sys.argv', ['rename_files.py', '--help'])
    def test_main_help(self):
        """ヘルプメッセージの表示"""
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

