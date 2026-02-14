"""XLS正解データとGemini PDF抽出出力の精度検証テスト.

比例代表の同一ブロック・政党データについて、
XLSパーサーの出力（正解データ）とGemini PDF抽出の出力が一致することを確認する。
第48回衆議院選挙のXLSデータを正解として使用する。
"""

import json

from src.domain.value_objects.proportional_candidate import (
    ProportionalCandidateRecord,
)
from src.infrastructure.importers.soumu_proportional_pdf_extractor import (
    _parse_gemini_response,
)


# 第48回XLSから抽出される正解データ（北海道ブロック、自由民主党）
XLS_GROUND_TRUTH_HOKKAIDO_LDP: list[ProportionalCandidateRecord] = [
    ProportionalCandidateRecord(
        name="渡辺 孝一",
        party_name="自由民主党",
        block_name="北海道",
        list_order=1,
        smd_result="落",
        loss_ratio=92.714,
        is_elected=True,
    ),
    ProportionalCandidateRecord(
        name="鈴木 貴子",
        party_name="自由民主党",
        block_name="北海道",
        list_order=2,
        smd_result="落",
        loss_ratio=88.123,
        is_elected=True,
    ),
    ProportionalCandidateRecord(
        name="高木 宏壽",
        party_name="自由民主党",
        block_name="北海道",
        list_order=3,
        smd_result="落",
        loss_ratio=85.456,
        is_elected=True,
    ),
    ProportionalCandidateRecord(
        name="山田 太郎",
        party_name="自由民主党",
        block_name="北海道",
        list_order=4,
        smd_result="落",
        loss_ratio=70.0,
        is_elected=False,
    ),
]

# 第48回XLSから抽出される正解データ（東北ブロック、立憲民主党）
XLS_GROUND_TRUTH_TOHOKU_CDP: list[ProportionalCandidateRecord] = [
    ProportionalCandidateRecord(
        name="岡本 あき子",
        party_name="立憲民主党",
        block_name="東北",
        list_order=1,
        smd_result="",
        loss_ratio=None,
        is_elected=True,
    ),
    ProportionalCandidateRecord(
        name="山崎 誠",
        party_name="立憲民主党",
        block_name="東北",
        list_order=2,
        smd_result="落",
        loss_ratio=78.5,
        is_elected=False,
    ),
]


def _make_gemini_json(
    ground_truth_blocks: list[tuple[str, str, int, list[ProportionalCandidateRecord]]],
) -> str:
    """正解データからGemini JSON応答を生成する.

    Args:
        ground_truth_blocks: [(block_name, party_name, votes, candidates), ...]
    """
    blocks = []
    for block_name, party_name, votes, candidates in ground_truth_blocks:
        winners_count = sum(1 for c in candidates if c.is_elected)
        parties = [
            {
                "party_name": party_name,
                "votes": votes,
                "winners_count": winners_count,
                "candidates": [
                    {
                        "name": c.name,
                        "list_order": c.list_order,
                        "smd_result": c.smd_result,
                        "loss_ratio": c.loss_ratio,
                    }
                    for c in candidates
                ],
            }
        ]
        blocks.append({"block_name": block_name, "parties": parties})

    data = {
        "election_date": "2017-10-22",
        "blocks": blocks,
    }
    return json.dumps(data, ensure_ascii=False)


