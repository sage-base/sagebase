"""京都市議会データ登録スクリプトのユニットテスト."""

from __future__ import annotations

import sys

from pathlib import Path
from unittest.mock import AsyncMock

import pytest


# スクリプトのimportを可能にする
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.import_kyoto_city_council import (
    CONFERENCES,
    GROUP_URLS,
    POLITICIANS,
    import_conferences,
    import_memberships,
    import_parliamentary_groups,
    import_politicians,
)

from src.domain.entities.conference import Conference
from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.entities.politician import Politician
from src.infrastructure.persistence.conference_repository_impl import (
    ConferenceRepositoryImpl,
)
from src.infrastructure.persistence.parliamentary_group_membership_repository_impl import (  # noqa: E501
    ParliamentaryGroupMembershipRepositoryImpl,
)
from src.infrastructure.persistence.parliamentary_group_repository_impl import (
    ParliamentaryGroupRepositoryImpl,
)
from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl,
)


class TestDataDefinitions:
    """データ定義の整合性テスト."""

    def test_total_politician_count_is_67(self) -> None:
        """議員データが67名であること."""
        assert len(POLITICIANS) == 67

    def test_all_politicians_have_required_fields(self) -> None:
        """全議員データに必須フィールドがあること."""
        for p in POLITICIANS:
            assert p.name, f"議員名が空: {p}"
            assert p.district, f"選挙区が空: {p.name}"
            assert p.group, f"会派が空: {p.name}"

    def test_all_groups_referenced_by_politicians_exist(self) -> None:
        """議員データの会派がすべてGROUP_URLSに存在すること."""
        valid_groups = set(GROUP_URLS.keys())
        for p in POLITICIANS:
            assert p.group in valid_groups, (
                f"{p.name}の会派「{p.group}」がGROUP_URLSに存在しない"
            )

    def test_group_counts(self) -> None:
        """会派ごとの議員数が正しいこと."""
        from collections import Counter

        counts = Counter(p.group for p in POLITICIANS)
        assert counts["自由民主党京都市会議員団"] == 19
        assert counts["維新・京都・国民市会議員団"] == 16
        assert counts["日本共産党京都市会議員団"] == 14
        assert counts["公明党京都市会議員団"] == 11
        assert counts["無所属"] == 7

    def test_all_districts_are_valid_kyoto_wards(self) -> None:
        """全議員の選挙区が京都市の11行政区であること."""
        valid_districts = {
            "北区",
            "上京区",
            "左京区",
            "中京区",
            "東山区",
            "山科区",
            "下京区",
            "南区",
            "右京区",
            "西京区",
            "伏見区",
        }
        for p in POLITICIANS:
            assert p.district in valid_districts, (
                f"{p.name}の選挙区「{p.district}」が不正"
            )

    def test_no_duplicate_politician_names(self) -> None:
        """議員名に重複がないこと."""
        names = [p.name for p in POLITICIANS]
        assert len(names) == len(set(names)), "議員名に重複あり"

    def test_conferences_count(self) -> None:
        """会議体が9件であること（本会議1 + 常任5 + 特別2 + 運営1）."""
        assert len(CONFERENCES) == 9

    def test_conferences_include_expected_names(self) -> None:
        """主要な会議体名が含まれていること."""
        assert "京都市会本会議" in CONFERENCES
        assert "総務消防委員会" in CONFERENCES
        assert "予算特別委員会" in CONFERENCES
        assert "市会運営委員会" in CONFERENCES

    def test_group_urls_has_5_groups(self) -> None:
        """会派URLが5会派分あること."""
        assert len(GROUP_URLS) == 5

    def test_each_group_has_leader(self) -> None:
        """各会派（無所属以外）に団長がいること."""
        groups_with_leaders = {p.group for p in POLITICIANS if p.role == "団長"}
        expected = {
            "自由民主党京都市会議員団",
            "維新・京都・国民市会議員団",
            "日本共産党京都市会議員団",
            "公明党京都市会議員団",
        }
        assert groups_with_leaders == expected


class TestImportPoliticians:
    """議員登録関数のテスト."""

    @pytest.fixture
    def mock_politician_repo(self) -> AsyncMock:
        return AsyncMock(spec=PoliticianRepositoryImpl)

    @pytest.mark.asyncio
    async def test_creates_new_politician(
        self, mock_politician_repo: AsyncMock
    ) -> None:
        """既存データがない場合に新規作成されること."""
        mock_politician_repo.get_by_name.return_value = None
        mock_politician_repo.create.return_value = Politician(
            id=1,
            name="テスト太郎",
            prefecture="京都府",
            district="北区",
        )

        await import_politicians(mock_politician_repo, dry_run=False)

        assert mock_politician_repo.create.await_count == len(POLITICIANS)

    @pytest.mark.asyncio
    async def test_skips_existing_politician(
        self, mock_politician_repo: AsyncMock
    ) -> None:
        """既存データがある場合はスキップされること."""
        existing = Politician(
            id=99,
            name="橋村芳和",
            prefecture="京都府",
            district="伏見区",
        )
        mock_politician_repo.get_by_name.return_value = existing

        result = await import_politicians(mock_politician_repo, dry_run=False)

        mock_politician_repo.create.assert_not_awaited()
        assert result["橋村芳和"] == existing

    @pytest.mark.asyncio
    async def test_dry_run_does_not_create(
        self, mock_politician_repo: AsyncMock
    ) -> None:
        """ドライランではDBに書き込まないこと."""
        mock_politician_repo.get_by_name.return_value = None

        await import_politicians(mock_politician_repo, dry_run=True)

        mock_politician_repo.create.assert_not_awaited()


