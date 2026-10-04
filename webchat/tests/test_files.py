from datetime import UTC, datetime

from webchat.adapters.files import append_messages, read_config, read_messages, read_state, write_config, write_state
from webchat.domain.auth import new_passphrase_record
from webchat.models.chat import LoggedMessage, Role
from webchat.models.config import WebchatConfig
from webchat.models.paths import WebchatPaths
from webchat.models.state import WebchatState

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


def test_paths_sit_under_the_data_root(paths: WebchatPaths) -> None:
    assert paths.config == paths.root / "config.json"
    assert paths.conversations == paths.root / "conversations"


def test_missing_config_reads_as_defaults(paths: WebchatPaths) -> None:
    assert read_config(paths=paths) == WebchatConfig()


def test_config_round_trips(paths: WebchatPaths) -> None:
    config = WebchatConfig(port=9000, passphrase=new_passphrase_record(passphrase="p"))
    write_config(paths=paths, config=config)
    assert read_config(paths=paths) == config


def test_state_is_none_until_written(paths: WebchatPaths) -> None:
    assert read_state(paths=paths) is None
    state = WebchatState(session_id="s1", started_at=NOW)
    write_state(paths=paths, state=state)
    assert read_state(paths=paths) == state


def test_messages_append_in_order_per_session(paths: WebchatPaths) -> None:
    first = LoggedMessage(role=Role.ASSISTANT, text="Hello.", at=NOW)
    second = LoggedMessage(role=Role.USER, text="Hi\nthere", at=NOW)
    append_messages(paths=paths, session_id="s1", messages=[first])
    append_messages(paths=paths, session_id="s1", messages=[second])
    assert read_messages(paths=paths, session_id="s1") == [first, second]
    assert read_messages(paths=paths, session_id="s2") == []
