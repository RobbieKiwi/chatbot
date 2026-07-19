"""
Utility functions for freshtopics conversation topic management.

This module provides robust functions for reading, updating, and writing
conversation topics JSON files used by the freshtopics skill.
"""

import json
from datetime import datetime
from pathlib import Path

from freshtopics.models import TopicEntry, TopicsData

DATA_ROOT = Path(__file__).parent / "data"
MAX_TOPICS = 100


def get_topics_file_path(*, parent_name: str) -> Path:
    """The parent's topics file, data/<parent>/topics.json; its directory is created on demand."""
    file_path = DATA_ROOT / parent_name / "topics.json"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    return file_path


def read_topics_data(*, parent_name: str) -> TopicsData:
    """
    Read and parse the conversation topics JSON file.

    Handles edge cases:
    - File doesn't exist: returns empty data structure
    - JSON is corrupted: attempts to recover or create fresh
    - Invalid data structure: returns valid empty structure

    Args:
        parent_name: Name of the parent skill

    Returns:
        TopicsData
    """
    file_path = get_topics_file_path(parent_name=parent_name)

    # Check if file exists
    if not file_path.exists():
        return TopicsData()

    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    return TopicsData.model_validate(data)


def write_topics_data(*, parent_name: str, data: TopicsData) -> bool:
    """
    Write the conversation topics data back to JSON file.

    Args:
        parent_name: Name of the parent skill
        data: TopicsData model with topics data to write

    Returns:
        True if write was successful, False otherwise
    """
    file_path = get_topics_file_path(parent_name=parent_name)

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(data.model_dump_json(indent=2, ensure_ascii=False))
        return True
    except Exception as e:
        print(f"Error writing {file_path}: {e}")
        return False


def create_topic_entry(*, parent_name: str, phrase: str, initiator: str, score: int = 5) -> TopicEntry:
    phrase = phrase.lower().strip()
    return TopicEntry(inserted=datetime.now(), parent_name=parent_name, phrase=phrase, initiator=initiator, score=score)


def add_topic_entry(*, parent_name: str, phrase: str, initiator: str, score: int = 5) -> tuple[TopicsData, bool]:
    """
    Add a new topic entry to the conversation topics data.

    This is the main function for logging topics. It:
    1. Reads current data
    2. Creates new entry
    3. Appends to topics array
    4. Updates terrible_topics and excellent_topics based on score
    5. Trims topics to MAX_TOPICS entries (removes oldest)
    6. Writes back to file

    Args:
        parent_name: Name of the parent skill
        phrase: Topic phrase
        initiator: Who started the topic
        score: User response quality (1-10, optional)

    Returns:
        Tuple of (updated_data, success) where success is True if file was written

    Raises:
        ValueError: If any parameter is invalid
    """
    # Read current data
    data = read_topics_data(parent_name=parent_name)

    # Create new entry
    entry = create_topic_entry(parent_name=parent_name, phrase=phrase, initiator=initiator, score=score)

    # Append to topics
    data.topics.append(entry)

    # Update terrible_topics and excellent_topics based on score
    _update_topic_lists(data=data, topic=entry.phrase, score=score)

    # Trim topics to MAX_TOPICS (remove oldest first)
    if len(data.topics) > MAX_TOPICS:
        data.topics = data.topics[-MAX_TOPICS:]

    # Write back to file
    success = write_topics_data(parent_name=parent_name, data=data)

    return data, success


def _update_topic_lists(*, data: TopicsData, topic: str, score: int) -> None:
    """
    Update terrible_topics and excellent_topics lists based on score.

    Rules:
    - If score <= 3: add to terrible_topics (or ensure it's there)
    - If score >= 7: add to excellent_topics (or ensure it's there)
    - If score 4-6: remove from both lists if present

    Args:
        data: The topics data model (modified in place)
        topic: The topic phrase
        score: The score for the topic
    """
    # Convert to sets for easier manipulation
    terrible_set = set(data.terrible_topics)
    excellent_set = set(data.excellent_topics)

    if score <= 3:
        # Add to terrible, remove from excellent
        terrible_set.add(topic)
        excellent_set.discard(topic)
    elif score >= 7:
        # Add to excellent, remove from terrible
        excellent_set.add(topic)
        terrible_set.discard(topic)
    else:
        # Score 4-6: remove from both lists
        terrible_set.discard(topic)
        excellent_set.discard(topic)

    # Convert back to lists
    data.terrible_topics = sorted(list(terrible_set))
    data.excellent_topics = sorted(list(excellent_set))


def get_recent_topics(*, parent_name: str, count: int = 10) -> list[TopicEntry]:
    """
    Get the most recent topics.

    Args:
        parent_name: Name of the parent skill
        count: Number of recent topics to return

    Returns:
        List of most recent topic entries (most recent last)
    """
    data = read_topics_data(parent_name=parent_name)
    return data.topics[-count:] if count else []


def get_terrible_topics(*, parent_name: str) -> list[str]:
    """
    Get the list of terrible topics.

    Args:
        parent_name: Name of the parent skill

    Returns:
        List of terrible topic phrases
    """
    data = read_topics_data(parent_name=parent_name)
    return data.terrible_topics


def get_excellent_topics(*, parent_name: str) -> list[str]:
    """
    Get the list of excellent topics.

    Args:
        parent_name: Name of the parent skill

    Returns:
        List of excellent topic phrases
    """
    data = read_topics_data(parent_name=parent_name)
    return data.excellent_topics


def get_topic_summary(*, parent_name: str, recent_count: int = 10) -> dict:
    """
    Get a complete summary of topics for a parent skill.

    This is the main function for getting all topic data in one call.
    It combines recent topics, terrible topics, and excellent topics.

    Args:
        parent_name: Name of the parent skill
        recent_count: Number of recent topics to return (default 10)

    Returns:
        Dictionary containing:
        - recent_topics: List of most recent TopicEntry models
        - terrible_topics: List of disliked topic phrases
        - excellent_topics: List of liked topic phrases
    """
    data = read_topics_data(parent_name=parent_name)
    return {"recent_topics": data.topics[-recent_count:] if recent_count else [], "terrible_topics": data.terrible_topics, "excellent_topics": data.excellent_topics}
