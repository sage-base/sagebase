"""参議院選挙データインポートのDTO."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ImportSangiinElectionInputDto:
    """参議院選挙データインポートの入力DTO."""

    file_path: Path
    """giin.jsonファイルのパス."""
    governing_body_id: int
    """開催主体ID（国会=1）."""
    dry_run: bool = False
    """ドライラン（DB書き込みなし）."""


@dataclass
class ImportSangiinElectionOutputDto:
    """参議院選挙データインポートの出力DTO."""

    total_councillors: int = 0
    """処理した議員総数."""
    elections_created: int = 0
    """作成した選挙レコード数."""
    matched_politicians: int = 0
    """既存政治家にマッチした数."""
    created_politicians: int = 0
    """新規作成した政治家数."""
    created_parties: int = 0
    """新規作成した政党数."""
    skipped_ambiguous: int = 0
    """同姓同名でスキップした数."""
    skipped_duplicate: int = 0
    """重複でスキップした数."""
    election_members_created: int = 0
    """作成したElectionMemberレコード数."""
    errors: int = 0
    """エラー件数."""
    error_details: list[str] = field(default_factory=list)
    """エラー詳細."""
