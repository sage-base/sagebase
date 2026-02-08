"""Use case for managing conference members."""

from dataclasses import dataclass
from datetime import date

from src.domain.entities.conference_member import ConferenceMember
from src.domain.repositories.conference_member_repository import (
    ConferenceMemberRepository,
)
from src.domain.repositories.conference_repository import ConferenceRepository
from src.domain.repositories.election_member_repository import (
    ElectionMemberRepository,
)
from src.domain.repositories.politician_repository import PoliticianRepository


# DTOs for Use Case
@dataclass
class ManualMatchInputDTO:
    """手動政治家マッチングの入力DTO."""

    politician_id: int
    conference_id: int


@dataclass
class ManualMatchOutputDTO:
    """手動マッチング操作の出力DTO."""

    success: bool
    message: str


@dataclass
class SearchPoliticiansInputDTO:
    """政治家検索の入力DTO."""

    name: str


@dataclass
class GetElectionCandidatesInputDTO:
    """当選者候補取得の入力DTO."""

    conference_id: int


@dataclass
class PoliticianCandidateDTO:
    """政治家候補のDTO."""

    id: int
    name: str


@dataclass
class SearchPoliticiansOutputDTO:
    """政治家検索の出力DTO."""

    candidates: list[PoliticianCandidateDTO]


@dataclass
class ConferenceMemberDTO:
    """DTO for conference member data."""

    id: int
    politician_id: int
    politician_name: str
    conference_id: int
    role: str | None
    start_date: date
    end_date: date | None


class ManageConferenceMembersUseCase:
    """会議体メンバー管理ユースケース

    会議体（議会・委員会）のメンバー情報を管理します。
    選挙結果に基づく当選者の取得や、手動での政治家紐付けを行います。

    Attributes:
        conference_repo: 会議体リポジトリ
        politician_repo: 政治家リポジトリ
        conference_member_repo: 会議体メンバーリポジトリ
        election_member_repo: 選挙結果メンバーリポジトリ（当選者絞り込み用）
    """

    def __init__(
        self,
        conference_repository: ConferenceRepository,
        politician_repository: PoliticianRepository,
        conference_member_repository: ConferenceMemberRepository,
        election_member_repository: ElectionMemberRepository | None = None,
    ):
        """会議体メンバー管理ユースケースを初期化する

        Args:
            conference_repository: 会議体リポジトリの実装
            politician_repository: 政治家リポジトリの実装
            conference_member_repository: 会議体メンバーリポジトリの実装
            election_member_repository: 選挙結果メンバーリポジトリ
        """
        self.conference_repo = conference_repository
        self.politician_repo = politician_repository
        self.conference_member_repo = conference_member_repository
        self.election_member_repo = election_member_repository

    async def manual_match(self, request: ManualMatchInputDTO) -> ManualMatchOutputDTO:
        """手動で政治家を会議体メンバーとして登録する

        指定された政治家をConferenceMemberとして登録します。

        Args:
            request: 手動マッチングリクエストDTO
                - politician_id: 紐付ける政治家ID
                - conference_id: 会議体ID

        Returns:
            ManualMatchOutputDTO: 操作結果
        """
        politician = await self.politician_repo.get_by_id(request.politician_id)
        if not politician:
            return ManualMatchOutputDTO(
                success=False,
                message=f"政治家ID {request.politician_id} が見つかりません",
            )

        # ConferenceMemberを作成（既存のアクティブな所属がなければ）
        existing = await self.conference_member_repo.get_by_politician_and_conference(
            request.politician_id, request.conference_id
        )
        active = [a for a in existing if not a.end_date]
        if not active:
            conference_member = ConferenceMember(
                politician_id=request.politician_id,
                conference_id=request.conference_id,
                start_date=date.today(),
                is_manually_verified=True,
            )
            await self.conference_member_repo.create(conference_member)

        return ManualMatchOutputDTO(
            success=True,
            message="手動マッチングが完了しました",
        )

    async def search_politicians(
        self, request: SearchPoliticiansInputDTO
    ) -> SearchPoliticiansOutputDTO:
        """政治家を名前で検索する

        名前の正規化（スペース除去）を行い、政治家を検索します。

        Args:
            request: 検索リクエストDTO

        Returns:
            SearchPoliticiansOutputDTO: 検索結果
        """
        normalized = request.name.replace(" ", "").replace("\u3000", "")
        if not normalized:
            return SearchPoliticiansOutputDTO(candidates=[])

        candidates = await self.politician_repo.search_by_name(normalized)
        return SearchPoliticiansOutputDTO(
            candidates=[
                PoliticianCandidateDTO(id=c.id or 0, name=c.name) for c in candidates
            ]
        )

    async def get_election_candidates(
        self, request: GetElectionCandidatesInputDTO
    ) -> SearchPoliticiansOutputDTO:
        """会議体に紐づく選挙の当選者を取得する

        会議体のelection_idから選挙結果メンバーを取得し、
        当選者の政治家情報を返します。

        Args:
            request: 当選者候補取得リクエストDTO

        Returns:
            SearchPoliticiansOutputDTO: 当選者の政治家候補リスト
        """
        if self.election_member_repo is None:
            return SearchPoliticiansOutputDTO(candidates=[])

        conference = await self.conference_repo.get_by_id(request.conference_id)
        if not conference or not conference.election_id:
            return SearchPoliticiansOutputDTO(candidates=[])

        election_members = await self.election_member_repo.get_by_election_id(
            conference.election_id
        )
        elected = [m for m in election_members if m.is_elected]

        candidates: list[PoliticianCandidateDTO] = []
        for em in elected:
            politician = await self.politician_repo.get_by_id(em.politician_id)
            if politician:
                candidates.append(
                    PoliticianCandidateDTO(id=politician.id or 0, name=politician.name)
                )

        return SearchPoliticiansOutputDTO(candidates=candidates)
