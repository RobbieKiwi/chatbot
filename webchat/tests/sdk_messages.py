"""Claude Agent SDK messages as the CLI would send them, for tests."""

from claude_agent_sdk import ResultMessage, StreamEvent


def text_delta(*, text: str, session_id: str = "s1", in_subagent: bool = False) -> StreamEvent:
    return StreamEvent(
        uuid="u",
        session_id=session_id,
        event={"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": text}},
        parent_tool_use_id="toolu_1" if in_subagent else None,
    )


def block_start(*, block_type: str, session_id: str = "s1") -> StreamEvent:
    return StreamEvent(uuid="u", session_id=session_id, event={"type": "content_block_start", "index": 0, "content_block": {"type": block_type}})


def result(*, session_id: str = "s1", error: str | None = None, errors: list[str] | None = None) -> ResultMessage:
    failed = error is not None or errors is not None
    return ResultMessage(
        subtype="error_during_execution" if failed else "success",
        duration_ms=1,
        duration_api_ms=1,
        is_error=failed,
        num_turns=1,
        session_id=session_id,
        result=error,
        errors=errors,
    )
