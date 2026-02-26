"""衆参会派マッピング調査スクリプトのテスト."""

import json

from pathlib import Path

from scripts.investigate_kaiha_mapping import (
    aggregate_shuugiin_kaiha,
    extract_giin_kaiha,
    extract_sangiin_kaiha,
    extract_shuugiin_kaiha,
    generate_mapping_proposals,
    get_all_shuugiin_kaiha_with_range,
    parse_seed_parliamentary_groups,
    parse_seed_political_parties,
    propose_party_mapping,
)


class TestExtractShuugiinKaiha:
    """gian_summary.jsonから衆議院の会派名を抽出するテスト."""

    def test_基本的な会派抽出(self) -> None:
        """賛成・反対会派を正しく抽出できること."""
        # gian_summary.jsonの実際の構造: nested[0]がサブリスト
        nested_row = [""] * 14 + ["自由民主党; 公明党", "日本共産党"]
        data = [
            [
                "法律案",  # idx 0: 提案種別
                "143",  # idx 1: 回次（文字列）
                "1",  # idx 2: 番号
                "テスト法案",  # idx 3: 題名
                "",  # idx 4
                "可決",  # idx 5: 結果
                "",  # idx 6
                "",  # idx 7: 提出会派
                "",  # idx 8
                "",  # idx 9
                [nested_row],  # idx 10: nested（リストのリスト）
            ],
        ]
        result = extract_shuugiin_kaiha(data)
        assert 143 in result
        assert result[143]["自由民主党"] == 1
        assert result[143]["公明党"] == 1
        assert result[143]["日本共産党"] == 1

    def test_複数回次のデータ(self) -> None:
        """複数の回次にまたがるデータを正しく集計できること."""
        nested_143 = [[""] * 14 + ["自由民主党", "民主党"]]
        nested_144 = [[""] * 14 + ["自由民主党; 公明党", ""]]
        data = [
            ["法律案", "143", "1", "法案A", "", "", "", "", "", "", nested_143],
            ["法律案", "144", "1", "法案B", "", "", "", "", "", "", nested_144],
        ]
        result = extract_shuugiin_kaiha(data)
        assert 143 in result
        assert 144 in result
        assert result[143]["自由民主党"] == 1
        assert result[143]["民主党"] == 1
        assert result[144]["自由民主党"] == 1
        assert result[144]["公明党"] == 1

    def test_空のデータ(self) -> None:
        """空のデータでも例外が発生しないこと."""
        result = extract_shuugiin_kaiha([])
        assert result == {}

    def test_不正なレコードをスキップ(self) -> None:
        """不正なレコードをスキップして処理を続行すること."""
        data = [
            "not_a_list",  # 文字列
            [],  # 空リスト
            [None, "invalid_session"],  # 回次が数値でない
            [
                None,
                "143",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                "not_a_list",
            ],  # nestedがリストでない
        ]
        result = extract_shuugiin_kaiha(data)
        assert result == {}

    def test_会派名のトリム(self) -> None:
        """会派名の前後の空白がトリムされること."""
        nested = [[""] * 14 + [" 自由民主党 ;　公明党　", ""]]
        data = [
            ["法律案", "143", "1", "法案", "", "", "", "", "", "", nested],
        ]
        result = extract_shuugiin_kaiha(data)
        assert "自由民主党" in result[143]
        assert "公明党" in result[143]

    def test_空の会派名をスキップ(self) -> None:
        """空文字列やNullの会派名をスキップすること."""
        nested = [[""] * 14 + [";;自由民主党;;", ""]]
        data = [
            ["法律案", "143", "1", "法案", "", "", "", "", "", "", nested],
        ]
        result = extract_shuugiin_kaiha(data)
        assert "自由民主党" in result[143]


class TestAggregateShuugiinKaiha:
    """回次ごとの会派データをフラットリストに変換するテスト."""

    def test_基本的な変換(self) -> None:
        """正しいCSV出力用フォーマットに変換できること."""
        session_kaiha = {
            143: {"自由民主党": 5, "公明党": 3},
            144: {"自由民主党": 8},
        }
        rows = aggregate_shuugiin_kaiha(session_kaiha)
        assert len(rows) == 3
        assert rows[0] == {"session": 143, "kaiha_name": "公明党", "count": 3}
        assert rows[1] == {"session": 143, "kaiha_name": "自由民主党", "count": 5}
        assert rows[2] == {"session": 144, "kaiha_name": "自由民主党", "count": 8}