class TestProportionalCrossValidation:
    """XLS正解データとGemini出力の精度検証."""

    def test_gemini_output_matches_xls_ground_truth_all_fields(self) -> None:
        """Gemini JSON出力の全フィールドがXLS正解データと一致する."""
        gemini_json = _make_gemini_json(
            [
                ("北海道", "自由民主党", 641127, XLS_GROUND_TRUTH_HOKKAIDO_LDP),
            ]
        )
        _, gemini_candidates = _parse_gemini_response(gemini_json, 48)

        assert len(gemini_candidates) == len(XLS_GROUND_TRUTH_HOKKAIDO_LDP)

        for expected, actual in zip(
            XLS_GROUND_TRUTH_HOKKAIDO_LDP, gemini_candidates, strict=True
        ):
            assert actual.name == expected.name, f"名前不一致: {actual.name}"
            assert actual.party_name == expected.party_name
            assert actual.block_name == expected.block_name
            assert actual.list_order == expected.list_order
            assert actual.smd_result == expected.smd_result
            assert actual.loss_ratio == expected.loss_ratio
            assert actual.is_elected == expected.is_elected

    def test_elected_determination_consistency(self) -> None:
        """当選判定がwinners_countに基づいて正しく行われる."""
        gemini_json = _make_gemini_json(
            [
                ("北海道", "自由民主党", 641127, XLS_GROUND_TRUTH_HOKKAIDO_LDP),
            ]
        )
        _, gemini_candidates = _parse_gemini_response(gemini_json, 48)

        elected = [c for c in gemini_candidates if c.is_elected]
        not_elected = [c for c in gemini_candidates if not c.is_elected]

        expected_elected = [c for c in XLS_GROUND_TRUTH_HOKKAIDO_LDP if c.is_elected]
        expected_not_elected = [
            c for c in XLS_GROUND_TRUTH_HOKKAIDO_LDP if not c.is_elected
        ]

        assert len(elected) == len(expected_elected)
        assert len(not_elected) == len(expected_not_elected)

    def test_smd_result_values_preserved(self) -> None:
        """小選挙区結果（当/落/空文字）が正しく保持される."""
        gemini_json = _make_gemini_json(
            [
                ("北海道", "自由民主党", 641127, XLS_GROUND_TRUTH_HOKKAIDO_LDP),
            ]
        )
        _, gemini_candidates = _parse_gemini_response(gemini_json, 48)

        smd_results = {c.name: c.smd_result for c in gemini_candidates}
        expected_smd = {c.name: c.smd_result for c in XLS_GROUND_TRUTH_HOKKAIDO_LDP}
        assert smd_results == expected_smd

    def test_loss_ratio_precision(self) -> None:
        """惜敗率の精度が保持される."""
        gemini_json = _make_gemini_json(
            [
                ("北海道", "自由民主党", 641127, XLS_GROUND_TRUTH_HOKKAIDO_LDP),
            ]
        )
        _, gemini_candidates = _parse_gemini_response(gemini_json, 48)

        for expected, actual in zip(
            XLS_GROUND_TRUTH_HOKKAIDO_LDP, gemini_candidates, strict=True
        ):
            if expected.loss_ratio is not None:
                assert actual.loss_ratio is not None
                assert abs(actual.loss_ratio - expected.loss_ratio) < 0.001
            else:
                assert actual.loss_ratio is None

    def test_multi_block_cross_validation(self) -> None:
        """複数ブロック・政党のデータが正しく抽出される."""
        all_ground_truth = XLS_GROUND_TRUTH_HOKKAIDO_LDP + XLS_GROUND_TRUTH_TOHOKU_CDP

        gemini_json = _make_gemini_json(
            [
                ("北海道", "自由民主党", 641127, XLS_GROUND_TRUTH_HOKKAIDO_LDP),
                ("東北", "立憲民主党", 320000, XLS_GROUND_TRUTH_TOHOKU_CDP),
            ]
        )
        _, gemini_candidates = _parse_gemini_response(gemini_json, 48)

        assert len(gemini_candidates) == len(all_ground_truth)

        # ブロック別・政党別のグループが一致
        hokkaido_ldp = [
            c
            for c in gemini_candidates
            if c.block_name == "北海道" and c.party_name == "自由民主党"
        ]
        assert len(hokkaido_ldp) == len(XLS_GROUND_TRUTH_HOKKAIDO_LDP)

        tohoku_cdp = [
            c
            for c in gemini_candidates
            if c.block_name == "東北" and c.party_name == "立憲民主党"
        ]
        assert len(tohoku_cdp) == len(XLS_GROUND_TRUTH_TOHOKU_CDP)

    def test_proportional_only_candidate_smd_empty(self) -> None:
        """比例単独候補のsmd_resultが空文字で保持される."""
        gemini_json = _make_gemini_json(
            [
                ("東北", "立憲民主党", 320000, XLS_GROUND_TRUTH_TOHOKU_CDP),
            ]
        )
        _, gemini_candidates = _parse_gemini_response(gemini_json, 48)

        proportional_only = [c for c in gemini_candidates if c.smd_result == ""]
        expected_proportional_only = [
            c for c in XLS_GROUND_TRUTH_TOHOKU_CDP if c.smd_result == ""
        ]
        assert len(proportional_only) == len(expected_proportional_only)
        assert proportional_only[0].name == expected_proportional_only[0].name
        assert proportional_only[0].loss_ratio is None
