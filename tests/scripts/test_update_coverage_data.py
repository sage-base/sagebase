"""update_coverage_data スクリプトのユニットテスト.

BQへの実接続は行わず、build_coverage_json のデータ変換ロジックのみをテストする。
"""

from scripts.update_coverage_data import (
    _build_prefecture_entry,
    _calculate_year_span,
    _count_covered_municipalities,
    _count_covered_prefectures,
    _extract_year,
    _format_number_jp,
    build_coverage_json,
)

from src.domain.entities.bq_coverage_stats import BQCoverageSummary


def _make_summary(**overrides) -> BQCoverageSummary:
    """テスト用のBQCoverageSummaryを生成."""
    base: BQCoverageSummary = {
        "national": {"conversation_count": 10_800_000, "meeting_count": 102_000},
        "local_total": {"conversation_count": 400_000, "meeting_count": 6_600},
        "politician_stats": {
            "national_politician_count": 6_400,
            "local_politician_count": 5_500,
        },
        "proposal_stats": {"national_proposal_count": 15_000},
        "speaker_linkage": {
            "total_speakers": 39_805,
            "matched_speakers": 5_081,
            "government_official_count": 14_200,
            "linkage_rate": 89.5,
        },
        "parliamentary_group_mapping": {
            "total_parliamentary_groups": 1_200,
            "mapped_parliamentary_groups": 1_080,
            "mapping_rate": 90.0,
        },
        "party_group_counts": {
            "political_party_count": 195,
            "parliamentary_group_count": 1_200,
        },
        "national_period": {
            "earliest_date": "1947-05-20",
            "latest_date": "2026-03-15",
        },
        "local_period": {
            "earliest_date": "1963-01-10",
            "latest_date": "2025-12-20",
        },
        "prefecture_stats": [
            {
                "prefecture": "東京都",
                "governing_body_count": 5,
                "conversation_count": 120_000,
                "meeting_count": 2_000,
                "politician_count": 800,
                "speaker_count": 1_500,
                "matched_speaker_count": 1_200,
                "linkage_rate": 80.0,
                "proposal_count": 500,
                "earliest_date": "1963-01-10",
                "latest_date": "2025-12-20",
            },
            {
                "prefecture": "大阪府",
                "governing_body_count": 4,
                "conversation_count": 80_000,
                "meeting_count": 1_500,
                "politician_count": 600,
                "speaker_count": 1_000,
                "matched_speaker_count": 800,
                "linkage_rate": 80.0,
                "proposal_count": 300,
                "earliest_date": "1983-04-01",
                "latest_date": "2025-11-30",
            },
        ],
    }
    base.update(overrides)  # type: ignore[typeddict-item]
    return base


class TestFormatNumberJp:
    """_format_number_jp のテスト."""

    def test_ten_million_plus(self):
        assert _format_number_jp(10_800_000) == "1,080万+"

    def test_hundred_thousand(self):
        assert _format_number_jp(102_000) == "10.2万+"

    def test_integer_man(self):
        assert _format_number_jp(400_000) == "40万+"

    def test_under_ten_thousand(self):
        assert _format_number_jp(6_400) == "6,400"

    def test_zero(self):
        assert _format_number_jp(0) == "0"


class TestExtractYear:
    """_extract_year のテスト."""

    def test_standard_date(self):
        assert _extract_year("2025-12-31") == 2025

    def test_none(self):
        assert _extract_year(None) is None

    def test_empty_string(self):
        assert _extract_year("") is None


class TestCalculateYearSpan:
    """_calculate_year_span のテスト."""

    def test_span(self):
        assert _calculate_year_span("1947-05-20", "2026-03-15") == "80"

    def test_same_year(self):
        assert _calculate_year_span("2025-01-01", "2025-12-31") == "1"

    def test_none_input(self):
        assert _calculate_year_span(None, "2025-12-31") is None


class TestCountCoveredPrefectures:
    """_count_covered_prefectures のテスト."""

    def test_count(self):
        stats = [
            {"conversation_count": 100},
            {"conversation_count": 0},
            {"conversation_count": 50},
        ]
        assert _count_covered_prefectures(stats) == 2

    def test_empty(self):
        assert _count_covered_prefectures([]) == 0


class TestCountCoveredMunicipalities:
    """_count_covered_municipalities のテスト."""

    def test_sum(self):
        stats = [
            {"governing_body_count": 5},
            {"governing_body_count": 3},
        ]
        assert _count_covered_municipalities(stats) == 8


