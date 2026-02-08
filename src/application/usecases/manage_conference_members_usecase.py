"""Use case for managing conference members."""

from dataclasses import dataclass
from datetime import date

from src.domain.entities.conference_member import ConferenceMember
from src.domain.entities.extracted_conference_member import ExtractedConferenceMember
from src.domain.repositories.conference_member_repository import (
    ConferenceMemberRepository,
)
from src.domain.repositories.conference_repository import ConferenceRepository
from src.domain.repositories.election_member_repository import (
    ElectionMemberRepository,
)
from src.domain.repositories.extracted_conference_member_repository import (
    ExtractedConferenceMemberRepository,
)
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.services.conference_domain_service import ConferenceDomainService
from src.domain.services.interfaces.web_scraper_service import IWebScraperService


# DTOs for Use Case
@dataclass
class ExtractMembersInputDTO:
    """Input DTO for extract_members."""

    conference_id: int
    force: bool = False


@dataclass
class ExtractedMemberDTO:
    """DTO for extracted member data.

    Bronze Layer（抽出ログ層）のデータを表す。
    政治家との紐付けはGold Layer（ConferenceMember）で管理される。
    """

    id: int
    conference_id: int
    name: str
    role: str | None
    party_affiliation: str | None


@dataclass
class ExtractMembersOutputDTO:
    """Output DTO for extract_members."""

    conference_id: int
    extracted_count: int
    members: list[ExtractedMemberDTO]


@dataclass
class ManualMatchInputDTO:
    """手動政治家マッチングの入力DTO."""

    member_id: int
    politician_id: int


@dataclass
class ManualMatchOutputDTO:
    """手動マッチング操作の出力DTO."""

    success: bool
    member_id: int
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
    source_extracted_member_id: int | None = None