class TestImportParliamentaryGroups:
    """会派登録関数のテスト."""

    @pytest.fixture
    def mock_pg_repo(self) -> AsyncMock:
        return AsyncMock(spec=ParliamentaryGroupRepositoryImpl)

    @pytest.mark.asyncio
    async def test_creates_new_group(self, mock_pg_repo: AsyncMock) -> None:
        """既存データがない場合に新規作成されること."""
        mock_pg_repo.get_by_name_and_governing_body.return_value = None
        mock_pg_repo.create.return_value = ParliamentaryGroup(
            id=1,
            name="テスト",
            governing_body_id=100,
        )

        await import_parliamentary_groups(
            mock_pg_repo, governing_body_id=100, dry_run=False
        )

        assert mock_pg_repo.create.await_count == 5

    @pytest.mark.asyncio
    async def test_skips_existing_group(self, mock_pg_repo: AsyncMock) -> None:
        """既存データがある場合はスキップされること."""
        existing = ParliamentaryGroup(
            id=10,
            name="無所属",
            governing_body_id=100,
        )
        mock_pg_repo.get_by_name_and_governing_body.return_value = existing

        await import_parliamentary_groups(
            mock_pg_repo, governing_body_id=100, dry_run=False
        )

        mock_pg_repo.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_dry_run_does_not_create(self, mock_pg_repo: AsyncMock) -> None:
        """ドライランではDBに書き込まないこと."""
        mock_pg_repo.get_by_name_and_governing_body.return_value = None

        await import_parliamentary_groups(
            mock_pg_repo, governing_body_id=100, dry_run=True
        )

        mock_pg_repo.create.assert_not_awaited()


class TestImportMemberships:
    """会派所属登録関数のテスト."""

    @pytest.fixture
    def mock_membership_repo(self) -> AsyncMock:
        return AsyncMock(spec=ParliamentaryGroupMembershipRepositoryImpl)

    @pytest.mark.asyncio
    async def test_creates_membership(self, mock_membership_repo: AsyncMock) -> None:
        """議員と会派の紐付けが作成されること."""
        name_to_politician = {
            "橋村芳和": Politician(
                id=1,
                name="橋村芳和",
                prefecture="京都府",
                district="伏見区",
            ),
        }
        name_to_group = {
            "自由民主党京都市会議員団": ParliamentaryGroup(
                id=10,
                name="自由民主党京都市会議員団",
                governing_body_id=100,
            ),
        }

        await import_memberships(
            mock_membership_repo,
            name_to_politician,
            name_to_group,
            dry_run=False,
        )

        # 橋村芳和は自民会派なので1回呼ばれる
        # （他はpoliticianが見つからないのでスキップ）
        assert mock_membership_repo.add_membership.await_count == 1
        call_kwargs = mock_membership_repo.add_membership.call_args
        assert call_kwargs.kwargs["politician_id"] == 1
        assert call_kwargs.kwargs["parliamentary_group_id"] == 10
        assert call_kwargs.kwargs["role"] == "団長"

    @pytest.mark.asyncio
    async def test_skips_when_politician_not_found(
        self, mock_membership_repo: AsyncMock
    ) -> None:
        """議員が見つからない場合はスキップされること."""
        await import_memberships(
            mock_membership_repo,
            name_to_politician={},
            name_to_group={
                "自由民主党京都市会議員団": ParliamentaryGroup(
                    id=10,
                    name="自由民主党京都市会議員団",
                    governing_body_id=100,
                ),
            },
            dry_run=False,
        )

        mock_membership_repo.add_membership.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_dry_run_does_not_create(
        self, mock_membership_repo: AsyncMock
    ) -> None:
        """ドライランではDBに書き込まないこと."""
        name_to_politician = {
            "橋村芳和": Politician(
                id=1,
                name="橋村芳和",
                prefecture="京都府",
                district="伏見区",
            ),
        }
        name_to_group = {
            "自由民主党京都市会議員団": ParliamentaryGroup(
                id=10,
                name="自由民主党京都市会議員団",
                governing_body_id=100,
            ),
        }

        await import_memberships(
            mock_membership_repo,
            name_to_politician,
            name_to_group,
            dry_run=True,
        )

        mock_membership_repo.add_membership.assert_not_awaited()


class TestImportConferences:
    """会議体登録関数のテスト."""

    @pytest.fixture
    def mock_conference_repo(self) -> AsyncMock:
        return AsyncMock(spec=ConferenceRepositoryImpl)

    @pytest.mark.asyncio
    async def test_creates_new_conferences(
        self, mock_conference_repo: AsyncMock
    ) -> None:
        """既存データがない場合に会議体が作成されること."""
        mock_conference_repo.get_by_name_and_governing_body.return_value = None
        mock_conference_repo.create.return_value = Conference(
            id=1,
            name="テスト",
            governing_body_id=100,
        )

        await import_conferences(
            mock_conference_repo, governing_body_id=100, dry_run=False
        )

        assert mock_conference_repo.create.await_count == 9

    @pytest.mark.asyncio
    async def test_skips_existing_conferences(
        self, mock_conference_repo: AsyncMock
    ) -> None:
        """既存データがある場合はスキップされること."""
        existing = Conference(
            id=5,
            name="京都市会本会議",
            governing_body_id=100,
        )
        mock_conference_repo.get_by_name_and_governing_body.return_value = existing

        await import_conferences(
            mock_conference_repo, governing_body_id=100, dry_run=False
        )

        mock_conference_repo.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_dry_run_does_not_create(
        self, mock_conference_repo: AsyncMock
    ) -> None:
        """ドライランではDBに書き込まないこと."""
        mock_conference_repo.get_by_name_and_governing_body.return_value = None

        await import_conferences(
            mock_conference_repo, governing_body_id=100, dry_run=True
        )

        mock_conference_repo.create.assert_not_awaited()
