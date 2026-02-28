"""BAML-based Politician Matching Service

このモジュールは、BAMLを使用して政治家マッチング処理を行います。
Infrastructure層に配置され、Domain層のIPoliticianMatchingServiceインターフェースを実装します。

Clean Architecture準拠:
    - Infrastructure層に配置
    - Domain層のインターフェース（IPoliticianMatchingService）を実装
    - Domain層のValue Object（PoliticianMatch）を戻り値として使用
"""

import re

from typing import Any

from baml_py.errors import BamlValidationError

from baml_client.async_client import b

from src.common.logging import get_logger
from src.domain.exceptions import ExternalServiceException
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.services.interfaces.llm_service import ILLMService
from src.domain.services.speaker_classifier import is_non_politician_name
from src.domain.value_objects.politician_match import PoliticianMatch
from src.domain.value_objects.speaker_politician_match_result import (
    PoliticianCandidate,
)


logger = get_logger(__name__)


class BAMLPoliticianMatchingService:
    """BAML-based 発言者-政治家マッチングサービス

    BAMLを使用して政治家マッチング処理を行うクラス。
    IPoliticianMatchingServiceインターフェースを実装します。

    特徴:
        - ルールベースマッチング（高速パス）とBAMLマッチングのハイブリッド
        - トークン効率とパース精度の向上
    """

    def __init__(
        self,
        llm_service: ILLMService,  # 互換性のため保持（BAML使用時は不要）
        politician_repository: PoliticianRepository,
    ):
        """
        Initialize BAML politician matching service

        Args:
            llm_service: 互換性のためのパラメータ（BAML使用時は不要）
            politician_repository: Politician repository instance (domain interface)
        """
        self.llm_service = llm_service
        self.politician_repository = politician_repository
        logger.info("BAMLPoliticianMatchingService 初期化完了")

    async def find_best_match(
        self,
        speaker_name: str,
        speaker_type: str | None = None,
        speaker_party: str | None = None,
        role_name_mappings: dict[str, str] | None = None,
    ) -> PoliticianMatch:
        """
        発言者に最適な政治家マッチを見つける

        Args:
            speaker_name: マッチングする発言者名
            speaker_type: 発言者の種別
            speaker_party: 発言者の所属政党（もしあれば）
            role_name_mappings: 役職-人名マッピング辞書（例: {"議長": "伊藤条一"}）
                役職のみの発言者名を実名に解決するために使用

        Returns:
            PoliticianMatch: マッチング結果
        """
        # 役職のみの発言者の場合、マッピングから実名解決を試みる
        resolved_name = self._resolve_role_name(speaker_name, role_name_mappings)
        if resolved_name is None:
            return PoliticianMatch(
                matched=False,
                confidence=0.0,
                reason=f"役職名のみでマッピングなし: {speaker_name}",
            )

        # 既存の政治家リストを取得
        available_politicians = await self.politician_repository.get_all_for_matching()

        if not available_politicians:
            return PoliticianMatch(
                matched=False, confidence=0.0, reason="利用可能な政治家リストが空です"
            )

        return await self._match_against_candidates(
            resolved_name=resolved_name,
            speaker_type=speaker_type,
            speaker_party=speaker_party,
            candidate_dicts=available_politicians,
            operation="politician_matching",
        )

    async def find_best_match_from_candidates(
        self,
        speaker_name: str,
        candidates: list[PoliticianCandidate],
        speaker_type: str | None = None,
        speaker_party: str | None = None,
        role_name_mappings: dict[str, str] | None = None,
    ) -> PoliticianMatch:
        """外部から提供された候補リストを使って発言者に最適な政治家マッチを見つける.

        find_best_matchと同じロジックだが、politician_repositoryの代わりに
        引数の候補リストを使用する。ConferenceMemberでスコープされた候補に
        対してBAMLマッチングを行う場合に使用。

        Args:
            speaker_name: マッチングする発言者名
            candidates: 候補政治家リスト
            speaker_type: 発言者の種別
            speaker_party: 発言者の所属政党
            role_name_mappings: 役職-人名マッピング辞書
        """
        # 役職のみの発言者の場合、マッピングから実名解決を試みる
        resolved_name = self._resolve_role_name(speaker_name, role_name_mappings)
        if resolved_name is None:
            return PoliticianMatch(
                matched=False,
                confidence=0.0,
                reason=f"役職名のみでマッピングなし: {speaker_name}",
            )

        if not candidates:
            return PoliticianMatch(
                matched=False,
                confidence=0.0,
                reason="候補政治家リストが空です",
            )

        # PoliticianCandidate → dict に変換（内部ルールベース互換）
        candidate_dicts = self._candidates_to_dicts(candidates)

        return await self._match_against_candidates(
            resolved_name=resolved_name,
            speaker_type=speaker_type,
            speaker_party=speaker_party,
            candidate_dicts=candidate_dicts,
            operation="politician_matching_from_candidates",
        )

    def _resolve_role_name(
        self,
        speaker_name: str,
        role_name_mappings: dict[str, str] | None,
    ) -> str | None:
        """役職のみの発言者名を実名に解決する.

        Returns:
            解決済みの名前。役職のみでマッピングがない場合はNone。
        """
        if is_non_politician_name(speaker_name):
            if role_name_mappings and speaker_name in role_name_mappings:
                resolved = role_name_mappings[speaker_name]
                logger.info(
                    "役職'%s'を人名'%s'に解決（マッピング使用）",
                    speaker_name,
                    resolved,
                )
                return resolved
            logger.debug(
                "役職のみの発言者をスキップ（マッピングなし）: '%s'",
                speaker_name,
            )
            return None
        return speaker_name

    async def _match_against_candidates(
        self,
        resolved_name: str,
        speaker_type: str | None,
        speaker_party: str | None,
        candidate_dicts: list[dict[str, Any]],
        operation: str,
    ) -> PoliticianMatch:
        """ルールベース→BAMLのマッチングパイプラインを実行する共通メソッド."""
        # ルールベースマッチング（高速パス）
        rule_based_match = self._rule_based_matching(
            resolved_name, speaker_party, candidate_dicts
        )
        if rule_based_match.matched and rule_based_match.confidence >= 0.9:
            logger.info("ルールベースマッチング成功: '%s'", resolved_name)
            return rule_based_match

        # BAMLによる高度なマッチング
        try:
            filtered = self._filter_candidates(
                resolved_name, speaker_party, candidate_dicts
            )

            baml_result = await b.MatchPolitician(
                speaker_name=resolved_name,
                speaker_type=speaker_type or "不明",
                speaker_party=speaker_party or "不明",
                available_politicians=self._format_politicians_for_llm(filtered),
            )

            # 信頼度に応じてマッチ結果を構築
            matched = baml_result.matched and baml_result.confidence >= 0.7
            match_result = PoliticianMatch(
                matched=matched,
                politician_id=baml_result.politician_id if matched else None,
                politician_name=baml_result.politician_name if matched else None,
                political_party_name=baml_result.political_party_name
                if matched
                else None,
                confidence=baml_result.confidence,
                reason=baml_result.reason,
            )

            logger.info(
                "BAMLマッチング結果: '%s' - matched=%s, confidence=%s",
                resolved_name,
                match_result.matched,
                match_result.confidence,
            )
            return match_result

        except BamlValidationError as e:
            logger.warning(
                "BAMLバリデーション失敗: '%s' - %s. マッチなし結果を返します。",
                resolved_name,
                e,
            )
            return PoliticianMatch(
                matched=False,
                confidence=0.0,
                reason=f"LLMが構造化出力を返せませんでした: {resolved_name}",
            )
        except Exception as e:
            logger.error(
                "BAML政治家マッチング中のエラー: '%s' - %s",
                resolved_name,
                e,
                exc_info=True,
            )
            raise ExternalServiceException(
                service_name="BAML",
                operation=operation,
                reason=f"政治家マッチング中にエラーが発生しました: {e}",
            ) from e

    @staticmethod
    def _candidates_to_dicts(
        candidates: list[PoliticianCandidate],
    ) -> list[dict[str, Any]]:
        """PoliticianCandidate → dict変換（内部ルールベース互換用）."""
        return [
            {
                "id": c.politician_id,
                "name": c.name,
                "party_name": c.party_name,
                "furigana": c.furigana,
            }
            for c in candidates
        ]

    def _rule_based_matching(
        self,
        speaker_name: str,
        speaker_party: str | None,
        available_politicians: list[dict[str, Any]],
    ) -> PoliticianMatch:
        """従来のルールベースマッチング（高速パス）"""

        # 1. 完全一致（名前と政党）
        if speaker_party:
            for politician in available_politicians:
                if (
                    politician["name"] == speaker_name
                    and politician["party_name"] == speaker_party
                ):
                    return PoliticianMatch(
                        matched=True,
                        politician_id=politician["id"],
                        politician_name=politician["name"],
                        political_party_name=politician["party_name"],
                        confidence=1.0,
                        reason="名前と政党が完全一致",
                    )

        # 2. 名前のみ完全一致
        exact_matches = [p for p in available_politicians if p["name"] == speaker_name]
        if len(exact_matches) == 1:
            politician = exact_matches[0]
            return PoliticianMatch(
                matched=True,
                politician_id=politician["id"],
                politician_name=politician["name"],
                political_party_name=politician["party_name"],
                confidence=0.9,
                reason="名前が完全一致（唯一の候補）",
            )

        # 3. 敬称を除去して検索
        cleaned_name = re.sub(r"(議員|氏|さん|様|先生)$", "", speaker_name)
        if cleaned_name != speaker_name:
            for politician in available_politicians:
                if politician["name"] == cleaned_name:
                    return PoliticianMatch(
                        matched=True,
                        politician_id=politician["id"],
                        politician_name=politician["name"],
                        political_party_name=politician["party_name"],
                        confidence=0.85,
                        reason=f"敬称除去後に一致: {speaker_name} → {cleaned_name}",
                    )

        return PoliticianMatch(
            matched=False, confidence=0.0, reason="ルールベースマッチングでは一致なし"
        )

    def _filter_candidates(
        self,
        speaker_name: str,
        speaker_party: str | None,
        available_politicians: list[dict[str, Any]],
        max_candidates: int = 20,
    ) -> list[dict[str, Any]]:
        """候補を絞り込む（LLMの処理効率向上のため）"""
        candidates: list[dict[str, Any]] = []

        # 敬称を除去
        cleaned_name = re.sub(r"(議員|氏|さん|様|先生)$", "", speaker_name)

        for politician in available_politicians:
            score = 0

            # 完全一致
            if politician["name"] == speaker_name:
                score += 10

            # 敬称除去後の一致
            if politician["name"] == cleaned_name:
                score += 8

            # 部分一致
            if politician["name"] in speaker_name or speaker_name in politician["name"]:
                score += 5

            # 政党一致
            if speaker_party and politician["party_name"] == speaker_party:
                score += 3

            # 姓または名の一致（スペースで分割）
            speaker_parts = speaker_name.split()
            politician_parts = politician["name"].split()
            for sp in speaker_parts:
                if sp in politician_parts:
                    score += 2

            # 文字列長の類似性
            len_diff = abs(len(politician["name"]) - len(speaker_name))
            if len_diff <= 2:
                score += 1

            if score > 0:
                candidates.append({**politician, "score": score})

        # スコア順にソート
        candidates.sort(key=lambda x: x["score"], reverse=True)

        # 最大候補数に制限
        return candidates[:max_candidates]

    def _format_politicians_for_llm(self, politicians: list[dict[str, Any]]) -> str:
        """政治家リストをLLM用にフォーマット"""
        formatted: list[str] = []
        for p in politicians:
            info = f"ID: {p['id']}, 名前: {p['name']}"
            if p.get("party_name"):
                info += f", 政党: {p['party_name']}"
            if p.get("position"):
                info += f", 役職: {p['position']}"
            if p.get("prefecture"):
                info += f", 都道府県: {p['prefecture']}"
            if p.get("electoral_district"):
                info += f", 選挙区: {p['electoral_district']}"
            formatted.append(info)
        return "\n".join(formatted)
