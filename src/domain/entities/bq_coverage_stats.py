"""BQカバレッジ集計用エンティティ定義.

国会/地方議会を分離した集計結果を表現するTypedDict群。
"""

from typing import TypedDict


class ConversationMeetingStats(TypedDict):
    """発言数・会議数の集計結果.

    国会 / 都道府県 / 市区町村 の各レベルで使用。
    """

    conversation_count: int
    meeting_count: int


class PoliticianStats(TypedDict):
    """政治家数の集計結果."""

    national_politician_count: int
    local_politician_count: int


class ProposalStats(TypedDict):
    """議案数の集計結果（国会のみ）."""

    national_proposal_count: int


class DataPeriod(TypedDict):
    """データ収録期間."""

    earliest_date: str | None
    latest_date: str | None


class SpeakerLinkageStats(TypedDict):
    """発言者→政治家紐付け統計."""

    total_speakers: int
    matched_speakers: int
    government_official_count: int
    linkage_rate: float


class ParliamentaryGroupMappingStats(TypedDict):
    """会派マッピング統計."""

    total_parliamentary_groups: int
    mapped_parliamentary_groups: int
    mapping_rate: float


class PartyGroupCounts(TypedDict):
    """政党・会派の登録数."""

    political_party_count: int
    parliamentary_group_count: int


class PrefectureCoverageStats(TypedDict):
    """都道府県別カバレッジ統計.

    4軸: 発言・政治家・紐付け・議案
    """

    prefecture: str
    governing_body_count: int
    conversation_count: int
    meeting_count: int
    politician_count: int
    speaker_count: int
    matched_speaker_count: int
    linkage_rate: float
    proposal_count: int
    earliest_date: str | None
    latest_date: str | None


class BQCoverageSummary(TypedDict):
    """BQカバレッジ集計の全体サマリー.

    カバレッジページで必要な全指標を1つにまとめた構造。
    """

    # 発言数・会議数（国会 / 地方合計）
    national: ConversationMeetingStats
    local_total: ConversationMeetingStats

    # 政治家数
    politician_stats: PoliticianStats

    # 議案数（国会）
    proposal_stats: ProposalStats

    # 発言者紐付け
    speaker_linkage: SpeakerLinkageStats

    # 会派マッピング
    parliamentary_group_mapping: ParliamentaryGroupMappingStats

    # 政党・会派登録数
    party_group_counts: PartyGroupCounts

    # データ収録期間（国会 / 地方）
    national_period: DataPeriod
    local_period: DataPeriod

    # 都道府県別内訳
    prefecture_stats: list[PrefectureCoverageStats]
