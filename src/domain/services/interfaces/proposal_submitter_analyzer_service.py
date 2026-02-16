"""議案提出者分析サービスのインターフェース定義.

提出者文字列を解析し、SubmitterType判定と
議員/会派マッチングを行うサービスの抽象化。
"""

from typing import Protocol

from src.domain.value_objects.submitter_analysis_result import SubmitterAnalysisResult


class IProposalSubmitterAnalyzerService(Protocol):
    """議案提出者分析サービスのインターフェース.

    提出者文字列を解析して種別判定・マッチングを行う。
    Infrastructure層で具体的な実装が提供される。

    実装クラス:
        - RuleBasedProposalSubmitterAnalyzer: ルールベースの実装
    """

    async def analyze(
        self,
        submitter_name: str,
        conference_id: int,
    ) -> list[SubmitterAnalysisResult]:
        """提出者文字列を解析してマッチングする.

        提出者文字列をパースし、各名前に対して種別判定・マッチングを行う。
        カンマ区切りの場合は複数の結果を返す。

        Args:
            submitter_name: 提出者の文字列（例: 「田中太郎」「熊代昭彦,谷畑孝」）
            conference_id: 会議体ID（候補絞り込みに使用）

        Returns:
            list[SubmitterAnalysisResult]: 分析結果リスト
        """
        ...
