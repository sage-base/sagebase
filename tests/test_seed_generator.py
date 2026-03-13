"""seed_generator.pyのユニットテスト"""

from unittest.mock import MagicMock, patch

import pytest

from src.seed_generator import SeedGenerator, generate_all_seeds


@pytest.fixture
def mock_engine():
    """モックエンジンを返すフィクスチャ"""
    with patch("src.seed_generator.get_db_engine") as mock_get_engine:
        engine = MagicMock()
        mock_get_engine.return_value = engine
        yield engine


def _make_mock_result(columns: list[str], rows: list[tuple[object, ...]]):
    """モックのクエリ結果を生成するヘルパー"""
    mock_result = MagicMock()
    mock_result.keys.return_value = columns
    mock_result.__iter__ = lambda self: iter(rows)
    return mock_result


def _make_count_result(count: int):
    """COUNTクエリ用のモック結果を生成するヘルパー"""
    mock_result = MagicMock()
    mock_result.fetchone.return_value = (count,)
    return mock_result


def _setup_conn(mock_engine: MagicMock) -> MagicMock:
    """モックコネクションのセットアップヘルパー"""
    mock_conn = MagicMock()
    mock_conn.__enter__ = lambda self: self
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_engine.connect.return_value = mock_conn
    return mock_conn


class TestGetTableCount:
    """get_table_countメソッドのテスト"""

    def test_returns_count(self, mock_engine: MagicMock) -> None:
        """テーブルのレコード数を返す"""
        mock_conn = _setup_conn(mock_engine)
        mock_conn.execute.return_value = _make_count_result(42)

        gen = SeedGenerator()
        assert gen.get_table_count("speakers") == 42

    def test_returns_zero_for_empty_table(self, mock_engine: MagicMock) -> None:
        """空テーブルで0を返す"""
        mock_conn = _setup_conn(mock_engine)
        mock_conn.execute.return_value = _make_count_result(0)

        gen = SeedGenerator()
        assert gen.get_table_count("speakers") == 0

    def test_rejects_invalid_table_name(self, mock_engine: MagicMock) -> None:
        """不正なテーブル名でValueErrorが発生する"""
        gen = SeedGenerator()
        with pytest.raises(ValueError, match="不正なテーブル名"):
            gen.get_table_count("invalid_table")


class TestGetSpeakerPoliticianLinkCount:
    """get_speaker_politician_link_countメソッドのテスト"""

    def test_returns_combined_count(self, mock_engine: MagicMock) -> None:
        """政治家紐付け + 非政治家分類の合計カウントを返す"""
        mock_conn = _setup_conn(mock_engine)
        mock_conn.execute.side_effect = [
            _make_count_result(10),
            _make_count_result(5),
        ]

        gen = SeedGenerator()
        assert gen.get_speaker_politician_link_count() == 15

    def test_returns_zero_when_no_links(self, mock_engine: MagicMock) -> None:
        """紐付けが0件の場合0を返す"""
        mock_conn = _setup_conn(mock_engine)
        mock_conn.execute.side_effect = [
            _make_count_result(0),
            _make_count_result(0),
        ]

        gen = SeedGenerator()
        assert gen.get_speaker_politician_link_count() == 0


class TestEmptyTableSafety:
    """空テーブル安全対策のテスト"""

    def test_skip_when_table_is_empty(
        self, mock_engine: MagicMock, tmp_path: object
    ) -> None:
        """0件の場合、ファイルが作成されない"""
        mock_conn = _setup_conn(mock_engine)
        mock_conn.execute.return_value = _make_count_result(0)

        output_file = tmp_path / "seed_speakers_generated.sql"  # type: ignore[operator]
        assert not output_file.exists()

        generate_all_seeds(str(tmp_path))

        assert not output_file.exists()

    def test_existing_file_preserved_when_table_empty(
        self, mock_engine: MagicMock, tmp_path: object
    ) -> None:
        """既存ファイルがある状態で0件 → ファイル内容が変わらない"""
        mock_conn = _setup_conn(mock_engine)
        mock_conn.execute.return_value = _make_count_result(0)

        output_file = tmp_path / "seed_speakers_generated.sql"  # type: ignore[operator]
        original_content = "-- existing seed data\nINSERT INTO speakers ...;\n"
        output_file.write_text(original_content)

        generate_all_seeds(str(tmp_path))

        assert output_file.read_text() == original_content


