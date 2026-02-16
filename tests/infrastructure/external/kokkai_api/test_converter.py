"""KokkaiSpeechConverter のユニットテスト."""

import pytest

from src.infrastructure.external.kokkai_api.converter import KokkaiSpeechConverter
from src.infrastructure.external.kokkai_api.types import SpeechRecord


def _make_speech(**overrides: object) -> SpeechRecord:
    """テスト用SpeechRecordを生成."""
    defaults = {
        "speech_id": "121705253X00320250423001",
        "issue_id": "121705253X00320250423",
        "session": 213,
        "name_of_house": "衆議院",
        "name_of_meeting": "本会議",
        "issue": "第3号",
        "date": "2025-04-23",
        "speech_order": 1,
        "speaker": "岸田文雄君",
        "speaker_yomi": "きしだふみおくん",
        "speech": "テスト発言です。",
        "speech_url": "https://kokkai.ndl.go.jp/speech/1",
        "meeting_url": "https://kokkai.ndl.go.jp/meeting/1",
        "pdf_url": "https://kokkai.ndl.go.jp/pdf/1",
    }
    defaults.update(overrides)
    return SpeechRecord(**defaults)  # type: ignore[arg-type]


class TestNormalizeSpeakerName:
    """発言者名正規化のテスト."""

    @pytest.mark.parametrize(
        ("input_name", "expected"),
        [
            ("岸田文雄君", "岸田文雄"),
            ("河野太郎さん", "河野太郎"),
            ("山田太郎殿", "山田太郎"),
            ("田中花子氏", "田中花子"),
            ("佐藤一郎", "佐藤一郎"),
            (" 岸田文雄君 ", "岸田文雄"),
            ("", ""),
        ],
    )
    def test_remove_honorifics(self, input_name: str, expected: str) -> None:
        assert KokkaiSpeechConverter.normalize_speaker_name(input_name) == expected

    def test_no_honorific_returns_unchanged(self) -> None:
        assert (
            KokkaiSpeechConverter.normalize_speaker_name("内閣総理大臣")
            == "内閣総理大臣"
        )


class TestBuildConferenceName:
    """Conference名構築のテスト."""

    @pytest.mark.parametrize(
        ("house", "meeting", "expected"),
        [
            ("衆議院", "本会議", "衆議院本会議"),
            ("参議院", "予算委員会", "参議院予算委員会"),
            ("衆議院", "内閣委員会", "衆議院内閣委員会"),
        ],
    )
    def test_concatenate_house_and_meeting(
        self, house: str, meeting: str, expected: str
    ) -> None:
        assert KokkaiSpeechConverter.build_conference_name(house, meeting) == expected


class TestSpeechToConversation:
    """speech -> Conversation 変換のテスト."""

    def test_normal_conversion(self) -> None:
        speech = _make_speech()
        conv = KokkaiSpeechConverter.speech_to_conversation(
            speech, minutes_id=10, speaker_id=5
        )

        assert conv.comment == "テスト発言です。"
        assert conv.sequence_number == 1
        assert conv.minutes_id == 10
        assert conv.speaker_id == 5
        assert conv.speaker_name == "岸田文雄"
        assert conv.is_manually_verified is True

    def test_speaker_id_none(self) -> None:
        speech = _make_speech()
        conv = KokkaiSpeechConverter.speech_to_conversation(speech, minutes_id=10)

        assert conv.speaker_id is None
        assert conv.is_manually_verified is True

    def test_speaker_name_honorific_removed(self) -> None:
        speech = _make_speech(speaker="河野太郎さん")
        conv = KokkaiSpeechConverter.speech_to_conversation(speech, minutes_id=10)

        assert conv.speaker_name == "河野太郎"


class TestSpeechToSpeaker:
    """speech -> Speaker 変換のテスト."""

    def test_normal_conversion(self) -> None:
        speech = _make_speech()
        speaker = KokkaiSpeechConverter.speech_to_speaker(speech)

        assert speaker.name == "岸田文雄"
        assert speaker.name_yomi == "きしだふみお"

    def test_empty_yomi_returns_none(self) -> None:
        speech = _make_speech(speaker_yomi="")
        speaker = KokkaiSpeechConverter.speech_to_speaker(speech)

        assert speaker.name_yomi is None

    def test_yomi_honorific_removed(self) -> None:
        speech = _make_speech(speaker_yomi="やまだたろうくん")
        speaker = KokkaiSpeechConverter.speech_to_speaker(speech)

        assert speaker.name_yomi == "やまだたろう"


class TestBuildMeetingName:
    """会議名構築のテスト."""

    def test_normal_build(self) -> None:
        assert (
            KokkaiSpeechConverter.build_meeting_name(213, "第3号")
            == "第213回国会 第3号"
        )

    def test_single_digit_session(self) -> None:
        result = KokkaiSpeechConverter.build_meeting_name(1, "第1号")
        assert result == "第1回国会 第1号"
