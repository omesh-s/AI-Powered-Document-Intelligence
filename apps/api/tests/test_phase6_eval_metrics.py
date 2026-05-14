from evals import metrics as M


def test_recall_at_k() -> None:
    assert M.recall_at_k(["a", "b"], ["b", "c", "a"], k=2) == 0.5


def test_keyword_overlap() -> None:
    assert M.keyword_overlap_score("Hello world example", ["world", "missing"]) == 0.5


def test_groundedness_proxy() -> None:
    s = M.groundedness_proxy("alpha beta gamma", ["alpha beta fish"])
    assert 0.0 <= s <= 1.0