class TestGenerateSpeakersSeed:
    """generate_speakers_seedメソッドのテスト"""

    def test_generates_insert_statements(self, mock_engine: MagicMock) -> None:
        """デデュプ済みデータから正しいINSERT文が生成される"""
        mock_conn = _setup_conn(mock_engine)
        mock_conn.execute.return_value = _make_mock_result(
            ["name", "name_yomi"],
            [
                ("田中太郎", "たなかたろう"),
                ("佐藤花子", None),
            ],
        )

        gen = SeedGenerator()
        result = gen.generate_speakers_seed()

        assert "INSERT INTO speakers (name, name_yomi)" in result
        assert "WHERE NOT EXISTS" in result
        assert "'田中太郎'" in result
        assert "'たなかたろう'" in result
        # NULLのname_yomiが正しく処理される
        assert "NULL" in result
        assert "'佐藤花子'" in result

    def test_dedup_prefers_name_yomi(self, mock_engine: MagicMock) -> None:
        """name_yomiありが優先される（クエリレベルのDISTINCT ONで保証）"""
        mock_conn = _setup_conn(mock_engine)
        mock_conn.execute.return_value = _make_mock_result(
            ["name", "name_yomi"],
            [("田中太郎", "たなかたろう")],
        )

        gen = SeedGenerator()
        result = gen.generate_speakers_seed()

        assert result.count("INSERT INTO speakers") == 1
        assert "'たなかたろう'" in result

    def test_header_comment_includes_count(self, mock_engine: MagicMock) -> None:
        """ヘッダコメントに件数が含まれる"""
        mock_conn = _setup_conn(mock_engine)
        mock_conn.execute.return_value = _make_mock_result(
            ["name", "name_yomi"],
            [("テスト", None)],
        )

        gen = SeedGenerator()
        result = gen.generate_speakers_seed()

        assert "1 unique speakers" in result
        assert "deduped by name" in result

    def test_returns_empty_string_when_no_data(self, mock_engine: MagicMock) -> None:
        """データが0件の場合は空文字を返す"""
        mock_conn = _setup_conn(mock_engine)
        mock_conn.execute.return_value = _make_mock_result(
            ["name", "name_yomi"],
            [],
        )

        gen = SeedGenerator()
        result = gen.generate_speakers_seed()

        assert result == ""


class TestGenerateSpeakerPoliticianLinksSeed:
    """generate_speaker_politician_links_seedメソッドのテスト"""

    def test_generates_politician_update_statements(
        self, mock_engine: MagicMock
    ) -> None:
        """政治家紐付けのUPDATE文が正しく生成される"""
        mock_conn = _setup_conn(mock_engine)
        pol_result = _make_mock_result(
            [
                "name",
                "politician_name",
                "matching_confidence",
                "matching_reason",
                "is_manually_verified",
            ],
            [
                ("田中太郎", "田中太郎（政治家）", 0.95, "完全一致", True),
            ],
        )
        skip_result = _make_mock_result(
            ["name", "skip_reason"],
            [],
        )
        mock_conn.execute.side_effect = [pol_result, skip_result]

        gen = SeedGenerator()
        result = gen.generate_speaker_politician_links_seed()

        assert "UPDATE speakers SET" in result
        assert "politician_id = (SELECT id FROM politicians" in result
        assert "is_politician = true" in result
        assert "matching_confidence = 0.95" in result
        assert "'完全一致'" in result
        assert "is_manually_verified = true" in result

    def test_generates_skip_reason_update_statements(
        self, mock_engine: MagicMock
    ) -> None:
        """非政治家分類のUPDATE文が正しく生成される"""
        mock_conn = _setup_conn(mock_engine)
        pol_result = _make_mock_result(
            [
                "name",
                "politician_name",
                "matching_confidence",
                "matching_reason",
                "is_manually_verified",
            ],
            [],
        )
        skip_result = _make_mock_result(
            ["name", "skip_reason"],
            [("議長", "役職名のため除外")],
        )
        mock_conn.execute.side_effect = [pol_result, skip_result]

        gen = SeedGenerator()
        result = gen.generate_speaker_politician_links_seed()

        assert "is_politician = false" in result
        assert "skip_reason = '役職名のため除外'" in result
        assert "name = '議長'" in result

    def test_sections_are_separated(self, mock_engine: MagicMock) -> None:
        """政治家紐付けと非政治家分類のセクションが分かれている"""
        mock_conn = _setup_conn(mock_engine)
        pol_result = _make_mock_result(
            [
                "name",
                "politician_name",
                "matching_confidence",
                "matching_reason",
                "is_manually_verified",
            ],
            [("田中太郎", "田中太郎（政治家）", 0.9, "一致", False)],
        )
        skip_result = _make_mock_result(
            ["name", "skip_reason"],
            [("議長", "役職名")],
        )
        mock_conn.execute.side_effect = [pol_result, skip_result]

        gen = SeedGenerator()
        result = gen.generate_speaker_politician_links_seed()

        assert "Speaker-Politician" in result
        assert "非政治家分類" in result

    def test_returns_empty_string_when_no_data(self, mock_engine: MagicMock) -> None:
        """紐付けも非政治家分類も0件の場合は空文字を返す"""
        mock_conn = _setup_conn(mock_engine)
        pol_result = _make_mock_result(
            [
                "name",
                "politician_name",
                "matching_confidence",
                "matching_reason",
                "is_manually_verified",
            ],
            [],
        )
        skip_result = _make_mock_result(
            ["name", "skip_reason"],
            [],
        )
        mock_conn.execute.side_effect = [pol_result, skip_result]

        gen = SeedGenerator()
        result = gen.generate_speaker_politician_links_seed()

        assert result == ""


