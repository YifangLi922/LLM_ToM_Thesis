"""规则评分（scoring.py）：规范化、日期/单位、否定、与另一条件 gold 的区分。离线。"""
from __future__ import annotations

import pytest

from scoring import answer_kind, matches, rule_score, tokens


def verdict(answer, own, alt):
    return rule_score(answer, own, alt).verdict


# ----------------------------------------------------------------- 基本匹配与复数/大小写/标点
@pytest.mark.parametrize("answer", ["Fungi", "fungi.", "FUNGI", "They are fungi", "Fungi (not plants)"])
def test_correct_when_only_own_gold_matches(answer):
    assert verdict(answer, ["fungi", "fungus"], ["plants"]) == "correct"


@pytest.mark.parametrize("answer", ["Plants", "plant", "The plant kingdom"])
def test_wrong_alt_when_only_the_other_gold_matches(answer):
    assert verdict(answer, ["fungi"], ["plants"]) == "wrong_alt"


def test_plural_stemming():
    assert verdict("Lungs", ["lung"], ["gills"]) == "correct"
    assert verdict("gill", ["lungs"], ["gills"]) == "wrong_alt"


# ----------------------------------------------------------------- 否定：不能因为包含关键词就判对
def test_negated_keyword_is_not_a_match():
    assert not matches("Fungi, not plants", ["plants"])
    assert verdict("Fungi, not plants", ["fungi"], ["plants"]) == "correct"
    assert verdict("Not fungi", ["fungi"], ["plants"]) == "undecided"          # 唯一的匹配被否定 -> 交给裁判
    assert verdict("It cannot travel", ["can travel"], ["cannot travel"]) == "wrong_alt"


def test_gold_that_itself_contains_negation_still_matches():
    assert verdict("Sound cannot travel through a vacuum", ["cannot travel"], ["can travel"]) == "correct"
    assert verdict("No change", ["No change; retain the bell-ringing sound effect."], ["Remove the bell-ringing sound effect."]) == "correct"


def test_both_or_neither_is_undecided():
    assert verdict("Plants and fungi", ["fungi"], ["plants"]) == "undecided"
    assert verdict("Mosses", ["fungi"], ["plants"]) == "undecided"
    assert verdict("", ["fungi"], ["plants"]) == "undecided"


def test_long_answers_go_to_the_judge():
    long = "fungi " + " ".join(["because"] * 40)
    assert verdict(long, ["fungi"], ["plants"]) == "undecided"


# ----------------------------------------------------------------- 日期 / 数字 / 单位
@pytest.mark.parametrize("answer", ["2 October", "October 2", "October 2nd", "2nd of October", "Oct 2", "the 2nd October"])
def test_date_formats_are_normalised(answer):
    assert verdict(answer, ["2 October"], ["8 November"]) == "correct"
    assert verdict(answer.replace("2", "8").replace("October", "November").replace("Oct", "Nov"), ["2 October"], ["8 November"]) == "wrong_alt"


def test_month_only_answers():
    assert verdict("March", ["March"], ["August"]) == "correct"
    assert verdict("In August.", ["March"], ["August"]) == "wrong_alt"


def test_number_words_and_digits():
    assert verdict("six", ["6"], ["10"]) == "correct"
    assert verdict("10 photographs", ["6"], ["10"]) == "wrong_alt"


@pytest.mark.parametrize("answer", ["%", "percent", "Percent (%)", "per cent"])
def test_percent_variants(answer):
    assert verdict(answer, ["%"], ["°C"]) == "correct"


@pytest.mark.parametrize("answer", ["°C", "℃", "degrees Celsius", "Celsius", "° C"])
def test_celsius_variants(answer):
    assert verdict(answer, ["°C"], ["%"]) == "correct"
    assert verdict(answer, ["%"], ["°C"]) == "wrong_alt"


# ----------------------------------------------------------------- 多词 gold 的片段
def test_semicolon_segments_of_a_gold_can_match():
    gold = "No change; retain the bell-ringing sound effect."
    assert matches("No change", [gold]) and matches("no change.", [gold])
    assert not matches("Change it", [gold])


def test_answer_kind():
    assert answer_kind("2 October") == "date_or_month" and answer_kind("h8") == "coordinate"
    assert answer_kind("About 10") == "numeric" and answer_kind("Zoom out") == "other"


def test_tokens_basic():
    assert tokens("Lungs!") == ["lung"] and tokens("Twenty-four bibs") == ["24", "bib"]


# ----------------------------------------------------------------- 含糊/两可的答案不能自动判对
@pytest.mark.parametrize("answer", ["°F or °C (depending on regional convention)", "Either % or °C", "Maybe °C"])
def test_hedged_answers_are_undecided(answer):
    assert verdict(answer, ["°C"], ["%"]) == "undecided"


def test_gold_that_itself_contains_or_is_not_a_hedge():
    assert verdict("horizontally or vertically", ["horizontally or vertically"], ["diagonally"]) == "correct"
    assert verdict("Horizontally or vertically.", ["horizontally or vertically"], ["diagonally"]) == "correct"
