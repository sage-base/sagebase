"""発言・発言者管理ビューのテスト

統合ページ（conversations/）のテスト
"""

from unittest.mock import MagicMock, patch

from src.application.dtos.speaker_dto import SpeakerMatchingDTO
from src.application.usecases.link_speaker_to_politician_usecase import (
    LinkSpeakerToPoliticianOutputDto,
)
from src.domain.value_objects.speaker_with_conversation_count import (
    SpeakerWithConversationCount,
)
from src.interfaces.web.streamlit.views.conversations.tabs.speakers_list_tab import (  # noqa: E501
    _get_classification_label,
    _get_match_status,
    render_speakers_list_tab,
)


@patch(
    "src.interfaces.web.streamlit.views.conversations.tabs.speakers_list_tab.RepositoryAdapter"
)
@patch("src.interfaces.web.streamlit.views.conversations.tabs.speakers_list_tab.st")
def test_render_speakers_list_tab_displays_placeholder(mock_st, mock_repo_adapter):
    """発言者一覧タブがデータなし時にinfoメッセージを表示することを確認"""
    # RepositoryAdapterのモック（データなし）
    mock_speaker_repo = MagicMock()
    mock_speaker_repo.get_speakers_with_conversation_count.return_value = []
    mock_politician_repo = MagicMock()
    mock_repo_adapter.side_effect = [mock_speaker_repo, mock_politician_repo]

    # st.columns()のモック
    mock_cols = [MagicMock() for _ in range(4)]
    mock_st.columns.return_value = mock_cols

    # st.text_input, st.selectbox, st.number_inputのモック
    mock_st.text_input.return_value = ""
    mock_st.selectbox.return_value = "すべて"
    mock_st.number_input.return_value = 50

    # Act
    render_speakers_list_tab()

    # Assert
    mock_st.info.assert_called_once_with("該当する発言者がありません")


class TestGetMatchStatus:
    """_get_match_status の各分岐テスト."""

    def test_manually_verified_match(self):
        """手動マッチ済みのラベルを返す。"""
        speaker = SpeakerWithConversationCount(
            id=1,
            name="テスト",
            type=None,
            political_party_name=None,
            position=None,
            is_politician=True,
            conversation_count=5,
            politician_id=100,
            is_manually_verified=True,
        )
        assert _get_match_status(speaker) == "手動マッチ済み"

    def test_auto_match(self):
        """自動マッチ済みのラベルを返す。"""
        speaker = SpeakerWithConversationCount(
            id=1,
            name="テスト",
            type=None,
            political_party_name=None,
            position=None,
            is_politician=True,
            conversation_count=5,
            politician_id=100,
            is_manually_verified=False,
        )
        assert _get_match_status(speaker) == "自動マッチ済み"

    def test_non_politician(self):
        """非政治家のラベルを返す。"""
        speaker = SpeakerWithConversationCount(
            id=1,
            name="テスト",
            type=None,
            political_party_name=None,
            position=None,
            is_politician=False,
            conversation_count=5,
        )
        assert _get_match_status(speaker) == "非政治家"

    def test_unmatched(self):
        """未マッチのラベルを返す。"""
        speaker = SpeakerWithConversationCount(
            id=1,
            name="テスト",
            type=None,
            political_party_name=None,
            position=None,
            is_politician=True,
            conversation_count=5,
        )
        assert _get_match_status(speaker) == "未マッチ"


class TestGetClassificationLabel:
    """_get_classification_label の各分岐テスト."""

    def test_valid_skip_reason(self):
        """有効なSkipReasonの表示ラベルを返す。"""
        speaker = SpeakerWithConversationCount(
            id=1,
            name="テスト",
            type=None,
            political_party_name=None,
            position=None,
            is_politician=False,
            conversation_count=5,
            skip_reason="reference_person",
        )
        result = _get_classification_label(speaker)
        assert "REFERENCE_PERSON" in result

    def test_invalid_skip_reason(self):
        """無効なskip_reasonはそのまま返す。"""
        speaker = SpeakerWithConversationCount(
            id=1,
            name="テスト",
            type=None,
            political_party_name=None,
            position=None,
            is_politician=False,
            conversation_count=5,
            skip_reason="unknown_value",
        )
        assert _get_classification_label(speaker) == "unknown_value"

    def test_no_skip_reason(self):
        """skip_reasonがNoneの場合はハイフンを返す。"""
        speaker = SpeakerWithConversationCount(
            id=1,
            name="テスト",
            type=None,
            political_party_name=None,
            position=None,
            is_politician=True,
            conversation_count=5,
        )
        assert _get_classification_label(speaker) == "-"


