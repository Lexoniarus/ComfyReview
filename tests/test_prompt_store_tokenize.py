from prompt_store import tokenize


def test_tokenize_splits_only_by_comma_and_keeps_content() -> None:
    text = "a, b ,(c:1.2), d\n e"
    toks = tokenize(text)
    assert toks == ["a", "b", "(c:1.2)", "d  e"]


def test_tokenize_empty() -> None:
    assert tokenize("") == []
    assert tokenize(None) == []