class TestGetAllShuugiinKaihaWithRange:
    """全会派名の出現回次範囲を算出するテスト."""

    def test_出現範囲算出(self) -> None:
        """会派ごとの出現回次範囲が正しく算出されること."""
        session_kaiha = {
            140: {"自由民主党": 10},
            143: {"自由民主党": 5, "公明党": 3},
            145: {"公明党": 7},
        }
        result = get_all_shuugiin_kaiha_with_range(session_kaiha)
        assert result["自由民主党"]["min_session"] == 140
        assert result["自由民主党"]["max_session"] == 143
        assert result["自由民主党"]["total_count"] == 15
        assert result["公明党"]["min_session"] == 143
        assert result["公明党"]["max_session"] == 145
        assert result["公明党"]["total_count"] == 10


class TestExtractSangiinKaiha:
    """kaiha.jsonから参議院会派を抽出するテスト."""

    def test_基本的な抽出(self) -> None:
        """ヘッダー行をスキップして会派データを正しく抽出できること."""
        data = [
            ["ID", "会派名", "略称"],  # ヘッダー行
            [1, "自由民主党・国民の声", "自民"],
            [2, "立憲民主・社民", "立民"],
        ]
        result = extract_sangiin_kaiha(data)
        assert len(result) == 2
        assert result[0] == {"name": "自由民主党・国民の声", "short_name": "自民"}
        assert result[1] == {"name": "立憲民主・社民", "short_name": "立民"}

    def test_空データ(self) -> None:
        """ヘッダーのみのデータで空リストを返すこと."""
        data = [["ID", "会派名", "略称"]]
        result = extract_sangiin_kaiha(data)
        assert result == []

    def test_不正な行をスキップ(self) -> None:
        """不正な行をスキップすること."""
        data = [
            ["header"],
            "not_a_list",
            [1],  # フィールド不足
            [1, "正常会派", "正常"],
        ]
        result = extract_sangiin_kaiha(data)
        assert len(result) == 1
        assert result[0]["name"] == "正常会派"


class TestExtractGiinKaiha:
    """giin.jsonから議員の会派略称を抽出するテスト."""

    def test_基本的な抽出(self) -> None:
        """ユニークな会派略称をソート済みで返すこと."""
        data = [
            ["氏名", "本名", "URL", "ふりがな", "会派"],  # ヘッダー
            ["山田太郎", "", "", "やまだたろう", "自民"],
            ["鈴木次郎", "", "", "すずきじろう", "立民"],
            ["佐藤三郎", "", "", "さとうさぶろう", "自民"],  # 重複
        ]
        result = extract_giin_kaiha(data)
        assert sorted(result) == sorted(["自民", "立民"])

    def test_空データ(self) -> None:
        """空データで空リストを返すこと."""
        result = extract_giin_kaiha([["header"]])
        assert result == []


class TestParseSeedParliamentaryGroups:
    """seed_parliamentary_groups_generated.sqlの解析テスト."""

    def test_基本的な解析(self, tmp_path: Path) -> None:
        """seedファイルから会派データを正しく解析できること."""
        sql = (
            "INSERT INTO parliamentary_groups"
            " (name, governing_body_id, url, description, is_active,"
            " chamber) VALUES\n"
            "('自由民主党', (SELECT id FROM governing_bodies"
            " WHERE name = '国会' AND type = '国'), NULL, NULL, true, ''),\n"
            "('無所属の会', (SELECT id FROM governing_bodies"
            " WHERE name = '国会' AND type = '国'), NULL, NULL, false, '')\n"
            "ON CONFLICT (name, governing_body_id, chamber)"
            " DO UPDATE SET url = EXCLUDED.url;"
        )
        seed_file = tmp_path / "seed.sql"
        seed_file.write_text(sql, encoding="utf-8")

        result = parse_seed_parliamentary_groups(seed_file)
        assert len(result) == 2
        assert result[0]["name"] == "自由民主党"
        assert result[0]["governing_body"] == "国会"
        assert result[0]["is_active"] is True
        assert result[1]["name"] == "無所属の会"
        assert result[1]["is_active"] is False


class TestParseSeedPoliticalParties:
    """seed_political_parties_generated.sqlの解析テスト."""

    def test_基本的な解析(self, tmp_path: Path) -> None:
        """政党名一覧を正しく取得できること."""
        sql = """INSERT INTO political_parties (name, members_list_url) VALUES
('自由民主党', 'https://example.com'),
('公明党', NULL),
('無所属', NULL)
ON CONFLICT (name) DO NOTHING;"""
        seed_file = tmp_path / "seed.sql"
        seed_file.write_text(sql, encoding="utf-8")

        result = parse_seed_political_parties(seed_file)
        assert "自由民主党" in result
        assert "公明党" in result
        assert "無所属" in result


