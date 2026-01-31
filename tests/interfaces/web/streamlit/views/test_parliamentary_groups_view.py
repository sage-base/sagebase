"""議員団管理ビューのテスト"""

import inspect

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_presenter():
    """ParliamentaryGroupPresenterのモック"""
    mock = MagicMock()
    mock.get_all_governing_bodies.return_value = []
    mock.load_data.return_value = []
    return mock


@patch("src.interfaces.web.streamlit.views.parliamentary_groups.tabs.list_tab.st")
def test_render_parliamentary_groups_list_tab_with_no_data(mock_st, mock_presenter):
    """議員団一覧タブがデータなしの場合に情報メッセージを表示することを確認"""
    # Arrange
    from src.interfaces.web.streamlit.views.parliamentary_groups.tabs.list_tab import (
        render_parliamentary_groups_list_tab,
    )

    mock_presenter.get_all_governing_bodies.return_value = []
    mock_presenter.load_data.return_value = []

    # st.selectbox()がコンテキストマネージャーを返すようにモック
    mock_st.selectbox.return_value = "すべて"

    # Act
    render_parliamentary_groups_list_tab(mock_presenter)

    # Assert
    mock_st.info.assert_called_with("議員団が登録されていません")


@patch("src.interfaces.web.streamlit.views.parliamentary_groups.tabs.new_tab.st")
def test_render_new_parliamentary_group_tab_requires_governing_bodies(
    mock_st, mock_presenter
):
    """新規登録タブが開催主体の存在を要求することを確認"""
    # Arrange
    from src.interfaces.web.streamlit.views.parliamentary_groups.tabs.new_tab import (
        render_new_parliamentary_group_tab,
    )

    mock_presenter.get_all_governing_bodies.return_value = []

    # Act
    render_new_parliamentary_group_tab(mock_presenter)

    # Assert
    mock_st.error.assert_called_once_with(
        "開催主体が登録されていません。先に開催主体を登録してください。"
    )


@patch(
    "src.interfaces.web.streamlit.views.parliamentary_groups.subtabs.create_memberships_subtab.st"
)
@patch(
    "src.interfaces.web.streamlit.views.parliamentary_groups.subtabs.create_memberships_subtab.google_sign_in"
)
@patch(
    "src.interfaces.web.streamlit.views.parliamentary_groups.subtabs.create_memberships_subtab.ParliamentaryGroupMemberPresenter"
)
def test_render_create_memberships_subtab_requires_login(
    mock_presenter_class, mock_auth, mock_st
):
    """メンバーシップ作成タブがログインを要求することを確認"""
    # Arrange
    from src.interfaces.web.streamlit.views.parliamentary_groups.subtabs.create_memberships_subtab import (  # noqa: E501
        render_create_memberships_subtab,
    )

    mock_auth.get_user_info.return_value = None  # 未ログイン
    mock_presenter = MagicMock()
    mock_presenter_class.return_value = mock_presenter

    # Act
    render_create_memberships_subtab(mock_presenter)

    # Assert
    mock_st.warning.assert_called_once_with(
        "ユーザー情報を取得できません。ログインしてください。"
    )


def test_function_return_types():
    """View関数の戻り値型がNoneであることを確認"""
    from src.interfaces.web.streamlit.views.parliamentary_groups.page import (
        render_parliamentary_groups_page,
    )
    from src.interfaces.web.streamlit.views.parliamentary_groups.subtabs.create_memberships_subtab import (  # noqa: E501
        render_create_memberships_subtab,
    )
    from src.interfaces.web.streamlit.views.parliamentary_groups.subtabs.duplicate_management_subtab import (  # noqa: E501
        render_duplicate_management_subtab,
    )
    from src.interfaces.web.streamlit.views.parliamentary_groups.subtabs.review_subtab import (  # noqa: E501
        render_member_review_subtab,
    )
    from src.interfaces.web.streamlit.views.parliamentary_groups.subtabs.statistics_subtab import (  # noqa: E501
        render_member_statistics_subtab,
    )
    from src.interfaces.web.streamlit.views.parliamentary_groups.tabs.edit_delete_tab import (  # noqa: E501
        render_edit_delete_tab,
    )
    from src.interfaces.web.streamlit.views.parliamentary_groups.tabs.list_tab import (  # noqa: E501
        render_parliamentary_groups_list_tab,
    )
    from src.interfaces.web.streamlit.views.parliamentary_groups.tabs.member_extraction_tab import (  # noqa: E501
        render_member_extraction_tab,
    )
    from src.interfaces.web.streamlit.views.parliamentary_groups.tabs.member_review_tab import (  # noqa: E501
        render_member_review_tab,
    )
    from src.interfaces.web.streamlit.views.parliamentary_groups.tabs.memberships_list_tab import (  # noqa: E501
        render_memberships_list_tab,
    )
    from src.interfaces.web.streamlit.views.parliamentary_groups.tabs.new_tab import (
        render_new_parliamentary_group_tab,
    )

    functions = [
        render_parliamentary_groups_page,
        render_parliamentary_groups_list_tab,
        render_new_parliamentary_group_tab,
        render_edit_delete_tab,
        render_member_extraction_tab,
        render_member_review_tab,
        render_member_review_subtab,
        render_member_statistics_subtab,
        render_create_memberships_subtab,
        render_memberships_list_tab,
        render_duplicate_management_subtab,
    ]

    for func in functions:
        sig = inspect.signature(func)
        assert sig.return_annotation is None, f"{func.__name__} should return None"


def test_user_info_type_hint_is_correct():
    """user_infoの型ヒントがdict[str, str] | Noneであることを確認"""
    from src.interfaces.web.streamlit.views.parliamentary_groups.subtabs.create_memberships_subtab import (  # noqa: E501
        render_create_memberships_subtab,
    )

    # 関数のソースコードから型ヒントを確認
    source = inspect.getsource(render_create_memberships_subtab)
    # user_infoの型ヒントがdict[str, str] | Noneであることを確認
    assert "user_info: dict[str, str] | None" in source, (
        "user_info should have type hint dict[str, str] | None"
    )
