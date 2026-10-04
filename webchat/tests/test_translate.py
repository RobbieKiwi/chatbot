from claude_agent_sdk import AssistantMessage, TextBlock

from webchat.domain.translate import PARAGRAPH_BREAK, ReplyTranslator
from webchat.models.chat import TextDelta, TurnDone, TurnError, Working
from webchat.tests.sdk_messages import block_start, result, text_delta


def test_text_deltas_become_text_events() -> None:
    translator = ReplyTranslator()
    assert translator.translate(message=text_delta(text="Hello")) == [TextDelta(text="Hello")]


def test_tool_use_shows_working() -> None:
    assert ReplyTranslator().translate(message=block_start(block_type="tool_use")) == [Working()]


def test_later_text_blocks_start_a_new_paragraph() -> None:
    translator = ReplyTranslator()
    assert translator.translate(message=block_start(block_type="text")) == []
    translator.translate(message=text_delta(text="Let me look."))
    assert translator.translate(message=block_start(block_type="text")) == [TextDelta(text=PARAGRAPH_BREAK)]


def test_subagent_text_is_not_shown() -> None:
    assert ReplyTranslator().translate(message=text_delta(text="librarian notes", in_subagent=True)) == []


def test_success_result_ends_the_turn() -> None:
    assert ReplyTranslator().translate(message=result()) == [TurnDone()]


def test_error_result_carries_its_text() -> None:
    assert ReplyTranslator().translate(message=result(error="Usage limit reached")) == [TurnError(message="Usage limit reached")]


def test_error_result_without_text_uses_its_errors() -> None:
    assert ReplyTranslator().translate(message=result(errors=["a", "b"])) == [TurnError(message="a; b")]


def test_complete_assistant_messages_are_ignored() -> None:
    message = AssistantMessage(content=[TextBlock(text="Hello")], model="m")
    assert ReplyTranslator().translate(message=message) == []
