"""参議院選挙データソースサービスのインターフェース."""

from pathlib import Path
from typing import Protocol

from src.domain.value_objects.sangiin_candidate import SangiinCandidateRecord


class ISangiinElectionDataSourceService(Protocol):
    """参議院選挙データソースのプロトコル."""

    async def fetch_councillors(self, file_path: Path) -> list[SangiinCandidateRecord]:
        """ファイルから参議院議員データを取得する.

        Args:
            file_path: データファイルのパス（giin.json）

        Returns:
            参議院議員候補者レコードのリスト
        """
        ...
