"""Tests for conference member CLI commands"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from click.testing import CliRunner

from src.interfaces.cli.commands.conference_member_commands import (
    ConferenceMemberCommands,
)


class TestConferenceMemberCommands:
    """Test cases for conference member CLI commands"""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner"""
        return CliRunner()

    @pytest.fixture
    def mock_progress(self):
        """Create a mock progress tracker"""
        with patch("src.interfaces.cli.progress.ProgressTracker") as mock:
            progress_instance = Mock()
            progress_instance.__enter__ = Mock(return_value=progress_instance)
            progress_instance.__exit__ = Mock(return_value=None)
            progress_instance.start = Mock()
            progress_instance.update = Mock()
            progress_instance.finish = Mock()
            progress_instance.set_description = Mock()
            mock.return_value = progress_instance
            yield progress_instance

    def test_extract_conference_members_success(self, runner, mock_progress):
        """Test successful extraction of conference members"""
        with patch(
            "src.interfaces.cli.commands.conference_member_commands.RepositoryAdapter"
        ) as mock_adapter_class:
            with patch(
                "src.interfaces.cli.commands.conference_member_commands"
                ".ConferenceMemberExtractor"
            ) as mock_extractor_class:
                # Setup mocks
                mock_conf_repo = MagicMock()
                mock_conf_repo.get_conference_by_id.return_value = {
                    "id": 1,
                    "name": "本会議",
                    "members_introduction_url": "https://example.com/members",
                }
                mock_conf_repo.close = Mock()

                mock_member_repo = MagicMock()
                mock_member_repo.close = Mock()

                # Set up RepositoryAdapter to return different repos based on the type
                def adapter_side_effect(impl_class):
                    # Check ExtractedConferenceMember first (contains "Conference")
                    if "ExtractedConferenceMember" in impl_class.__name__:
                        return mock_member_repo
                    elif "Conference" in impl_class.__name__:
                        return mock_conf_repo
                    return MagicMock()

                mock_adapter_class.side_effect = adapter_side_effect

                mock_extractor = Mock()
                mock_extractor.extract_and_save_members = AsyncMock(
                    return_value={
                        "extracted_count": 5,
                        "saved_count": 5,
                        "failed_count": 0,
                    }
                )
                mock_extractor.close = Mock()
                mock_extractor_class.return_value = mock_extractor

                # Execute
                result = runner.invoke(
                    ConferenceMemberCommands.extract_conference_members,
                    ["--conference-id", "1"],
                )

                # Assert
                assert result.exit_code == 0
                assert "📋 会議体メンバー情報の抽出を開始します" in result.output
                assert "=== 抽出完了 ===" in result.output
                assert "✅ 抽出総数: 5人" in result.output
                assert "✅ 保存総数: 5人" in result.output
                mock_extractor.extract_and_save_members.assert_called_once()

    def test_extract_conference_members_with_force(self, runner, mock_progress):
        """Test extraction with force flag"""
        with patch(
            "src.interfaces.cli.commands.conference_member_commands.RepositoryAdapter"
        ) as mock_adapter_class:
            with patch(
                "src.interfaces.cli.commands.conference_member_commands"
                ".ConferenceMemberExtractor"
            ) as mock_extractor_class:
                # Setup mocks
                mock_conf_repo = MagicMock()
                mock_conf_repo.get_conference_by_id.return_value = {
                    "id": 1,
                    "name": "本会議",
                    "members_introduction_url": "https://example.com/members",
                }
                mock_conf_repo.close = Mock()

                mock_member_repo = MagicMock()
                # Ensure delete_extracted_members returns an integer, not a Mock
                mock_member_repo.delete_extracted_members.return_value = 2
                mock_member_repo.close = Mock()

                # Set up RepositoryAdapter to return different repos based on the type
                def adapter_side_effect(impl_class):
                    class_name = impl_class.__name__
                    # Check ExtractedConferenceMember first (contains "Conference")
                    if "ExtractedConferenceMember" in class_name:
                        return mock_member_repo
                    elif "Conference" in class_name:
                        return mock_conf_repo
                    return MagicMock()

                mock_adapter_class.side_effect = adapter_side_effect

                mock_extractor = Mock()
                mock_extractor.extract_and_save_members = AsyncMock(
                    return_value={
                        "extracted_count": 3,
                        "saved_count": 3,
                        "failed_count": 0,
                    }
                )
                mock_extractor.close = Mock()
                mock_extractor_class.return_value = mock_extractor

                # Execute with --force
                result = runner.invoke(
                    ConferenceMemberCommands.extract_conference_members,
                    ["--conference-id", "1", "--force"],
                )

                # Assert
                assert result.exit_code == 0
                assert "既存の抽出データ2件を削除しました" in result.output
                mock_member_repo.delete_extracted_members.assert_called_once_with(1)
                mock_extractor.extract_and_save_members.assert_called_once()

    def test_member_status_success(self, runner):
        """Test member status command"""
        with patch(
            "src.interfaces.cli.commands.conference_member_commands.RepositoryAdapter"
        ) as mock_adapter_class:
            # Setup mocks
            mock_repo = MagicMock()
            mock_repo.get_extraction_summary.return_value = {
                "total": 10,
            }
            mock_repo.get_all_extracted_members.return_value = []
            mock_repo.close = Mock()
            mock_adapter_class.return_value = mock_repo

            # Execute
            result = runner.invoke(
                ConferenceMemberCommands.member_status, ["--conference-id", "1"]
            )

            # Assert
            assert result.exit_code == 0
            assert "総件数: 10件" in result.output
            # マッチング関連の出力は削除されている
            assert "💡 政治家との紐付けはStreamlit UI" in result.output

    def test_extract_conference_members_error(self, runner):
        """Test extraction error handling"""
        with patch(
            "src.interfaces.cli.commands.conference_member_commands.RepositoryAdapter"
        ) as mock_adapter_class:
            # Setup mock conference repo that returns None
            mock_conf_repo = MagicMock()
            mock_conf_repo.get_conference_by_id.return_value = None
            mock_conf_repo.close = Mock()
            mock_adapter_class.return_value = mock_conf_repo

            # Execute
            result = runner.invoke(
                ConferenceMemberCommands.extract_conference_members,
                ["--conference-id", "999"],
            )

            # Assert
            assert (
                result.exit_code == 0
            )  # Command returns normally after printing error
            assert "会議体ID 999 が見つかりません" in result.output