class TestSqlEscape:
    """SQLエスケープのテスト"""

    def test_single_quote_escaped_in_speaker_name(self, mock_engine: MagicMock) -> None:
        """シングルクォートを含む名前が正しくエスケープされる"""
        mock_conn = _setup_conn(mock_engine)
        mock_conn.execute.return_value = _make_mock_result(
            ["name", "name_yomi"],
            [("O'Brien", None)],
        )

        gen = SeedGenerator()
        result = gen.generate_speakers_seed()

        assert "O''Brien" in result

    def test_single_quote_escaped_in_politician_link(
        self, mock_engine: MagicMock
    ) -> None:
        """政治家紐付けでもシングルクォートがエスケープされる"""
        mock_conn = _setup_conn(mock_engine)
        pol_result = _make_mock_result(
            [
                "name",
                "politician_name",
                "matching_confidence",
                "matching_reason",
                "is_manually_verified",
            ],
            [("O'Brien", "O'Brien（政治家）", 0.9, "テスト's理由", False)],
        )
        skip_result = _make_mock_result(
            ["name", "skip_reason"],
            [],
        )
        mock_conn.execute.side_effect = [pol_result, skip_result]

        gen = SeedGenerator()
        result = gen.generate_speaker_politician_links_seed()

        assert "O''Brien" in result
        assert "O''Brien（政治家）" in result
        assert "テスト''s理由" in result


class TestGenerateAllSeedsIntegration:
    """generate_all_seeds統合テスト"""

    def test_skips_empty_tables(
        self, mock_engine: MagicMock, tmp_path: object, capsys: object
    ) -> None:
        """空テーブルをスキップし、サマリを表示する"""
        mock_conn = _setup_conn(mock_engine)
        mock_conn.execute.return_value = _make_count_result(0)

        generate_all_seeds(str(tmp_path))

        captured = capsys.readouterr()  # type: ignore[union-attr]
        assert "スキップ" in captured.out
        assert "全テーブルが空" in captured.out

    def test_join_zero_does_not_overwrite(
        self, mock_engine: MagicMock, tmp_path: object
    ) -> None:
        """speakersは存在するがpolitician紐付けが0件のケースで上書きしない"""
        links_file = tmp_path / "seed_speaker_politician_links_generated.sql"  # type: ignore[operator]
        original_content = "-- existing links\nUPDATE speakers SET ...;\n"
        links_file.write_text(original_content)

        mock_conn = _setup_conn(mock_engine)
        mock_conn.execute.return_value = _make_count_result(0)

        generate_all_seeds(str(tmp_path))

        assert links_file.read_text() == original_content
