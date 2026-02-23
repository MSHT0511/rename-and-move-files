import pytest
import tempfile
import shutil
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
import sys

# rename_files.pyのprocess_folder関数をインポート
sys.path.insert(0, str(Path(__file__).parent.parent))
from rename_files import process_folder

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