@patch(
    "src.interfaces.web.streamlit.views.conversations.tabs.speakers_list_tab.RepositoryAdapter"
)
@patch("src.interfaces.web.streamlit.views.conversations.tabs.speakers_list_tab.st")
def test_render_speakers_list_tab_with_data(mock_st, mock_repo_adapter):
    """発言者一覧タブがデータあり時にテーブルと統計を表示することを確認"""
    # テストデータ
    speakers = [
        SpeakerWithConversationCount(
            id=1,
            name="山田太郎",
            type=None,
            political_party_name="自民党",
            position=None,
            is_politician=True,
            conversation_count=10,
            politician_id=100,
        ),
        SpeakerWithConversationCount(
            id=2,
            name="参考人A",
            type=None,
            political_party_name=None,
            position=None,
            is_politician=False,
            conversation_count=3,
            skip_reason="reference_person",
        ),
    ]

    # RepositoryAdapterのモック（speaker_repo, politician_repo + 官僚タブ用）
    mock_speaker_repo = MagicMock()
    mock_speaker_repo.get_speakers_with_conversation_count.return_value = speakers
    mock_politician_repo = MagicMock()
    mock_politician_repo.search_by_name.return_value = []
    mock_official_repo = MagicMock()
    mock_official_repo.search_by_name.return_value = []
    mock_repo_adapter.side_effect = [
        mock_speaker_repo,
        mock_politician_repo,
        mock_official_repo,
        mock_official_repo,
    ]

    # st.columns()のモック（引数に応じた数の要素を返す）
    def columns_side_effect(spec, **kwargs):
        if isinstance(spec, int):
            return [MagicMock() for _ in range(spec)]
        return [MagicMock() for _ in range(len(spec))]

    mock_st.columns.side_effect = columns_side_effect

    # フィルタ入力のモック
    mock_st.text_input.return_value = ""
    mock_st.selectbox.return_value = "すべて"
    mock_st.number_input.return_value = 50
    mock_st.button.return_value = False

    # expanderのモック
    mock_expander = MagicMock()
    mock_st.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
    mock_st.expander.return_value.__exit__ = MagicMock(return_value=None)

    # tabsのモック（政治家にマッチ、官僚に紐付け、非政治家として分類の3タブ）
    mock_tab1 = MagicMock()
    mock_tab2 = MagicMock()
    mock_tab3 = MagicMock()
    mock_st.tabs.return_value = [mock_tab1, mock_tab2, mock_tab3]

    # Act
    render_speakers_list_tab()

    # Assert
    # dataframeが呼ばれたことを確認
    mock_st.dataframe.assert_called_once()
    # メトリクスが呼ばれたことを確認（表示中、マッチ済み、未マッチ、非政治家の4つ）
    metric_calls = mock_st.metric.call_args_list
    assert len(metric_calls) == 4
    # 表示中メトリクスの値確認
    assert metric_calls[0] == (("表示中", "2件"),)


@patch("src.interfaces.web.streamlit.views.conversations.tabs.matching_tab.st")
@patch(
    "src.interfaces.web.streamlit.views.conversations.tabs.matching_tab.google_sign_in"
)
def test_render_matching_tab_requires_login(mock_auth, mock_st):
    """発言マッチングタブがログインを要求することを確認"""
    # Arrange
    from src.interfaces.web.streamlit.views.conversations.tabs.matching_tab import (
        render_matching_tab,
    )

    mock_auth.get_user_info.return_value = None  # 未ログイン

    # Act
    render_matching_tab()

    # Assert
    mock_st.warning.assert_called_once_with(
        "ユーザー情報を取得できません。ログインしてください。"
    )


