"""SEEDファイル生成モジュールのテスト"""

import io

from unittest.mock import MagicMock, patch

import pytest

from src.seed_generator import SeedGenerator


class TestSeedGenerator:
    """SeedGeneratorのテスト"""

    @pytest.fixture
    def seed_generator(self):
        """SeedGeneratorのインスタンスを返すフィクスチャ"""
        with patch("src.seed_generator.get_db_engine") as mock_get_db_engine:
            mock_engine = MagicMock()
            mock_get_db_engine.return_value = mock_engine
            generator = SeedGenerator()
            return generator

    def test_generate_governing_bodies_seed(self, seed_generator):
        """governing_bodiesのSEED生成テスト"""
        # モックデータの準備
        mock_rows = [
            ("日本国", "国", None, "国"),
            ("東京都", "都道府県", "130001", "都道府県"),
            ("大阪府", "都道府県", "270008", "都道府県"),
        ]

        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter(mock_rows))
        mock_result.keys.return_value = [
            "name",
            "type",
            "organization_code",
            "organization_type",
        ]

        mock_conn = MagicMock()
        mock_conn.execute.return_value = mock_result
        seed_generator.engine = MagicMock()
        seed_generator.engine.connect.return_value.__enter__.return_value = mock_conn

        # 実行
        output = io.StringIO()
        result = seed_generator.generate_governing_bodies_seed(output=output)

        # 検証
        assert "INSERT INTO governing_bodies " in result
        assert "(name, type, organization_code, organization_type) VALUES" in result
        assert "('日本国', '国', NULL, '国')" in result
        assert "('東京都', '都道府県', '130001', '都道府県')" in result
        assert "('大阪府', '都道府県', '270008', '都道府県')" in result
        assert "ON CONFLICT (name, type) DO NOTHING;" in result

    def test_generate_conferences_seed(self, seed_generator):
        """conferencesのSEED生成テスト"""
        # モックデータの準備
        mock_rows = [
            ("衆議院", 1, "日本国", "国"),
            ("参議院", 1, "日本国", "国"),
            (
                "東京都議会",
                2,
                "東京都",
                "都道府県",
            ),
        ]

        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter(mock_rows))
        mock_result.keys.return_value = [
            "name",
            "governing_body_id",
            "governing_body_name",
            "governing_body_type",
        ]

        mock_conn = MagicMock()
        mock_conn.execute.return_value = mock_result
        seed_generator.engine = MagicMock()
        seed_generator.engine.connect.return_value.__enter__.return_value = mock_conn

        # 実行
        output = io.StringIO()
        result = seed_generator.generate_conferences_seed(output=output)

        # 検証
        assert "INSERT INTO conferences " in result
        assert "(name, governing_body_id) VALUES" in result
        assert "('衆議院'," in result
        assert "('参議院'," in result
        assert "('東京都議会'," in result
        assert "ON CONFLICT (name, governing_body_id, term) DO NOTHING;" in result

    def test_generate_political_parties_seed(self, seed_generator):
        """political_partiesのSEED生成テスト"""
        # モックデータの準備
        mock_rows = [
            ("自由民主党", "https://www.jimin.jp/members"),
            ("立憲民主党", "https://cdp-japan.jp/members"),
            ("日本維新の会", None),
        ]

        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter(mock_rows))
        mock_result.keys.return_value = ["name", "members_list_url"]

        mock_conn = MagicMock()
        mock_conn.execute.return_value = mock_result
        seed_generator.engine = MagicMock()
        seed_generator.engine.connect.return_value.__enter__.return_value = mock_conn

        # 実行
        output = io.StringIO()
        result = seed_generator.generate_political_parties_seed(output=output)

        # 検証
        assert "INSERT INTO political_parties (name, members_list_url) VALUES" in result
        assert "('自由民主党', 'https://www.jimin.jp/members')" in result
        assert "('立憲民主党', 'https://cdp-japan.jp/members')" in result
        assert "('日本維新の会', NULL)" in result
        assert "ON CONFLICT (name) DO NOTHING;" in result

    def test_generate_parliamentary_groups_seed(self, seed_generator):
        """parliamentary_groupsのSEED生成テスト"""
        # モックデータの準備
        mock_rows = [
            ("自由民主党", None, None, True, "東京都議会", "東京都", "都道府県"),
            (
                "都民ファーストの会",
                "https://example.com",
                "都議会第一会派",
                True,
                "東京都議会",
                "東京都",
                "都道府県",
            ),
        ]

        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter(mock_rows))
        mock_result.keys.return_value = [
            "name",
            "url",
            "description",
            "is_active",
            "conference_name",
            "governing_body_name",
            "governing_body_type",
        ]

        mock_conn = MagicMock()
        mock_conn.execute.return_value = mock_result
        seed_generator.engine = MagicMock()
        seed_generator.engine.connect.return_value.__enter__.return_value = mock_conn

        # 実行
        output = io.StringIO()
        result = seed_generator.generate_parliamentary_groups_seed(output=output)

        # 検証
        assert "INSERT INTO parliamentary_groups " in result
        assert "(name, conference_id, url, description, is_active) VALUES" in result
        assert "('自由民主党'," in result
        assert "('都民ファーストの会'," in result
        assert "NULL, NULL, true)" in result
        assert "'https://example.com', '都議会第一会派', true)" in result
        assert "ON CONFLICT (name, conference_id) DO NOTHING;" in result

    def test_generate_politicians_seed(self, seed_generator):
        """政治家SEEDファイル生成のテスト"""
        # モックデータ
        mock_rows = [
            (
                "山田太郎",
                "衆議院議員",
                "東京都",
                "東京1区",
                "https://example.com/yamada",
                "自由民主党",
            ),
            (
                "佐藤花子",
                "参議院議員",
                "大阪府",
                "大阪府",
                "https://example.com/sato",
                "立憲民主党",
            ),
            (
                "鈴木一郎",
                "衆議院議員",
                "北海道",
                "北海道1区",
                "https://example.com/suzuki",
                None,
            ),
        ]

        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter(mock_rows))
        mock_result.keys.return_value = [
            "name",
            "position",
            "prefecture",
            "electoral_district",
            "profile_url",
            "party_name",
        ]

        mock_conn = MagicMock()
        mock_conn.execute.return_value = mock_result
        seed_generator.engine = MagicMock()
        seed_generator.engine.connect.return_value.__enter__.return_value = mock_conn

        # 実行
        result = seed_generator.generate_politicians_seed()

        # 検証
        assert "-- politicians seed data" in result
        assert "INSERT INTO politicians" in result
        assert "-- 自由民主党" in result
        assert (
            "('山田太郎', (SELECT id FROM political_parties "
            "WHERE name = '自由民主党'), '衆議院議員', '東京都', '東京1区', "
            "'https://example.com/yamada')" in result
        )
        assert "-- 立憲民主党" in result
        assert (
            "('佐藤花子', (SELECT id FROM political_parties "
            "WHERE name = '立憲民主党'), '参議院議員', '大阪府', '大阪府', "
            "'https://example.com/sato')" in result
        )
        assert "-- 無所属" in result
        assert (
            "('鈴木一郎', NULL, '衆議院議員', '北海道', '北海道1区', "
            "'https://example.com/suzuki')" in result
        )
        assert ";" in result

    def test_generate_election_members_seed(self, seed_generator):
        """election_membersのSEED生成テスト"""
        # モックデータの準備
        mock_rows = [
            (1, 10, "当選", 85000, 1, 50, "国会", "国", "山田太郎"),
            (1, 11, "落選", 42000, 2, 50, "国会", "国", "佐藤花子"),
            (2, 12, "当選", None, None, 10, "東京都議会", "都道府県", "鈴木一郎"),
        ]

        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter(mock_rows))
        mock_result.keys.return_value = [
            "election_id",
            "politician_id",
            "result",
            "votes",
            "rank",
            "term_number",
            "governing_body_name",
            "governing_body_type",
            "politician_name",
        ]

        mock_conn = MagicMock()
        mock_conn.execute.return_value = mock_result
        seed_generator.engine = MagicMock()
        seed_generator.engine.connect.return_value.__enter__.return_value = mock_conn

        # 実行
        result = seed_generator.generate_election_members_seed()

        # 検証
        assert "-- election_members seed data" in result
        assert "INSERT INTO election_members" in result
        assert "(election_id, politician_id, result, votes, rank) VALUES" in result
        assert "-- 国会 (国) 第50回" in result
        assert "-- 東京都議会 (都道府県) 第10回" in result
        assert "'当選', 85000, 1)" in result
        assert "'落選', 42000, 2)" in result
        assert "'当選', NULL, NULL)" in result
        assert (
            "ON CONFLICT (election_id, politician_id) DO UPDATE SET "
            "result = EXCLUDED.result, "
            "votes = EXCLUDED.votes, "
            "rank = EXCLUDED.rank;"
        ) in result
        # サブクエリの検証
        assert "SELECT id FROM elections WHERE governing_body_id" in result
        assert "SELECT id FROM governing_bodies WHERE name" in result
        assert "SELECT id FROM politicians WHERE name" in result

    def test_generate_election_members_seed_sql_injection(self, seed_generator):
        """election_membersのSQLインジェクション対策テスト"""
        mock_rows = [
            (
                1,
                10,
                "当選",
                1000,
                1,
                50,
                "国会",
                "国",
                "O'Brien太郎",
            ),
        ]

        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter(mock_rows))
        mock_result.keys.return_value = [
            "election_id",
            "politician_id",
            "result",
            "votes",
            "rank",
            "term_number",
            "governing_body_name",
            "governing_body_type",
            "politician_name",
        ]

        mock_conn = MagicMock()
        mock_conn.execute.return_value = mock_result
        seed_generator.engine = MagicMock()
        seed_generator.engine.connect.return_value.__enter__.return_value = mock_conn

        # 実行
        result = seed_generator.generate_election_members_seed()

        # 検証 - シングルクォートがエスケープされていること
        assert "O''Brien太郎" in result

    def test_generate_election_members_seed_empty(self, seed_generator):
        """election_membersの空データテスト"""
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))
        mock_result.keys.return_value = []

        mock_conn = MagicMock()
        mock_conn.execute.return_value = mock_result
        seed_generator.engine = MagicMock()
        seed_generator.engine.connect.return_value.__enter__.return_value = mock_conn

        # 実行
        result = seed_generator.generate_election_members_seed()

        # 検証 - ヘッダーとフッターのみが含まれること
        assert "INSERT INTO election_members" in result
        assert "ON CONFLICT (election_id, politician_id) DO UPDATE SET" in result

    def test_sql_injection_protection(self, seed_generator):
        """SQLインジェクション対策のテスト"""
        # 悪意のあるデータ
        mock_rows = [
            ("悪意'; DROP TABLE--", "国", None, "国"),
            ("O'Reilly", "都道府県", "130001", "都道府県"),
        ]

        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter(mock_rows))
        mock_result.keys.return_value = [
            "name",
            "type",
            "organization_code",
            "organization_type",
        ]

        mock_conn = MagicMock()
        mock_conn.execute.return_value = mock_result
        seed_generator.engine = MagicMock()
        seed_generator.engine.connect.return_value.__enter__.return_value = mock_conn

        # 実行
        result = seed_generator.generate_governing_bodies_seed()

        # 検証 - シングルクォートがエスケープされていること
        assert "('悪意''; DROP TABLE--', '国', NULL, '国')" in result
        assert "('O''Reilly', '都道府県', '130001', '都道府県')" in result

    def test_empty_data(self, seed_generator):
        """空データの場合のテスト"""
        # 空のデータ
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))
        mock_result.keys.return_value = []

        mock_conn = MagicMock()
        mock_conn.execute.return_value = mock_result
        seed_generator.engine = MagicMock()
        seed_generator.engine.connect.return_value.__enter__.return_value = mock_conn

        # 実行
        result = seed_generator.generate_governing_bodies_seed()

        # 検証 - ヘッダーとフッターのみが含まれること
        assert "INSERT INTO governing_bodies" in result
        assert "ON CONFLICT (name, type) DO NOTHING;" in result

    @patch("src.seed_generator.open", create=True)
    @patch("src.seed_generator.get_db_engine")
    def test_generate_all_seeds(self, mock_get_db_engine, mock_open):
        """全SEEDファイル生成のテスト"""
        # DB接続のモック
        mock_engine = MagicMock()
        mock_get_db_engine.return_value = mock_engine

        # データベースクエリのモック
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))
        mock_result.keys.return_value = []

        mock_conn = MagicMock()
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        # ファイル書き込みのモック
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # 実行
        from src.seed_generator import generate_all_seeds

        generate_all_seeds()

        # 検証 - 各ファイルが作成されること
        assert mock_open.call_count == 8  # 8つのSEEDファイル
        expected_files = [
            "database/seed_governing_bodies_generated.sql",
            "database/seed_elections_generated.sql",
            "database/seed_conferences_generated.sql",
            "database/seed_political_parties_generated.sql",
            "database/seed_parliamentary_groups_generated.sql",
            "database/seed_meetings_generated.sql",
            "database/seed_politicians_generated.sql",
            "database/seed_election_members_generated.sql",
        ]
        for call, expected_file in zip(
            mock_open.call_args_list, expected_files, strict=False
        ):
            assert call[0][0] == expected_file