class TestProposePartyMapping:
    """会派→政党マッピング提案ロジックのテスト."""

    def test_既存マッピングを優先(self) -> None:
        """既存seedのマッピングがある場合はそれを使用すること."""
        result = propose_party_mapping(
            "自由民主党・無所属の会",
            {"自由民主党・無所属の会": "自由民主党"},
            ["自由民主党"],
        )
        assert result["confidence"] == "existing"
        assert result["proposed_party"] == "自由民主党"

    def test_政党名と完全一致(self) -> None:
        """会派名が政党名と完全一致する場合."""
        result = propose_party_mapping(
            "公明党",
            {},
            ["公明党", "自由民主党"],
        )
        assert result["confidence"] == "high"
        assert result["proposed_party"] == "公明党"

    def test_名前ベースの推定(self) -> None:
        """会派名に政党名が含まれる場合の推定."""
        result = propose_party_mapping(
            "公明党・改革クラブ",
            {},
            ["公明党"],
        )
        assert result["confidence"] == "high"
        assert result["proposed_party"] == "公明党"

    def test_連立会派の検出(self) -> None:
        """複数政党名を含む連立会派の検出."""
        result = propose_party_mapping(
            "民主党・無所属クラブ・国民新党",
            {},
            [],
        )
        assert result["is_coalition"] is True
        assert result["confidence"] == "medium"
        # 最初にマッチした主要政党が設定されること
        assert result["proposed_party"] is not None

    def test_マッピング候補なし(self) -> None:
        """マッピングできない会派."""
        result = propose_party_mapping(
            "21世紀クラブ",
            {},
            [],
        )
        assert result["confidence"] == "unmapped"
        assert result["proposed_party"] is None

    def test_既存マッピングがNULLの場合は推定(self) -> None:
        """既存seedでNULLの場合は名前ベースの推定を行うこと."""
        result = propose_party_mapping(
            "希望の党",
            {"希望の党": None},
            ["希望の党"],
        )
        # NULLマッピングなので完全一致で再推定
        assert result["confidence"] == "high"
        assert result["proposed_party"] == "希望の党"

    def test_社民連合の推定(self) -> None:
        """社会民主党系会派の推定."""
        result = propose_party_mapping(
            "社会民主党・市民連合",
            {},
            ["社会民主党"],
        )
        assert result["proposed_party"] == "社会民主党"
        assert result["confidence"] == "high"

    def test_無所属の推定(self) -> None:
        """無所属系会派の推定."""
        result = propose_party_mapping(
            "無所属の会",
            {},
            ["無所属"],
        )
        assert result["proposed_party"] == "無所属"

    def test_民進党は民主党にマッピング(self) -> None:
        """民進党系の会派は民主党にマッピングされること."""
        result = propose_party_mapping(
            "民進党・無所属クラブ",
            {},
            [],
        )
        assert result["proposed_party"] == "民主党"


class TestGenerateMappingProposals:
    """全会派のマッピング提案生成テスト."""

    def test_基本的な提案生成(self) -> None:
        """各会派に対して提案が生成されること."""
        all_kaiha = {"自由民主党", "日本共産党", "21世紀クラブ"}
        existing_seed = [
            {
                "name": "自由民主党",
                "governing_body": "国会",
                "has_party_id": True,
                "party_name": "自由民主党",
                "is_active": True,
            },
        ]
        known_parties = ["自由民主党", "日本共産党"]

        proposals = generate_mapping_proposals(all_kaiha, existing_seed, known_parties)
        assert len(proposals) == 3

        # 名前でソートされているはず
        names = [p["kaiha_name"] for p in proposals]
        assert names == sorted(names)

        # 各提案にconfidenceが設定されている
        for p in proposals:
            assert "confidence" in p
            assert p["confidence"] in ("existing", "high", "medium", "unmapped")

    def test_空入力(self) -> None:
        """空の入力で空リストを返すこと."""
        proposals = generate_mapping_proposals(set(), [], [])
        assert proposals == []


class TestOutputFormats:
    """出力ファイルのフォーマットテスト."""

    def test_マッピング提案のJSON構造(self) -> None:
        """マッピング提案JSONの構造が正しいこと."""
        proposal = propose_party_mapping("自由民主党", {}, ["自由民主党"])
        required_keys = {
            "kaiha_name",
            "proposed_party",
            "confidence",
            "is_coalition",
            "note",
        }
        assert set(proposal.keys()) == required_keys

    def test_提案のJSONシリアライズ(self) -> None:
        """提案がJSONシリアライズ可能であること."""
        proposals = generate_mapping_proposals(
            {"自由民主党", "テスト会派"},
            [],
            ["自由民主党"],
        )
        # 例外が発生しないことを確認
        json_str = json.dumps(proposals, ensure_ascii=False)
        parsed = json.loads(json_str)
        assert len(parsed) == 2