@patch(
    "src.interfaces.web.streamlit.views.conversations.tabs.matching_tab.RepositoryAdapter"
)
@patch("src.interfaces.web.streamlit.views.conversations.tabs.matching_tab.st")
@patch(
    "src.interfaces.web.streamlit.views.conversations.tabs.matching_tab.google_sign_in"
)
def test_render_matching_tab_with_login(mock_auth, mock_st, mock_repo_adapter):
    """発言マッチングタブがログイン時にユーザー情報を表示することを確認"""
    # Arrange
    from src.interfaces.web.streamlit.views.conversations.tabs.matching_tab import (
        render_matching_tab,
    )

    # ログイン状態をモック
    mock_auth.get_user_info.return_value = {
        "email": "test@example.com",
        "name": "Test User",
        "picture": "https://example.com/picture.jpg",
    }

    # st.button()をモック（クリックされていない）
    mock_st.button.return_value = False

    # st.number_input()をモック
    mock_st.number_input.return_value = 10

    # st.selectbox()をモック
    mock_st.selectbox.return_value = "すべて"

    # st.columns()をモック
    mock_col1 = MagicMock()
    mock_col2 = MagicMock()
    mock_st.columns.return_value = (mock_col1, mock_col2)

    # st.session_state.get()をモック
    mock_st.session_state.get.return_value = []

    # RepositoryAdapterのモック
    mock_meeting_repo = MagicMock()
    mock_meeting_repo.get_all.return_value = []
    mock_repo_adapter.return_value = mock_meeting_repo

    # Act
    render_matching_tab()

    # Assert
    # ユーザー情報が表示されることを確認
    mock_st.info.assert_called()
    # get_user_info()が呼ばれたことを確認
    mock_auth.get_user_info.assert_called_once()


@patch("src.interfaces.web.streamlit.views.conversations.tabs.statistics_tab.st")
def test_render_statistics_tab_displays_metrics(mock_st):
    """統計情報タブがメトリックを表示することを確認"""
    # Arrange
    from src.interfaces.web.streamlit.views.conversations.tabs.statistics_tab import (
        render_statistics_tab,
    )

    # st.columns()をモック
    mock_col1 = MagicMock()
    mock_col2 = MagicMock()
    mock_col3 = MagicMock()
    mock_st.columns.return_value = (mock_col1, mock_col2, mock_col3)

    # Act
    render_statistics_tab()

    # Assert
    mock_st.subheader.assert_called_once_with("統計情報")
    mock_st.columns.assert_called()


def test_render_conversations_page_return_type():
    """render_conversations_page関数の戻り値型がNoneであることを確認"""
    import inspect

    from src.interfaces.web.streamlit.views.conversations.page import (
        render_conversations_page,
    )

    sig = inspect.signature(render_conversations_page)
    assert sig.return_annotation is None


def test_user_info_type_hint_is_correct():
    """user_infoの型ヒントが正しいことを確認"""
    import inspect

    from src.interfaces.web.streamlit.views.conversations.tabs.matching_tab import (
        render_matching_tab,
    )

    # 関数のソースコードから型ヒントを確認
    source = inspect.getsource(render_matching_tab)
    # user_infoの型ヒントがdict[str, str] | Noneであることを確認
    assert "user_info: dict[str, str] | None" in source


# ===== render_politician_creation_form のテスト =====


@patch(
    "src.interfaces.web.streamlit.views.conversations.components.politician_creation_form.Container"
)
@patch(
    "src.interfaces.web.streamlit.views.conversations.components.politician_creation_form.PoliticianPresenter"
)
@patch(
    "src.interfaces.web.streamlit.views.conversations.components.politician_creation_form.st"
)
def test_render_politician_creation_form_displays_form(
    mock_st, mock_presenter_class, mock_container
):
    """政治家作成フォームが表示されることを確認"""
    # Arrange
    from src.interfaces.web.streamlit.views.conversations.components.politician_creation_form import (  # noqa: E501
        render_politician_creation_form,
    )

    result = SpeakerMatchingDTO(
        speaker_id=1,
        speaker_name="山田太郎",
        matched_politician_id=None,
        matched_politician_name=None,
        confidence_score=0.0,
        matching_method="none",
    )

    # Presenterのモック
    mock_presenter = MagicMock()
    mock_presenter.get_all_parties.return_value = []
    mock_presenter_class.return_value = mock_presenter

    # st.form()のモック
    mock_form_context = MagicMock()
    mock_st.form.return_value.__enter__ = MagicMock(return_value=mock_form_context)
    mock_st.form.return_value.__exit__ = MagicMock(return_value=None)

    # st.columns()のモック
    mock_col1 = MagicMock()
    mock_col2 = MagicMock()
    mock_st.columns.return_value = (mock_col1, mock_col2)

    # st.form_submit_button()のモック（クリックされていない）
    mock_st.form_submit_button.return_value = False

    # st.session_state.get()のモック
    mock_st.session_state.get.return_value = None

    # Act
    render_politician_creation_form(result=result, user_id=None)

    # Assert
    # フォームのタイトルが表示されることを確認
    mock_st.markdown.assert_any_call("#### 🆕 「山田太郎」の政治家を新規作成")
    # フォームが作成されることを確認
    mock_st.form.assert_called_once()


