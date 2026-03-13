"""seed_generator.py のユニットテスト"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_engine():
    """SeedGenerator用のモックエンジンを提供する"""
    with patch("src.seed_generator.get_db_engine") as mock_get_engine:
        engine = MagicMock()
        mock_get_engine.return_value = engine
        yield engine


def _make_mock_result(columns: list[str], rows: list[tuple]):
    """SQLAlchemy Result互換のモックを作成する"""
    mock_result = MagicMock()
    mock_result.keys.return_value = columns
    mock_result.__iter__ = MagicMock(return_value=iter(rows))
    return mock_result


def _make_count_result(count: int):
    """COUNT(*)クエリ用のモックResultを作成する"""
    mock_result = MagicMock()
    mock_result.fetchone.return_value = (count,)
    return mock_result


class TestGenerateSpeakersSeed:
    """generate_speakers_seed のテスト"""

    def test_正常系_INSERT文が生成される(self, mock_engine):
        from src.seed_generator import SeedGenerator

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        mock_conn.execute.return_value = _make_mock_result(
            ["name", "name_yomi"],
            [
                ("田中太郎", "たなかたろう"),
                ("山田花子", None),
            ],
        )

        generator = SeedGenerator()
        result = generator.generate_speakers_seed()

        assert "INSERT INTO speakers (name, name_yomi)" in result
        assert "WHERE NOT EXISTS" in result
        assert "'田中太郎'" in result
        assert "'たなかたろう'" in result
        assert "'山田花子'" in result
        assert "NULL" in result
        assert "2 unique speakers" in result

    def test_NULL_name_yomiの処理(self, mock_engine):
        from src.seed_generator import SeedGenerator

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        mock_conn.execute.return_value = _make_mock_result(
            ["name", "name_yomi"],
            [("テスト議員", None)],
        )

        generator = SeedGenerator()
        result = generator.generate_speakers_seed()

        assert (
            "SELECT 'テスト議員', NULL "
            "WHERE NOT EXISTS (SELECT 1 FROM speakers WHERE name = 'テスト議員');"
            in result
        )

    def test_空テーブルの場合は空文字を返す(self, mock_engine):
        from src.seed_generator import SeedGenerator

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        mock_conn.execute.return_value = _make_mock_result(["name", "name_yomi"], [])

        generator = SeedGenerator()
        result = generator.generate_speakers_seed()
        assert result == ""

    def test_SQLエスケープ_シングルクォート(self, mock_engine):
        from src.seed_generator import SeedGenerator

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        mock_conn.execute.return_value = _make_mock_result(
            ["name", "name_yomi"],
            [("O'Brien", "おぶらいえん")],
        )

        generator = SeedGenerator()
        result = generator.generate_speakers_seed()

        assert "O''Brien" in result
        assert "O'Brien" not in result.replace("O''Brien", "")

    def test_outputパラメータでファイル書き込み(self, mock_engine):
        from src.seed_generator import SeedGenerator

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        mock_conn.execute.return_value = _make_mock_result(
            ["name", "name_yomi"],
            [("テスト", "てすと")],
        )

        generator = SeedGenerator()
        mock_output = MagicMock()
        result = generator.generate_speakers_seed(output=mock_output)

        mock_output.write.assert_called_once_with(result)


class TestGenerateSpeakerPoliticianLinksSeed:
    """generate_speaker_politician_links_seed のテスト"""

    def test_政治家紐付けのUPDATE文が生成される(self, mock_engine):
        from src.seed_generator import SeedGenerator

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        # 1回目: 政治家紐付け、2回目: 非政治家分類
        mock_conn.execute.side_effect = [
            _make_mock_result(
                [
                    "name",
                    "politician_name",
                    "matching_confidence",
                    "matching_reason",
                    "is_manually_verified",
                ],
                [
                    ("田中太郎", "田中太郎", 1.00, "exact_name: 自動マッチ", False),
                ],
            ),
            _make_mock_result(["name", "skip_reason"], []),
        ]

        generator = SeedGenerator()
        result = generator.generate_speaker_politician_links_seed()

        assert "UPDATE speakers SET" in result
        assert "politician_id = (SELECT id FROM politicians" in result
        assert "is_politician = true" in result
        assert "matching_confidence = 1.00" in result
        assert "matching_reason = 'exact_name: 自動マッチ'" in result
        assert "is_manually_verified = false" in result
        assert "WHERE name = '田中太郎'" in result
        assert "1 unique names" in result

    def test_非政治家分類のUPDATE文が生成される(self, mock_engine):
        from src.seed_generator import SeedGenerator

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        mock_conn.execute.side_effect = [
            _make_mock_result(
                [
                    "name",
                    "politician_name",
                    "matching_confidence",
                    "matching_reason",
                    "is_manually_verified",
                ],
                [],
            ),
            _make_mock_result(
                ["name", "skip_reason"],
                [("会議録情報", "other_non_politician")],
            ),
        ]

        generator = SeedGenerator()
        result = generator.generate_speaker_politician_links_seed()

        assert "is_politician = false" in result
        assert "skip_reason = 'other_non_politician'" in result
        assert "WHERE name = '会議録情報'" in result
        assert "非政治家分類" in result

    def test_両方空の場合は空文字を返す(self, mock_engine):
        from src.seed_generator import SeedGenerator

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        mock_conn.execute.side_effect = [
            _make_mock_result(
                [
                    "name",
                    "politician_name",
                    "matching_confidence",
                    "matching_reason",
                    "is_manually_verified",
                ],
                [],
            ),
            _make_mock_result(["name", "skip_reason"], []),
        ]

        generator = SeedGenerator()
        result = generator.generate_speaker_politician_links_seed()
        assert result == ""

    def test_手動検証済みフラグがtrueの場合(self, mock_engine):
        from src.seed_generator import SeedGenerator

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        mock_conn.execute.side_effect = [
            _make_mock_result(
                [
                    "name",
                    "politician_name",
                    "matching_confidence",
                    "matching_reason",
                    "is_manually_verified",
                ],
                [("検証済み議員", "検証済み議員", 0.95, "manual: 手動確認", True)],
            ),
            _make_mock_result(["name", "skip_reason"], []),
        ]

        generator = SeedGenerator()
        result = generator.generate_speaker_politician_links_seed()

        assert "is_manually_verified = true" in result
        assert "matching_confidence = 0.95" in result

    def test_ヘッダコメントに前提条件が含まれる(self, mock_engine):
        from src.seed_generator import SeedGenerator

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        mock_conn.execute.side_effect = [
            _make_mock_result(
                [
                    "name",
                    "politician_name",
                    "matching_confidence",
                    "matching_reason",
                    "is_manually_verified",
                ],
                [("テスト", "テスト", 1.0, "test", False)],
            ),
            _make_mock_result(["name", "skip_reason"], []),
        ]

        generator = SeedGenerator()
        result = generator.generate_speaker_politician_links_seed()

        assert "speakers テーブルと politicians テーブルがロード済み" in result
        assert "名前ベースで参照" in result


class TestGetTableCount:
    """get_table_count のテスト"""

    def test_正常系(self, mock_engine):
        from src.seed_generator import SeedGenerator

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value = _make_count_result(100)

        generator = SeedGenerator()
        count = generator.get_table_count("speakers")
        assert count == 100

    def test_不正なテーブル名で例外(self, mock_engine):
        from src.seed_generator import SeedGenerator

        generator = SeedGenerator()
        with pytest.raises(ValueError, match="不正なテーブル名"):
            generator.get_table_count("invalid_table")


class TestEmptyTableSafety:
    """空テーブル安全対策のテスト"""

    def test_空テーブル時にファイルが生成されない(self, mock_engine, tmp_path):
        from src.seed_generator import generate_all_seeds

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        # 全テーブル0件を返す
        mock_conn.execute.return_value = _make_count_result(0)

        output_dir = str(tmp_path)
        generate_all_seeds(output_dir)

        # ファイルが生成されていないことを確認
        import os

        files = os.listdir(output_dir)
        assert len(files) == 0

    def test_既存ファイルが空テーブル時に保護される(self, mock_engine, tmp_path):
        from src.seed_generator import generate_all_seeds

        # 既存ファイルを作成
        existing_file = tmp_path / "seed_governing_bodies_generated.sql"
        existing_content = "-- existing content"
        existing_file.write_text(existing_content)

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        # 全テーブル0件
        mock_conn.execute.return_value = _make_count_result(0)

        generate_all_seeds(str(tmp_path))

        # 既存ファイルの内容が変わっていないこと
        assert existing_file.read_text() == existing_content
