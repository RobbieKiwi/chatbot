"""The slice of conversation a scribe run files."""

from memorylayers.models.transcript import ConversationTurns, ScribeWindow, Turn


def unprocessed_chars(*, turns: list[Turn]) -> int:
    return sum(len(turn.text) for turn in turns)


def select_window(*, turns: ConversationTurns, threshold_chars: int, overlap_fraction: float) -> ScribeWindow:
    new: list[Turn] = []
    total = 0
    for turn in turns.unprocessed:
        new.append(turn)
        total += len(turn.text)
        if total >= threshold_chars:
            break
    taken = {(turn.session_id, turn.line) for turn in new}
    end: dict[str, int] = {}
    for session_id, last_line in turns.ends.items():
        remaining = [turn for turn in turns.unprocessed if turn.session_id == session_id and (turn.session_id, turn.line) not in taken]
        end[session_id] = remaining[0].line if remaining else last_line
    context: list[Turn] = []
    budget = threshold_chars * overlap_fraction
    used = 0
    for turn in reversed(turns.processed):
        if used >= budget:
            break
        context.insert(0, turn)
        used += len(turn.text)
    return ScribeWindow(context=context, new=new, end=end)