@patch(
    "src.interfaces.web.streamlit.views.conversations.components.politician_creation_form.asyncio"
)
@patch(
    "src.interfaces.web.streamlit.views.conversations.components.politician_creation_form.Container"
)
@patch(
    "src.interfaces.web.streamlit.views.conversations.components.politician_creation_form.PoliticianPresenter"
)
@patch(
    "src.interfaces.web.streamlit.views.conversations.components.politician_creation_form.st"
)
def test_render_politician_creation_form_creates_politician_and_links(
    mock_st, mock_presenter_class, mock_container, mock_asyncio
):
    """政治家作成と紐付けが成功することを確認"""
    # Arrange
    from src.interfaces.web.streamlit.views.conversations.components.politician_creation_form import (  # noqa: E501
        render_politician_creation_form,
    )

    result = SpeakerMatchingDTO(
        speaker_id=1,
        speaker_name="山田太郎",
        matched_politician_id=None,
        matched_politician_name=None,
        confidence_score=0.0,
        matching_method="none",
    )

    # Presenterのモック
    mock_presenter = MagicMock()
    mock_presenter.get_all_parties.return_value = []
    mock_presenter.create.return_value = (True, 100, None)  # 成功、ID=100
    mock_presenter_class.return_value = mock_presenter

    # Containerのモック
    mock_link_usecase = MagicMock()
    mock_use_cases = mock_container.create_for_environment.return_value.use_cases
    mock_use_cases.link_speaker_to_politician_usecase.return_value = mock_link_usecase

    # UseCaseの戻り値をモック
    mock_updated_dto = SpeakerMatchingDTO(
        speaker_id=1,
        speaker_name="山田太郎",
        matched_politician_id=100,
        matched_politician_name="山田太郎",
        confidence_score=1.0,
        matching_method="manual",
        matching_reason="手動で政治家を作成・紐付け",
    )
    mock_asyncio.run.return_value = LinkSpeakerToPoliticianOutputDto(
        success=True,
        updated_matching_dto=mock_updated_dto,
    )

    # st.form()のモック
    mock_form_context = MagicMock()
    mock_st.form.return_value.__enter__ = MagicMock(return_value=mock_form_context)
    mock_st.form.return_value.__exit__ = MagicMock(return_value=None)

    # st.columns()のモック
    mock_col1 = MagicMock()
    mock_col2 = MagicMock()
    mock_st.columns.return_value = (mock_col1, mock_col2)

    # フォーム入力値のモック
    mock_st.text_input.side_effect = ["山田太郎", "東京", ""]  # 名前、選挙区、URL
    mock_st.selectbox.side_effect = ["東京都", "無所属"]  # 都道府県、政党

    # submit buttonがクリックされた状態
    mock_st.form_submit_button.side_effect = [True, False]  # 登録ボタンクリック

    # st.session_state.get()のモック
    mock_st.session_state.get.return_value = []

    # Act
    render_politician_creation_form(result=result, user_id=None)

    # Assert
    # Presenterのcreateが呼ばれたことを確認
    mock_presenter.create.assert_called_once()