class TestBuildPrefectureEntry:
    """_build_prefecture_entry のテスト."""

    def test_timeline_calculation(self):
        p = {
            "prefecture": "東京都",
            "conversation_count": 100,
            "meeting_count": 50,
            "politician_count": 30,
            "speaker_count": 20,
            "matched_speaker_count": 15,
            "linkage_rate": 75.0,
            "proposal_count": 10,
            "governing_body_count": 5,
            "earliest_date": "1963-01-01",
            "latest_date": "2025-12-31",
        }
        result = _build_prefecture_entry(p, 1947, 2026)
        assert result["earliest_year"] == 1963
        assert result["latest_year"] == 2025
        assert result["timeline_left"] == 20  # (1963-1947)/79*100 ≈ 20
        assert result["timeline_width"] == 80  # (2025-1963+1)/79*100 ≈ 80
        assert result["timeline_intensity"] == "intensity-high"  # 62年 > 50

    def test_short_span_intensity(self):
        p = {
            "prefecture": "テスト県",
            "conversation_count": 10,
            "meeting_count": 5,
            "politician_count": 3,
            "speaker_count": 2,
            "matched_speaker_count": 1,
            "linkage_rate": 50.0,
            "proposal_count": 0,
            "governing_body_count": 1,
            "earliest_date": "2020-01-01",
            "latest_date": "2025-12-31",
        }
        result = _build_prefecture_entry(p, 1947, 2026)
        assert result["timeline_intensity"] == "intensity-low"  # 5年 < 25

    def test_no_dates(self):
        p = {
            "prefecture": "テスト県",
            "conversation_count": 10,
            "meeting_count": 5,
            "politician_count": 3,
            "speaker_count": 2,
            "matched_speaker_count": 1,
            "linkage_rate": 50.0,
            "proposal_count": 0,
            "governing_body_count": 1,
            "earliest_date": None,
            "latest_date": None,
        }
        result = _build_prefecture_entry(p, 1947, 2026)
        assert result["timeline_left"] is None
        assert result["timeline_width"] is None


class TestBuildCoverageJson:
    """build_coverage_json のテスト."""

    def test_hero_national(self):
        summary = _make_summary()
        result = build_coverage_json(summary)

        national = result["hero"]["national"]
        assert national["conversation_count"] == 10_800_000
        assert national["conversation_count_display"] == "1,080万+"
        assert national["earliest_year"] == 1947
        assert national["latest_year"] == 2026
        assert national["year_span"] == "80"

    def test_hero_local(self):
        summary = _make_summary()
        result = build_coverage_json(summary)

        local = result["hero"]["local"]
        assert local["covered_prefectures"] == 2
        assert local["total_prefectures"] == 47
        assert local["covered_municipalities"] == 9  # 5 + 4

    def test_totals(self):
        summary = _make_summary()
        result = build_coverage_json(summary)

        totals = result["totals"]
        assert totals["conversation_count"] == 11_200_000
        assert totals["meeting_count"] == 108_600
        assert totals["politician_count"] == 11_900
        assert totals["party_count"] == 195

    def test_quality_speaker_linkage(self):
        summary = _make_summary()
        result = build_coverage_json(summary)

        sl = result["quality"]["speaker_linkage"]
        assert sl["rate"] == 89.5
        assert sl["total_speakers"] == 39_805

    def test_quality_pg_mapping(self):
        summary = _make_summary()
        result = build_coverage_json(summary)

        pg = result["quality"]["parliamentary_group_mapping"]
        assert pg["rate"] == 90.0
        assert pg["total_groups"] == 1_200

    def test_prefecture_ranking_sorted_by_conversation_count(self):
        summary = _make_summary()
        result = build_coverage_json(summary)

        ranking = result["prefecture_ranking"]
        assert len(ranking) == 2
        assert ranking[0]["name"] == "東京都"
        assert ranking[1]["name"] == "大阪府"

    def test_prefecture_ranking_includes_timeline_data(self):
        summary = _make_summary()
        result = build_coverage_json(summary)

        tokyo = result["prefecture_ranking"][0]
        assert "timeline_left" in tokyo
        assert "timeline_width" in tokyo
        assert "timeline_intensity" in tokyo
        assert tokyo["earliest_year"] == 1963

    def test_updated_fields_present(self):
        summary = _make_summary()
        result = build_coverage_json(summary)

        assert "updated_at" in result
        assert "updated_date" in result
        assert "T" in result["updated_at"]

    def test_empty_prefecture_stats(self):
        """都道府県データが空の場合でもエラーにならない."""
        summary = _make_summary(prefecture_stats=[])
        result = build_coverage_json(summary)

        assert result["hero"]["local"]["covered_prefectures"] == 0
        assert result["prefecture_ranking"] == []
