"""比例代表選挙データソースサービスのインターフェース — Domain layer."""

from pathlib import Path
from typing import Protocol

from src.domain.value_objects.proportional_candidate import (
    ProportionalCandidateRecord,
    ProportionalElectionInfo,
)


class IProportionalElectionDataSourceService(Protocol):
    """比例代表選挙データソースのインターフェース.

    外部データソース（総務省XLS/PDF等）から比例代表候補者データを取得する。
    """

    async def fetch_proportional_candidates(
        self,
        election_number: int,
        download_dir: Path | None = None,
    ) -> tuple[ProportionalElectionInfo | None, list[ProportionalCandidateRecord]]:
        """選挙番号から比例代表候補者データを取得する.

        Args:
            election_number: 選挙回次
            download_dir: ダウンロード先ディレクトリ（省略時はデフォルト）

        Returns:
            (選挙情報, 比例代表候補者レコードのリスト)
        """
        ...