@patch(
    "src.interfaces.web.streamlit.views.conversations.components.politician_creation_form.Container"
)
@patch(
    "src.interfaces.web.streamlit.views.conversations.components.politician_creation_form.PoliticianPresenter"
)
@patch(
    "src.interfaces.web.streamlit.views.conversations.components.politician_creation_form.st"
)
def test_render_politician_creation_form_validates_required_fields(
    mock_st, mock_presenter_class, mock_container
):
    """必須フィールドのバリデーションが機能することを確認"""
    # Arrange
    from src.interfaces.web.streamlit.views.conversations.components.politician_creation_form import (  # noqa: E501
        render_politician_creation_form,
    )

    result = SpeakerMatchingDTO(
        speaker_id=1,
        speaker_name="山田太郎",
        matched_politician_id=None,
        matched_politician_name=None,
        confidence_score=0.0,
        matching_method="none",
    )

    # Presenterのモック
    mock_presenter = MagicMock()
    mock_presenter.get_all_parties.return_value = []
    mock_presenter_class.return_value = mock_presenter

    # st.form()のモック
    mock_form_context = MagicMock()
    mock_st.form.return_value.__enter__ = MagicMock(return_value=mock_form_context)
    mock_st.form.return_value.__exit__ = MagicMock(return_value=None)

    # st.columns()のモック
    mock_col1 = MagicMock()
    mock_col2 = MagicMock()
    mock_st.columns.return_value = (mock_col1, mock_col2)

    # 名前が空の場合
    mock_st.text_input.side_effect = ["", "", ""]  # 空の名前
    mock_st.selectbox.side_effect = ["東京都", "無所属"]

    # submit buttonがクリックされた状態
    mock_st.form_submit_button.side_effect = [True, False]

    # st.session_state.get()のモック
    mock_st.session_state.get.return_value = None

    # Act
    render_politician_creation_form(result=result, user_id=None)

    # Assert
    # エラーメッセージが表示されることを確認
    mock_st.error.assert_called_with("名前を入力してください")


@patch(
    "src.interfaces.web.streamlit.views.conversations.components.politician_creation_form.Container"
)
@patch(
    "src.interfaces.web.streamlit.views.conversations.components.politician_creation_form.PoliticianPresenter"
)
@patch(
    "src.interfaces.web.streamlit.views.conversations.components.politician_creation_form.st"
)
def test_render_politician_creation_form_cancel_closes_form(
    mock_st, mock_presenter_class, mock_container
):
    """キャンセルボタンでフォームが閉じることを確認"""
    # Arrange
    from src.interfaces.web.streamlit.views.conversations.components.politician_creation_form import (  # noqa: E501
        render_politician_creation_form,
    )

    result = SpeakerMatchingDTO(
        speaker_id=1,
        speaker_name="山田太郎",
        matched_politician_id=None,
        matched_politician_name=None,
        confidence_score=0.0,
        matching_method="none",
    )

    # Presenterのモック
    mock_presenter = MagicMock()
    mock_presenter.get_all_parties.return_value = []
    mock_presenter_class.return_value = mock_presenter

    # st.form()のモック
    mock_form_context = MagicMock()
    mock_st.form.return_value.__enter__ = MagicMock(return_value=mock_form_context)
    mock_st.form.return_value.__exit__ = MagicMock(return_value=None)

    # st.columns()のモック
    mock_col1 = MagicMock()
    mock_col2 = MagicMock()
    mock_st.columns.return_value = (mock_col1, mock_col2)

    # キャンセルボタンがクリックされた状態
    mock_st.form_submit_button.side_effect = [False, True]  # キャンセルボタンクリック

    # st.session_stateのモック（辞書として振る舞うようにする）
    mock_st.session_state = {}

    # Act
    render_politician_creation_form(result=result, user_id=None)

    # Assert
    # session_stateのshow_formフラグがFalseに設定されることを確認
    assert mock_st.session_state.get(f"show_form_{result.speaker_id}") is False
    # st.rerunが呼ばれたことを確認
    mock_st.rerun.assert_called_once()


# ===== 会議フィルター機能のテスト =====


