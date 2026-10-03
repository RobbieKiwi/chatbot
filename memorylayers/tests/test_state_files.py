import threading
from datetime import UTC, datetime

from memorylayers.adapters.state_files import list_conversations, load_config, load_conversation, save_conversation, update_conversation, write_model
from memorylayers.models.config import MemoryConfig
from memorylayers.models.conversation import ConversationState
from memorylayers.models.paths import ParentPaths

NOW = datetime(2026, 10, 3, 18, 0, tzinfo=UTC)


def _conversation(*, conversation_id: str, hour: int) -> ConversationState:
    at = NOW.replace(hour=hour)
    return ConversationState(id=conversation_id, started_at=at, last_activity=at)


def test_paths_live_under_the_data_root(paths: ParentPaths) -> None:
    assert paths.db.name == "memory.db"
    assert paths.root.parent.name == "data"


def test_config_defaults_and_overrides(paths: ParentPaths) -> None:
    assert load_config(paths=paths) == MemoryConfig()
    write_model(path=paths.config, value=MemoryConfig(idle_hours=3))
    assert load_config(paths=paths).idle_hours == 3


def test_conversations_list_oldest_activity_first(paths: ParentPaths) -> None:
    save_conversation(paths=paths, state=_conversation(conversation_id="b", hour=19))
    save_conversation(paths=paths, state=_conversation(conversation_id="a", hour=10))
    assert [state.id for state in list_conversations(paths=paths)] == ["a", "b"]


def test_concurrent_updates_lose_nothing(paths: ParentPaths) -> None:
    save_conversation(paths=paths, state=_conversation(conversation_id="c", hour=10))

    def append_many(offset: int) -> None:
        for number in range(50):
            update_conversation(paths=paths, conversation_id="c", change=lambda state, n=number: state.ledger.append(offset + n))

    threads = [threading.Thread(target=append_many, args=(offset,)) for offset in (0, 1000)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(load_conversation(paths=paths, conversation_id="c").ledger) == 100


def test_a_fresh_data_root_is_created_on_first_write(paths: ParentPaths) -> None:
    assert not paths.root.exists()
    write_model(path=paths.config, value=MemoryConfig())
    assert paths.config.exists()
