"""FileHandlerのテスト"""

import json

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from src.web_scraper.handlers.file_handler import FileHandler


class TestFileHandler:
    """FileHandlerクラスのテスト"""

    @pytest.fixture
    def file_handler(self, tmp_path):
        """FileHandlerのインスタンスを返すフィクスチャ"""
        return FileHandler(base_dir=str(tmp_path / "test_data"))

    def test_init_creates_base_dir(self, tmp_path):
        """初期化時にbase_dirが作成されることをテスト"""
        base_dir = tmp_path / "new_data"
        assert not base_dir.exists()

        FileHandler(base_dir=str(base_dir))

        assert base_dir.exists()

    def test_save_json(self, file_handler):
        """JSONデータの保存テスト"""
        data = {"key": "value", "number": 123}
        result = file_handler.save_json(data, "test.json")

        # ファイルが作成されたことを確認
        assert Path(result).exists()
        assert Path(result).name == "test.json"

        # ファイル内容を確認
        with open(result, encoding="utf-8") as f:
            loaded_data = json.load(f)
        assert loaded_data == data

    def test_save_json_with_subdirs(self, file_handler):
        """サブディレクトリを指定してJSONを保存"""
        data = {"test": "data"}
        subdirs = ["2024", "12", "25"]
        result = file_handler.save_json(data, "test.json", subdirs=subdirs)

        # パスが正しいことを確認
        assert "2024" in result
        assert "12" in result
        assert "25" in result
        assert Path(result).exists()

    def test_save_text(self, file_handler):
        """テキストデータの保存テスト"""
        content = "This is a test content.\nLine 2"
        result = file_handler.save_text(content, "test.txt")

        # ファイルが作成されたことを確認
        assert Path(result).exists()

        # ファイル内容を確認
        with open(result, encoding="utf-8") as f:
            loaded_content = f.read()
        assert loaded_content == content

    def test_save_text_with_subdirs(self, file_handler):
        """サブディレクトリを指定してテキストを保存"""
        content = "Test content"
        subdirs = ["year", "month"]
        result = file_handler.save_text(content, "test.txt", subdirs=subdirs)

        assert "year" in result
        assert "month" in result
        assert Path(result).exists()

    def test_load_json(self, file_handler):
        """JSONファイルの読み込みテスト"""
        # まずファイルを保存
        data = {"key": "value"}
        filepath = file_handler.save_json(data, "test.json")

        # 読み込みテスト
        loaded_data = file_handler.load_json(filepath)
        assert loaded_data == data

    def test_load_json_file_not_found(self, file_handler):
        """存在しないJSONファイルの読み込み"""
        result = file_handler.load_json("nonexistent.json")
        assert result is None

    def test_load_json_invalid_json(self, file_handler, tmp_path):
        """不正なJSONファイルの読み込み"""
        # 不正なJSONファイルを作成
        invalid_json_path = tmp_path / "invalid.json"
        with open(invalid_json_path, "w", encoding="utf-8") as f:
            f.write("{invalid json}")

        result = file_handler.load_json(str(invalid_json_path))
        assert result is None

    def test_load_text(self, file_handler):
        """テキストファイルの読み込みテスト"""
        # まずファイルを保存
        content = "Test content"
        filepath = file_handler.save_text(content, "test.txt")

        # 読み込みテスト
        loaded_content = file_handler.load_text(filepath)
        assert loaded_content == content

    def test_load_text_file_not_found(self, file_handler):
        """存在しないテキストファイルの読み込み"""
        result = file_handler.load_text("nonexistent.txt")
        assert result is None

    def test_create_date_subdirs_default(self, file_handler):
        """現在日時でサブディレクトリリストを作成"""
        now = datetime.now()
        result = file_handler.create_date_subdirs()

        assert len(result) == 3
        assert result[0] == str(now.year)
        assert result[1] == f"{now.month:02d}"
        assert result[2] == f"{now.day:02d}"

    def test_create_date_subdirs_with_date(self, file_handler):
        """指定日時でサブディレクトリリストを作成"""
        test_date = datetime(2024, 3, 5)
        result = file_handler.create_date_subdirs(test_date)

        assert result == ["2024", "03", "05"]

    def test_generate_filename(self, file_handler):
        """ファイル名の生成テスト"""
        result = file_handler.generate_filename("council123", "schedule456", "json")
        assert result == "council123_schedule456.json"

    def test_list_files(self, file_handler):
        """ファイル一覧表示テスト"""
        # テストファイルを作成
        file_handler.save_json({"test": 1}, "file1.json")
        file_handler.save_json({"test": 2}, "file2.json")
        file_handler.save_text("text", "file3.txt")

        # JSON ファイルのみをリスト
        result = file_handler.list_files(pattern="*.json")
        assert len(result) == 2

        # すべてのファイルをリスト
        result_all = file_handler.list_files(pattern="*")
        assert len(result_all) == 3

    def test_list_files_with_subdirs(self, file_handler):
        """サブディレクトリ内のファイル一覧"""
        subdirs = ["2024", "12"]
        file_handler.save_json({"test": 1}, "file1.json", subdirs=subdirs)

        result = file_handler.list_files(pattern="*.json", subdirs=subdirs)
        assert len(result) == 1

    def test_list_files_nonexistent_dir(self, file_handler):
        """存在しないディレクトリでのファイル一覧"""
        result = file_handler.list_files(subdirs=["nonexistent"])
        assert result == []

    def test_get_file_info(self, file_handler):
        """ファイル情報の取得テスト"""
        # テストファイルを作成
        filepath = file_handler.save_json({"test": "data"}, "test.json")

        # ファイル情報を取得
        info = file_handler.get_file_info(filepath)

        assert info is not None
        assert info["path"] == filepath
        assert info["name"] == "test.json"
        assert info["size"] > 0
        assert "created" in info
        assert "modified" in info
        assert info["is_file"] is True
        assert info["is_dir"] is False

    def test_get_file_info_nonexistent(self, file_handler):
        """存在しないファイルの情報取得"""
        info = file_handler.get_file_info("nonexistent.json")
        assert info is None

    def test_ensure_directory(self, file_handler, tmp_path):
        """ディレクトリの確保テスト"""
        new_dir = tmp_path / "new" / "nested" / "directory"
        assert not new_dir.exists()

        result = file_handler.ensure_directory(str(new_dir))

        assert new_dir.exists()
        assert result == new_dir

    def test_ensure_directory_already_exists(self, file_handler, tmp_path):
        """既存のディレクトリの確保"""
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()

        result = file_handler.ensure_directory(str(existing_dir))

        assert result == existing_dir
        assert existing_dir.exists()

    @patch("time.time")
    def test_cleanup_old_files(self, mock_time, file_handler, tmp_path):
        """古いファイルの削除テスト"""
        # 現在時刻を2024-12-31と仮定
        current_time = datetime(2024, 12, 31).timestamp()
        mock_time.return_value = current_time

        # テストファイルを作成
        old_file = file_handler.base_dir / "old_file.txt"
        old_file.write_text("old")
        recent_file = file_handler.base_dir / "recent_file.txt"
        recent_file.write_text("recent")

        # old_fileを60日前に設定
        import os

        old_mtime = datetime(2024, 11, 1).timestamp()
        os.utime(old_file, (old_mtime, old_mtime))

        # recent_fileを10日前に設定
        recent_mtime = datetime(2024, 12, 21).timestamp()
        os.utime(recent_file, (recent_mtime, recent_mtime))

        # 30日より古いファイルを削除
        file_handler.cleanup_old_files(days=30)

        # 検証
        assert not old_file.exists()
        assert recent_file.exists()