@patch(
    "src.interfaces.web.streamlit.views.conversations.tabs.matching_tab.RepositoryAdapter"
)
@patch("src.interfaces.web.streamlit.views.conversations.tabs.matching_tab.st")
@patch(
    "src.interfaces.web.streamlit.views.conversations.tabs.matching_tab.google_sign_in"
)
def test_render_matching_tab_displays_meeting_filter(
    mock_auth, mock_st, mock_repo_adapter
):
    """会議選択フィルターが表示されることを確認"""
    # Arrange
    from src.interfaces.web.streamlit.views.conversations.tabs.matching_tab import (
        render_matching_tab,
    )

    # ログイン状態をモック
    mock_auth.get_user_info.return_value = {
        "email": "test@example.com",
        "name": "Test User",
    }

    # st.button()をモック（クリックされていない）
    mock_st.button.return_value = False

    # st.number_input()をモック
    mock_st.number_input.return_value = 10

    # st.selectbox()をモック
    mock_st.selectbox.return_value = "すべて"

    # st.columns()をモック
    mock_col1 = MagicMock()
    mock_col2 = MagicMock()
    mock_st.columns.return_value = (mock_col1, mock_col2)

    # st.session_state.get()をモック
    mock_st.session_state.get.return_value = []

    # 会議データをモック
    mock_meeting = MagicMock()
    mock_meeting.name = "テスト会議"
    mock_meeting.id = 1

    # RepositoryAdapterのモック
    mock_meeting_repo = MagicMock()
    mock_meeting_repo.get_all.return_value = [mock_meeting]

    mock_conversation_repo = MagicMock()
    mock_conversation_repo.get_by_meeting.return_value = []

    # 複数回の呼び出しに対応
    mock_repo_adapter.side_effect = [mock_meeting_repo, mock_conversation_repo]

    # Act
    render_matching_tab()

    # Assert
    # selectboxが呼ばれたことを確認（会議選択用）
    selectbox_calls = list(mock_st.selectbox.call_args_list)
    assert len(selectbox_calls) >= 1
    # 会議選択のselectboxが呼ばれていることを確認
    assert any("会議選択" in str(call) for call in selectbox_calls)


@patch(
    "src.interfaces.web.streamlit.views.conversations.tabs.matching_tab.RepositoryAdapter"
)
@patch("src.interfaces.web.streamlit.views.conversations.tabs.matching_tab.st")
@patch(
    "src.interfaces.web.streamlit.views.conversations.tabs.matching_tab.google_sign_in"
)
def test_render_matching_tab_shows_speaker_count_for_selected_meeting(
    mock_auth, mock_st, mock_repo_adapter
):
    """選択した会議の発言者数が表示されることを確認"""
    # Arrange
    from src.interfaces.web.streamlit.views.conversations.tabs.matching_tab import (
        render_matching_tab,
    )

    # ログイン状態をモック
    mock_auth.get_user_info.return_value = {
        "email": "test@example.com",
        "name": "Test User",
    }

    # st.button()をモック（クリックされていない）
    mock_st.button.return_value = False

    # st.number_input()をモック
    mock_st.number_input.return_value = 10

    # 会議データをモック
    mock_meeting = MagicMock()
    mock_meeting.name = "テスト会議"
    mock_meeting.id = 1

    # 会議が選択された状態をモック
    mock_st.selectbox.return_value = "テスト会議"

    # st.columns()をモック
    mock_col1 = MagicMock()
    mock_col2 = MagicMock()
    mock_st.columns.return_value = (mock_col1, mock_col2)

    # st.session_state.get()をモック
    mock_st.session_state.get.return_value = []

    # 会話データをモック（3人の発言者）
    mock_conv1 = MagicMock()
    mock_conv1.speaker_id = 1
    mock_conv2 = MagicMock()
    mock_conv2.speaker_id = 2
    mock_conv3 = MagicMock()
    mock_conv3.speaker_id = 3

    # RepositoryAdapterのモック
    mock_meeting_repo = MagicMock()
    mock_meeting_repo.get_all.return_value = [mock_meeting]

    mock_conversation_repo = MagicMock()
    mock_conversation_repo.get_by_meeting.return_value = [
        mock_conv1,
        mock_conv2,
        mock_conv3,
    ]

    mock_repo_adapter.side_effect = [mock_meeting_repo, mock_conversation_repo]

    # Act
    render_matching_tab()

    # Assert
    # captionが呼ばれたことを確認（発言者数表示）
    caption_calls = [str(call) for call in mock_st.caption.call_args_list]
    # 発言者数のキャプションが表示されていることを確認
    assert any("発言者数" in call for call in caption_calls)
