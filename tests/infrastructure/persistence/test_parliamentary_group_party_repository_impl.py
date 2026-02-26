"""ParliamentaryGroupPartyRepositoryImplのテスト."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.parliamentary_group_party import ParliamentaryGroupParty
from src.infrastructure.persistence.parliamentary_group_party_repository_impl import (
    ParliamentaryGroupPartyRepositoryImpl,
)
from src.infrastructure.persistence.sqlalchemy_models import (
    ParliamentaryGroupPartyModel,
)


class TestParliamentaryGroupPartyRepositoryImpl:
    @pytest.fixture
    def mock_session(self):
        session = MagicMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def repository(self, mock_session):
        return ParliamentaryGroupPartyRepositoryImpl(mock_session)

    def _make_model(
        self,
        id: int = 1,
        parliamentary_group_id: int = 10,
        political_party_id: int = 20,
        is_primary: bool = False,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> MagicMock:
        model = MagicMock(spec=ParliamentaryGroupPartyModel)
        model.id = id
        model.parliamentary_group_id = parliamentary_group_id
        model.political_party_id = political_party_id
        model.is_primary = is_primary
        model.created_at = created_at or datetime(2024, 1, 1, 10, 0)
        model.updated_at = updated_at or datetime(2024, 1, 1, 10, 0)
        return model

    @pytest.mark.asyncio
    async def test_get_by_parliamentary_group_id(self, repository, mock_session):
        models = [
            self._make_model(id=1, parliamentary_group_id=10, political_party_id=20),
            self._make_model(id=2, parliamentary_group_id=10, political_party_id=21),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = models

        async def async_execute(query):
            return mock_result

        mock_session.execute = async_execute

        result = await repository.get_by_parliamentary_group_id(10)

        assert len(result) == 2
        assert all(isinstance(e, ParliamentaryGroupParty) for e in result)
        assert result[0].parliamentary_group_id == 10
        assert result[0].political_party_id == 20
        assert result[1].political_party_id == 21

    @pytest.mark.asyncio
    async def test_get_by_parliamentary_group_id_empty(self, repository, mock_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        async def async_execute(query):
            return mock_result

        mock_session.execute = async_execute

        result = await repository.get_by_parliamentary_group_id(999)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_political_party_id(self, repository, mock_session):
        models = [
            self._make_model(id=1, parliamentary_group_id=10, political_party_id=20),
            self._make_model(id=3, parliamentary_group_id=11, political_party_id=20),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = models

        async def async_execute(query):
            return mock_result

        mock_session.execute = async_execute

        result = await repository.get_by_political_party_id(20)

        assert len(result) == 2
        assert result[0].political_party_id == 20
        assert result[1].political_party_id == 20

    @pytest.mark.asyncio
    async def test_get_by_political_party_id_empty(self, repository, mock_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        async def async_execute(query):
            return mock_result

        mock_session.execute = async_execute

        result = await repository.get_by_political_party_id(999)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_primary_party_found(self, repository, mock_session):
        model = self._make_model(
            id=1, parliamentary_group_id=10, political_party_id=20, is_primary=True
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = model

        async def async_execute(query):
            return mock_result

        mock_session.execute = async_execute

        result = await repository.get_primary_party(10)

        assert result is not None
        assert result.is_primary is True
        assert result.parliamentary_group_id == 10

    @pytest.mark.asyncio
    async def test_get_primary_party_not_found(self, repository, mock_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None

        async def async_execute(query):
            return mock_result

        mock_session.execute = async_execute

        result = await repository.get_primary_party(99)

        assert result is None

    @pytest.mark.asyncio
    async def test_add_party_new(self, repository, mock_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None

        async def async_execute(query):
            return mock_result

        mock_session.execute = async_execute
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        new_model = self._make_model(
            id=5, parliamentary_group_id=10, political_party_id=30, is_primary=True
        )

        async def async_refresh(model):
            model.id = new_model.id
            model.parliamentary_group_id = new_model.parliamentary_group_id
            model.political_party_id = new_model.political_party_id
            model.is_primary = new_model.is_primary
            model.created_at = new_model.created_at
            model.updated_at = new_model.updated_at

        mock_session.refresh = async_refresh

        result = await repository.add_party(10, 30, is_primary=True)

        assert isinstance(result, ParliamentaryGroupParty)
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_party_existing_does_not_create(self, repository, mock_session):
        existing_model = self._make_model(
            id=1, parliamentary_group_id=10, political_party_id=20
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = existing_model

        async def async_execute(query):
            return mock_result

        mock_session.execute = async_execute
        mock_session.add = MagicMock()

        result = await repository.add_party(10, 20)

        assert result.id == 1
        assert result.parliamentary_group_id == 10
        assert result.political_party_id == 20
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_party_exists(self, repository, mock_session):
        model = self._make_model(id=1, parliamentary_group_id=10, political_party_id=20)

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = model

        async def async_execute(query):
            return mock_result

        mock_session.execute = async_execute
        mock_session.delete = AsyncMock()
        mock_session.flush = AsyncMock()

        result = await repository.remove_party(10, 20)

        assert result is True
        mock_session.delete.assert_called_once_with(model)

    @pytest.mark.asyncio
    async def test_remove_party_not_exists(self, repository, mock_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None

        async def async_execute(query):
            return mock_result

        mock_session.execute = async_execute

        result = await repository.remove_party(10, 99)

        assert result is False

    @pytest.mark.asyncio
    async def test_set_primary(self, repository, mock_session):
        target_model = self._make_model(
            id=2, parliamentary_group_id=10, political_party_id=21, is_primary=False
        )
        current_primary_model = self._make_model(
            id=1, parliamentary_group_id=10, political_party_id=20, is_primary=True
        )

        call_count = 0

        async def async_execute(query):
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            if call_count == 1:
                mock_result.scalars.return_value.first.return_value = target_model
            elif call_count == 2:
                mock_result.scalars.return_value.first.return_value = (
                    current_primary_model
                )
            return mock_result

        mock_session.execute = async_execute
        mock_session.flush = AsyncMock()

        async def async_refresh(model):
            pass

        mock_session.refresh = async_refresh

        result = await repository.set_primary(10, 21)

        assert result is not None
        assert current_primary_model.is_primary is False
        assert target_model.is_primary is True

    @pytest.mark.asyncio
    async def test_set_primary_already_primary_is_idempotent(
        self, repository, mock_session
    ):
        """既にprimaryのレコードを再度primaryに設定する冪等性テスト."""
        target_model = self._make_model(
            id=1, parliamentary_group_id=10, political_party_id=20, is_primary=True
        )

        call_count = 0

        async def async_execute(query):
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            if call_count == 1:
                mock_result.scalars.return_value.first.return_value = target_model
            elif call_count == 2:
                mock_result.scalars.return_value.first.return_value = target_model
            return mock_result

        mock_session.execute = async_execute
        mock_session.flush = AsyncMock()

        async def async_refresh(model):
            pass

        mock_session.refresh = async_refresh

        result = await repository.set_primary(10, 20)

        assert result is not None
        assert target_model.is_primary is True

    @pytest.mark.asyncio
    async def test_set_primary_not_found(self, repository, mock_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None

        async def async_execute(query):
            return mock_result

        mock_session.execute = async_execute

        result = await repository.set_primary(10, 99)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_parliamentary_group_ids(self, repository, mock_session):
        """複数の会派IDで一括取得できること."""
        models = [
            self._make_model(id=1, parliamentary_group_id=10, political_party_id=20),
            self._make_model(id=2, parliamentary_group_id=11, political_party_id=21),
            self._make_model(id=3, parliamentary_group_id=10, political_party_id=22),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = models

        async def async_execute(query):
            return mock_result

        mock_session.execute = async_execute

        result = await repository.get_by_parliamentary_group_ids([10, 11])

        assert len(result) == 3
        assert all(isinstance(e, ParliamentaryGroupParty) for e in result)

    @pytest.mark.asyncio
    async def test_get_by_parliamentary_group_ids_empty_input(
        self, repository, mock_session
    ):
        """空リスト入力で空リストが返ること."""
        result = await repository.get_by_parliamentary_group_ids([])

        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_parliamentary_group_ids_no_match(
        self, repository, mock_session
    ):
        """該当なしで空リストが返ること."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        async def async_execute(query):
            return mock_result

        mock_session.execute = async_execute

        result = await repository.get_by_parliamentary_group_ids([999])

        assert result == []

    @pytest.mark.asyncio
    async def test_clear_primary(self, repository, mock_session):
        """primaryフラグがクリアされること."""
        primary_model = self._make_model(
            id=1, parliamentary_group_id=10, political_party_id=20, is_primary=True
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = primary_model

        async def async_execute(query):
            return mock_result

        mock_session.execute = async_execute
        mock_session.flush = AsyncMock()

        await repository.clear_primary(10)

        assert primary_model.is_primary is False

    @pytest.mark.asyncio
    async def test_clear_primary_no_primary(self, repository, mock_session):
        """primaryが存在しない場合でも正常終了すること."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None

        async def async_execute(query):
            return mock_result

        mock_session.execute = async_execute

        await repository.clear_primary(10)
        # 例外が発生しないこと

    def test_to_entity(self, repository):
        ts = datetime(2024, 6, 15, 12, 0)
        model = self._make_model(
            id=1,
            parliamentary_group_id=10,
            political_party_id=20,
            is_primary=True,
            created_at=ts,
            updated_at=ts,
        )

        entity = repository._to_entity(model)

        assert isinstance(entity, ParliamentaryGroupParty)
        assert entity.id == 1
        assert entity.parliamentary_group_id == 10
        assert entity.political_party_id == 20
        assert entity.is_primary is True
        assert entity.created_at == ts
        assert entity.updated_at == ts

    def test_to_model_new_entity(self, repository):
        entity = ParliamentaryGroupParty(
            parliamentary_group_id=10,
            political_party_id=20,
            is_primary=True,
        )

        model = repository._to_model(entity)

        assert model.id == 0
        assert model.parliamentary_group_id == 10
        assert model.political_party_id == 20
        assert model.is_primary is True

    def test_to_model_existing_entity(self, repository):
        entity = ParliamentaryGroupParty(
            id=5,
            parliamentary_group_id=10,
            political_party_id=20,
            is_primary=False,
        )

        model = repository._to_model(entity)

        assert model.id == 5

    def test_update_model(self, repository):
        model = self._make_model(
            id=1, parliamentary_group_id=10, political_party_id=20, is_primary=False
        )

        entity = ParliamentaryGroupParty(
            id=1,
            parliamentary_group_id=11,
            political_party_id=21,
            is_primary=True,
        )

        repository._update_model(model, entity)

        assert model.parliamentary_group_id == 11
        assert model.political_party_id == 21
        assert model.is_primary is True
