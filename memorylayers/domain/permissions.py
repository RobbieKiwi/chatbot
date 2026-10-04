"""The commands each headless worker may run: the read commands plus its own writes."""

from memorylayers.models.vocab import WorkerKind

_PYTHON = ".venv/Scripts/python -m"
_READS = ["summary", "recall", "facts", "search", "periods", "tags", "status"]
_WRITES = {
    WorkerKind.SCRIBE: ["store", "update", "supersede", "pending", "rolling-summary", "commit"],
    WorkerKind.SUMMARISER: ["refresh-plan", "tag-summary", "period", "era", "high-level-summary", "gaps", "refresh"],
    WorkerKind.CONSOLIDATOR: ["tag", "alias", "fact", "supersede", "refresh"],
}


def allowed_tools(*, kind: WorkerKind) -> list[str]:
    if kind is WorkerKind.MIGRATOR:
        return []  # the migrator answers with JSON and touches nothing
    tools = [f"Bash({_PYTHON} memorylayers {command}:*)" for command in [*_READS, *_WRITES[kind]]]
    if kind is WorkerKind.SCRIBE:
        tools.append(f"Bash({_PYTHON} freshtopics log:*)")
    return tools
