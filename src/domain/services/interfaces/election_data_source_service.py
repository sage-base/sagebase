"""選挙データソースサービスのインターフェース — Domain layer."""

from pathlib import Path
from typing import Protocol

from src.domain.value_objects.election_candidate import CandidateRecord, ElectionInfo


class IElectionDataSourceService(Protocol):
    """選挙データソースのインターフェース.

    外部データソース（総務省XLS等）から候補者データを取得する。
    """

    async def fetch_candidates(
        self,
        election_number: int,
        download_dir: Path | None = None,
    ) -> tuple[ElectionInfo | None, list[CandidateRecord]]:
        """選挙番号から候補者データを取得する.

        Args:
            election_number: 選挙回次
            download_dir: ダウンロード先ディレクトリ（省略時はデフォルト）

        Returns:
            (選挙情報, 候補者レコードのリスト)
        """
        ...
