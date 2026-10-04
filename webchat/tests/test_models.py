import pytest
from pydantic import ValidationError

from webchat.models.chat import CHAT_EVENT, ChatEvent, TextDelta, TurnDone, TurnError, Working
from webchat.models.config import WebchatConfig


@pytest.mark.parametrize("event", [TextDelta(text="Hi"), Working(), TurnDone(), TurnError(message="x", offer_new_conversation=True)])
def test_chat_events_round_trip_through_json(event: ChatEvent) -> None:
    assert CHAT_EVENT.validate_json(CHAT_EVENT.dump_json(event)) == event


def test_chat_event_json_names_its_kind() -> None:
    assert CHAT_EVENT.dump_json(TextDelta(text="Hi")) == b'{"kind":"text","text":"Hi"}'


def test_config_defaults_and_rejects_unknown_keys() -> None:
    assert WebchatConfig().port == 8765
    assert WebchatConfig().passphrase is None
    with pytest.raises(ValidationError):
        WebchatConfig.model_validate({"prot": 1})
