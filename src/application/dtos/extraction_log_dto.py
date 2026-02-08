"""抽出ログに関するDTOモジュール。

このモジュールは、抽出ログの検索・統計情報を表現するDTOを提供します。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from src.domain.entities.extraction_log import EntityType


if TYPE_CHECKING:
    from src.domain.entities.extraction_log import ExtractionLog


@dataclass
class ExtractionLogOutputItem:
    """抽出ログの出力アイテム."""

    id: int | None
    entity_type: str
    entity_id: int
    pipeline_version: str
    extracted_data: dict[str, Any]
    confidence_score: float | None
    extraction_metadata: dict[str, Any]
    created_at: datetime | None
    updated_at: datetime | None
    model_name: str | None
    token_count_input: int | None
    token_count_output: int | None
    processing_time_ms: int | None

    @classmethod
    def from_entity(cls, entity: ExtractionLog) -> ExtractionLogOutputItem:
        """エンティティから出力アイテムを生成する."""
        return cls(
            id=entity.id,
            entity_type=entity.entity_type.value,
            entity_id=entity.entity_id,
            pipeline_version=entity.pipeline_version,
            extracted_data=entity.extracted_data,
            confidence_score=entity.confidence_score,
            extraction_metadata=entity.extraction_metadata,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            model_name=entity.model_name,
            token_count_input=entity.token_count_input,
            token_count_output=entity.token_count_output,
            processing_time_ms=entity.processing_time_ms,
        )


@dataclass
class ExtractionLogFilterDTO:
    """抽出ログの検索フィルター。

    Attributes:
        entity_type: エンティティタイプ
        entity_id: エンティティID
        pipeline_version: パイプラインバージョン
        date_from: 検索開始日時
        date_to: 検索終了日時
        min_confidence_score: 最小信頼度スコア
        limit: 取得件数の上限
        offset: 取得開始位置
    """

    entity_type: EntityType | None = None
    entity_id: int | None = None
    pipeline_version: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    min_confidence_score: float | None = None
    limit: int = 100
    offset: int = 0


@dataclass
class PaginatedExtractionLogsDTO:
    """ページネーション付き抽出ログ。

    Attributes:
        logs: 抽出ログのリスト
        total_count: 総件数
        page_size: ページサイズ
        current_offset: 現在のオフセット
    """

    logs: list[ExtractionLogOutputItem]
    total_count: int
    page_size: int
    current_offset: int


@dataclass
class DailyCountDTO:
    """日別件数。

    Attributes:
        date: 日付
        count: 件数
    """

    date: datetime
    count: int


@dataclass
class ExtractionStatisticsDTO:
    """抽出統計情報。

    Attributes:
        total_count: 総件数
        by_entity_type: エンティティタイプ別件数
        by_pipeline_version: パイプラインバージョン別件数
        average_confidence: 平均信頼度スコア
        daily_counts: 日別件数リスト
        confidence_by_pipeline: パイプラインバージョン別平均信頼度
    """

    total_count: int
    by_entity_type: dict[str, int] = field(default_factory=dict)
    by_pipeline_version: dict[str, int] = field(default_factory=dict)
    average_confidence: float | None = None
    daily_counts: list[DailyCountDTO] = field(default_factory=list)
    confidence_by_pipeline: dict[str, float] = field(default_factory=dict)


@dataclass
class ExtractionLogDetailDTO:
    """抽出ログ詳細情報。

    Attributes:
        log: 抽出ログ出力アイテム
        entity_display_name: エンティティの表示名
        extracted_data_formatted: フォーマット済み抽出データ
        metadata_formatted: フォーマット済みメタデータ
    """

    log: ExtractionLogOutputItem
    entity_display_name: str = ""
    extracted_data_formatted: dict[str, Any] = field(default_factory=dict)
    metadata_formatted: dict[str, Any] = field(default_factory=dict)
