from autoformfill.filler import best_option
from autoformfill.mapper import _normalise
from autoformfill.scanner import FormField, Option

OPTS = [Option("Select Country", ""), Option("India", "IN"), Option("Indonesia", "ID"),
        Option("United States", "US")]


def test_exact_label_and_value():
    assert best_option("India", OPTS) == 1
    assert best_option("us", OPTS) == 3


def test_partial_prefers_shortest_match():
    assert best_option("Ind", OPTS) == 1


def test_no_match_returns_none():
    assert best_option("Germany", OPTS) is None
    assert best_option("", OPTS) is None


def test_normalise_checkbox_values():
    group = FormField("f1", "checkbox", options=[Option("A", "a"), Option("B", "b")])
    single = FormField("f2", "checkbox", options=[Option("Subscribe", "on")])
    assert _normalise(group, "A") == ["A"]
    assert _normalise(single, True) == ["Subscribe"]
    assert _normalise(group, True) is None
    assert _normalise(FormField("f3", "text"), "") is None


def test_short_option_does_not_match_inside_a_word():
    skills = [Option("C", "c"), Option("Java", "java"), Option("Python", "py")]
    assert best_option("JavaScript", skills) is None
    assert best_option("C", skills) == 0
    assert best_option("Python, SQL", skills) == 2