class ManageConferenceMembersUseCase:
    """会議体メンバー管理ユースケース

    会議体（議会・委員会）のメンバー情報を抽出し、
    手動で政治家と紐付けて所属情報を作成するプロセスを管理します。

    処理フロー：
    1. extract_members: WebページからメンバーをLLMで抽出（Bronze Layer）
    2. manual_match: 手動で政治家を選択してConferenceMemberを作成（Gold Layer）

    Bronze LayerとGold Layerの分離により、
    抽出データ（ExtractedConferenceMember）と確定データ（ConferenceMember）を
    明確に区別します。

    Attributes:
        conference_repo: 会議体リポジトリ
        politician_repo: 政治家リポジトリ
        conference_service: 会議体ドメインサービス
        extracted_repo: 抽出済みメンバーリポジトリ
        conference_member_repo: 会議体メンバーリポジトリ
        scraper: Webスクレイピングサービス
        election_member_repo: 選挙結果メンバーリポジトリ（当選者絞り込み用）

    Example:
        >>> use_case = ManageConferenceMembersUseCase(...)
        >>>
        >>> # Step 1: メンバー抽出
        >>> extracted = await use_case.extract_members(
        ...     ExtractMembersInputDTO(conference_id=185)
        ... )
        >>>
        >>> # Step 2: 手動で政治家を選択してConferenceMemberを作成
        >>> result = await use_case.manual_match(
        ...     ManualMatchInputDTO(member_id=1, politician_id=100)
        ... )
    """

    def __init__(
        self,
        conference_repository: ConferenceRepository,
        politician_repository: PoliticianRepository,
        conference_domain_service: ConferenceDomainService,
        extracted_member_repository: ExtractedConferenceMemberRepository,
        conference_member_repository: ConferenceMemberRepository,
        web_scraper_service: IWebScraperService,
        election_member_repository: ElectionMemberRepository | None = None,
    ):
        """会議体メンバー管理ユースケースを初期化する

        Args:
            conference_repository: 会議体リポジトリの実装
            politician_repository: 政治家リポジトリの実装
            conference_domain_service: 会議体ドメインサービス
            extracted_member_repository: 抽出済みメンバーリポジトリの実装
            conference_member_repository: 会議体メンバーリポジトリの実装
            web_scraper_service: Webスクレイピングサービス
            election_member_repository: 選挙結果メンバーリポジトリ
        """
        self.conference_repo = conference_repository
        self.politician_repo = politician_repository
        self.conference_service = conference_domain_service
        self.extracted_repo = extracted_member_repository
        self.conference_member_repo = conference_member_repository
        self.scraper = web_scraper_service
        self.election_member_repo = election_member_repository

    async def extract_members(
        self, request: ExtractMembersInputDTO
    ) -> ExtractMembersOutputDTO:
        """会議体メンバーをWebページから抽出する

        会議体のmembers_introduction_urlからメンバー情報を抽出し、
        ステージングテーブル（extracted_conference_members）に保存します。

        Args:
            request: 抽出リクエストDTO
                - conference_id: 対象会議体ID
                - force: 既存データを強制的に再抽出するか

        Returns:
            ExtractMembersOutputDTO:
                - conference_id: 会議体ID
                - extracted_count: 抽出されたメンバー数
                - members: 抽出されたメンバーDTOリスト

        Raises:
            ValueError: 会議体が見つからない、URLが未設定の場合
        """
        # Get conference
        conference = await self.conference_repo.get_by_id(request.conference_id)
        if not conference:
            raise ValueError(f"Conference {request.conference_id} not found")

        if not conference.members_introduction_url:
            raise ValueError(f"Conference {conference.name} has no members URL")

        # Check existing if not forcing
        if not request.force:
            existing = await self.extracted_repo.get_by_conference(
                request.conference_id
            )
            if existing:
                return ExtractMembersOutputDTO(
                    conference_id=request.conference_id,
                    extracted_count=len(existing),
                    members=[self._to_extracted_dto(m) for m in existing],
                )

        # Scrape and extract members using LLM
        # In a real implementation, this would scrape and use LLM to extract data
        members_data = await self.scraper.scrape_conference_members(
            conference.members_introduction_url
        )

        # Save to staging table
        created_members: list[ExtractedConferenceMember] = []
        for member_data in members_data:
            member = ExtractedConferenceMember(
                conference_id=request.conference_id,
                extracted_name=member_data["name"],
                source_url=conference.members_introduction_url,
                extracted_role=member_data.get("role"),
                extracted_party_name=member_data.get("party"),
            )
            created = await self.extracted_repo.create(member)
            created_members.append(created)

        return ExtractMembersOutputDTO(
            conference_id=request.conference_id,
            extracted_count=len(created_members),
            members=[self._to_extracted_dto(m) for m in created_members],
        )

    async def manual_match(self, request: ManualMatchInputDTO) -> ManualMatchOutputDTO:
        """手動で政治家をマッチングする

        抽出済みメンバーに指定された政治家を紐付け、
        Gold Layer（ConferenceMember）の所属情報を作成します。

        Args:
            request: 手動マッチングリクエストDTO
                - member_id: 抽出済みメンバーID
                - politician_id: 紐付ける政治家ID

        Returns:
            ManualMatchOutputDTO: 操作結果
        """
        member = await self.extracted_repo.get_by_id(request.member_id)
        if not member:
            return ManualMatchOutputDTO(
                success=False,
                member_id=request.member_id,
                message="メンバーが見つかりません",
            )

        politician = await self.politician_repo.get_by_id(request.politician_id)
        if not politician:
            return ManualMatchOutputDTO(
                success=False,
                member_id=request.member_id,
                message=f"政治家ID {request.politician_id} が見つかりません",
            )

        # Gold Layer: ConferenceMemberを作成（既存のアクティブな所属がなければ）
        existing = await self.conference_member_repo.get_by_politician_and_conference(
            request.politician_id, member.conference_id
        )
        active = [a for a in existing if not a.end_date]
        if not active:
            conference_member = ConferenceMember(
                politician_id=request.politician_id,
                conference_id=member.conference_id,
                role=member.extracted_role,
                start_date=date.today(),
                source_extracted_member_id=member.id,
                is_manually_verified=True,
            )
            await self.conference_member_repo.create(conference_member)

        return ManualMatchOutputDTO(
            success=True,
            member_id=request.member_id,
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

    def _to_extracted_dto(
        self, member: ExtractedConferenceMember
    ) -> ExtractedMemberDTO:
        """抽出済みメンバーエンティティをDTOに変換する

        Args:
            member: 抽出済みメンバーエンティティ

        Returns:
            抽出済みメンバーDTO
        """
        return ExtractedMemberDTO(
            id=member.id or 0,
            conference_id=member.conference_id,
            name=member.extracted_name,
            role=member.extracted_role,
            party_affiliation=member.extracted_party_name,
        )
