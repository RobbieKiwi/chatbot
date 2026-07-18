from memorylayers.tools.text import content_tokens, fts_query, jaccard


def test_content_tokens_drop_stop_words_and_the_user() -> None:
    assert content_tokens(text="The user is a friend of Jordan's") == frozenset({"friend", "jordan"})


def test_jaccard() -> None:
    assert jaccard(a=frozenset({"a", "b"}), b=frozenset({"b", "c"})) == 1 / 3
    assert jaccard(a=frozenset(), b=frozenset()) == 0.0


def test_fts_query_quotes_and_ors_tokens() -> None:
    assert fts_query(text="Jordan's tango!") == '"jordan" OR "tango"'
    assert fts_query(text="the a") is None
