import re
from pathlib import Path

import freshtopics
from freshtopics.word_lists import WORD_LISTS_DIR, read_word_list


def test_seed_words_are_about_1500_distinct_lowercase_nouns() -> None:
    words = read_word_list(name="seed_words.txt")
    assert 1400 <= len(words) <= 1600
    assert len(set(words)) == len(words)
    assert all(re.fullmatch(r"[a-z]+(-[a-z]+)*", word) for word in words), [word for word in words if not re.fullmatch(r"[a-z]+(-[a-z]+)*", word)][:10]


def test_subjects_are_about_200_distinct_fields() -> None:
    subjects = read_word_list(name="subjects.txt")
    assert 180 <= len(subjects) <= 220
    assert len(set(subjects)) == len(subjects)
    assert all(re.fullmatch(r"[a-z][a-z ,'-]*[a-z]", subject) for subject in subjects)


def test_word_lists_ship_in_the_tracked_resources_folder() -> None:
    assert WORD_LISTS_DIR == Path(freshtopics.__file__).parent / "resources"
    assert (WORD_LISTS_DIR / "seed_words.txt").is_file() and (WORD_LISTS_DIR / "subjects.txt").is_file()
