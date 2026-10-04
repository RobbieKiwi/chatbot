"""Turning Claude Agent SDK messages into the chat events the page shows."""

from typing import Any

from claude_agent_sdk import ResultMessage, StreamEvent

from webchat.models.chat import ChatEvent, TextDelta, TurnDone, TurnError, Working

PARAGRAPH_BREAK = "\n\n"


def describe_failure(*, result: ResultMessage) -> str:
    return result.result or "; ".join(result.errors or []) or f"The reply stopped ({result.subtype})"


class ReplyTranslator:
    """
    Translates one turn. Text streams from partial-message events, so complete assistant messages are skipped;
    text written by subagents (the librarian) is not the assistant speaking and is dropped.
    """

    def __init__(self) -> None:
        self._text_seen = False

    def translate(self, *, message: object) -> list[ChatEvent]:
        if isinstance(message, StreamEvent):
            return self._stream_event(event=message.event, in_subagent=message.parent_tool_use_id is not None)
        if isinstance(message, ResultMessage):
            return [TurnError(message=describe_failure(result=message))] if message.is_error else [TurnDone()]
        return []

    def _stream_event(self, *, event: dict[str, Any], in_subagent: bool) -> list[ChatEvent]:
        kind = event.get("type")
        if kind == "content_block_start":
            block_type = event.get("content_block", {}).get("type")
            if block_type == "tool_use":
                return [Working()]
            if block_type == "text" and self._text_seen and not in_subagent:
                return [TextDelta(text=PARAGRAPH_BREAK)]
        if kind == "content_block_delta" and not in_subagent:
            delta = event.get("delta", {})
            if delta.get("type") == "text_delta" and delta.get("text"):
                self._text_seen = True
                return [TextDelta(text=delta["text"])]
        return []
