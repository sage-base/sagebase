"""End-to-end tests for hierarchical politician scraping (Issue #614)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.entities.party_scraping_state import PartyScrapingState
from src.domain.value_objects.politician_member_data import PoliticianMemberData
from src.interfaces.cli.commands.politician_commands import PoliticianCommands


@pytest.mark.asyncio
async def test_scrape_politicians_with_hierarchical_flag():
    """Test that --hierarchical flag triggers Agent-based scraping."""
    # Mock database query results
    mock_party_data = MagicMock()
    mock_party_data.id = 1
    mock_party_data.name = "Test Party"
    mock_party_data.members_list_url = "https://example.com/members"

    # Create mock Agent that returns successful state
    mock_agent = AsyncMock()
    final_state = PartyScrapingState(
        current_url="https://example.com/members",
        party_name="Test Party",
        party_id=1,
        max_depth=3,
    )
    # Add some extracted members
    final_state.add_extracted_member(
        PoliticianMemberData(
            name="Test Politician 1",
            furigana="テストセイジカ1",
            district="Test District 1",
            profile_page_url="https://example.com/politician1",
        )
    )
    final_state.add_extracted_member(
        PoliticianMemberData(
            name="Test Politician 2",
            furigana="テストセイジカ2",
            district="Test District 2",
            profile_page_url="https://example.com/politician2",
        )
    )
    final_state.mark_visited("https://example.com/members")
    final_state.mark_visited("https://example.com/page1")

    mock_agent.scrape.return_value = final_state

    # Mock DI container
    mock_container = MagicMock()
    mock_container.use_cases.party_scraping_agent.return_value = mock_agent

    # Mock database operations
    with (
        patch("src.infrastructure.config.database.get_db_engine") as mock_engine,
        patch(
            "src.infrastructure.di.container.get_container",
            return_value=mock_container,
        ),
        patch.dict("os.environ", {"STREAMLIT_RUNNING": "true"}),  # Skip confirmation
    ):
        # Setup database mock
        mock_conn = MagicMock()
        mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = [mock_party_data]

        # Execute command
        await PoliticianCommands._async_scrape_politicians_hierarchical(
            party_id=1, all_parties=False, dry_run=True, max_depth=3
        )

        # Verify Agent was called
        mock_agent.scrape.assert_called_once()
        call_args = mock_agent.scrape.call_args[0][0]
        assert isinstance(call_args, PartyScrapingState)
        assert call_args.party_id == 1
        assert call_args.party_name == "Test Party"
        assert call_args.max_depth == 3
        assert call_args.current_url == "https://example.com/members"


@pytest.mark.asyncio
async def test_scrape_politicians_backward_compatibility():
    """Test that without --hierarchical flag, legacy scraping is used."""
    # Mock database query results
    mock_party_data = MagicMock()
    mock_party_data.id = 1
    mock_party_data.name = "Test Party"
    mock_party_data.members_list_url = "https://example.com/members"

    # Mock legacy components
    mock_extractor = MagicMock()
    mock_result = MagicMock()
    mock_result.members = []
    mock_extractor.extract_from_pages = AsyncMock(return_value=mock_result)

    mock_fetcher = MagicMock()
    # Return at least one page so extract_from_pages is called
    mock_fetcher.fetch_all_pages = AsyncMock(
        return_value=["<html><body>Test page</body></html>"]
    )

    # Mock DI container for extraction logging dependencies
    mock_di_container = MagicMock()
    mock_di_container.repositories.politician_repository.return_value = MagicMock()
    mock_usecases = mock_di_container.use_cases
    mock_usecases.update_politician_from_extraction_usecase.return_value = MagicMock()

    with (
        patch("src.infrastructure.config.database.get_db_engine") as mock_engine,
        patch(
            "src.infrastructure.di.container.get_container",
            return_value=mock_di_container,
        ),
        patch(
            "src.interfaces.factories.party_member_extractor_factory.PartyMemberExtractorFactory.create",
            return_value=mock_extractor,
        ),
        patch(
            "src.party_member_extractor.html_fetcher.PartyMemberPageFetcher",
        ) as mock_fetcher_class,
        patch.dict("os.environ", {"STREAMLIT_RUNNING": "true"}),
    ):
        # Setup database mock
        mock_conn = MagicMock()
        mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = [mock_party_data]

        # Setup fetcher mock
        mock_fetcher_class.return_value.__aenter__.return_value = mock_fetcher

        # Execute command WITHOUT hierarchical flag
        await PoliticianCommands._async_scrape_politicians(
            party_id=1,
            all_parties=False,
            dry_run=True,
            max_pages=10,
            hierarchical=False,  # Legacy mode
            max_depth=3,
        )

        # Verify legacy extractor was used
        mock_extractor.extract_from_pages.assert_called_once()


@pytest.mark.asyncio
async def test_hierarchical_scraping_with_max_depth():
    """Test that max_depth parameter is correctly passed to Agent."""
    mock_party_data = MagicMock()
    mock_party_data.id = 1
    mock_party_data.name = "Test Party"
    mock_party_data.members_list_url = "https://example.com/members"

    # Create mock Agent
    mock_agent = AsyncMock()
    final_state = PartyScrapingState(
        current_url="https://example.com/members",
        party_name="Test Party",
        party_id=1,
        max_depth=5,
    )
    mock_agent.scrape.return_value = final_state

    # Mock DI container
    mock_container = MagicMock()
    mock_container.use_cases.party_scraping_agent.return_value = mock_agent

    with (
        patch("src.infrastructure.config.database.get_db_engine") as mock_engine,
        patch(
            "src.infrastructure.di.container.get_container",
            return_value=mock_container,
        ),
        patch.dict("os.environ", {"STREAMLIT_RUNNING": "true"}),
    ):
        # Setup database mock
        mock_conn = MagicMock()
        mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = [mock_party_data]

        # Execute with custom max_depth
        await PoliticianCommands._async_scrape_politicians_hierarchical(
            party_id=1, all_parties=False, dry_run=True, max_depth=5
        )

        # Verify max_depth was passed correctly
        call_args = mock_agent.scrape.call_args[0][0]
        assert call_args.max_depth == 5


@pytest.mark.asyncio
async def test_hierarchical_scraping_error_handling():
    """Test that errors from Agent are properly handled."""
    mock_party_data = MagicMock()
    mock_party_data.id = 1
    mock_party_data.name = "Test Party"
    mock_party_data.members_list_url = "https://example.com/members"

    # Create mock Agent that returns error state
    mock_agent = AsyncMock()
    final_state = PartyScrapingState(
        current_url="https://example.com/members",
        party_name="Test Party",
        party_id=1,
        max_depth=3,
    )
    final_state.error_message = "Test error message"
    mock_agent.scrape.return_value = final_state

    # Mock DI container
    mock_container = MagicMock()
    mock_container.use_cases.party_scraping_agent.return_value = mock_agent

    with (
        patch("src.infrastructure.config.database.get_db_engine") as mock_engine,
        patch(
            "src.infrastructure.di.container.get_container",
            return_value=mock_container,
        ),
        patch.dict("os.environ", {"STREAMLIT_RUNNING": "true"}),
    ):
        # Setup database mock
        mock_conn = MagicMock()
        mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = [mock_party_data]

        # Execute command - should not raise exception
        await PoliticianCommands._async_scrape_politicians_hierarchical(
            party_id=1, all_parties=False, dry_run=True, max_depth=3
        )

        # Verify Agent was called despite error
        mock_agent.scrape.assert_called_once()
