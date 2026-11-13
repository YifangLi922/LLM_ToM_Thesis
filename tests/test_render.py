from __future__ import annotations

import pytest

from render_pairs import (
    BELIEF_TOKEN, CLAIM_TOKEN, RenderError, check_backbone, check_minimal_pairs, render_variants,
)
from schemas import Variants

BB = ("Ann reads the manual. It says that {{CLAIM_SPAN}}.{{BELIEF_INSERTION}} "
      "Later she plans a new task for the afternoon.")
CA, CC = "cats have four legs", "cats have six legs"
BA, BC = "Ann believes that cats have four legs.", "Ann believes that cats have six legs."


def _render(bb=BB):
    return render_variants(bb, CA, CC, BA, BC)


def codes(issues, severity="error"):
    return {i.code for i in issues if i.severity == severity}


# ----------------------------------------------------------------- 确定性渲染
def test_exact_output_of_four_conditions():
    v = _render()
    assert v.implicit_aligned == "Ann reads the manual. It says that cats have four legs. Later she plans a new task for the afternoon."
    assert v.implicit_conflicting == "Ann reads the manual. It says that cats have six legs. Later she plans a new task for the afternoon."
    assert v.explicit_aligned == ("Ann reads the manual. It says that cats have four legs. Ann believes that cats have four legs. "
                                  "Later she plans a new task for the afternoon.")
    assert v.explicit_conflicting == ("Ann reads the manual. It says that cats have six legs. Ann believes that cats have six legs. "
                                      "Later she plans a new task for the afternoon.")


def test_rendering_is_deterministic():
    assert _render() == _render()


def test_clean_render_passes_pair_check():
    assert not codes(check_minimal_pairs(_render(), CA, CC, BA, BC))


def test_extra_spaces_around_insertion_are_normalized():
    bb = "Ann reads. It says that {{CLAIM_SPAN}}.  {{BELIEF_INSERTION}}   Then she acts."
    v = render_variants(bb, CA, CC, BA, BC)
    assert "  " not in v.implicit_aligned and "  " not in v.explicit_aligned
    assert not codes(check_minimal_pairs(v, CA, CC, BA, BC))


def test_insertion_at_end_of_story():
    bb = "Ann reads. It says that {{CLAIM_SPAN}}.{{BELIEF_INSERTION}}"
    v = render_variants(bb, CA, CC, BA, BC)
    assert v.implicit_aligned.endswith("four legs.")
    assert v.explicit_aligned.endswith(BA)
    assert not codes(check_minimal_pairs(v, CA, CC, BA, BC))


def test_paragraph_break_after_insertion_preserved():
    bb = "It says that {{CLAIM_SPAN}}.{{BELIEF_INSERTION}}\n\nNext paragraph."
    v = render_variants(bb, CA, CC, BA, BC)
    assert v.implicit_aligned == "It says that cats have four legs.\n\nNext paragraph."
    assert v.explicit_aligned == f"It says that cats have four legs. {BA}\n\nNext paragraph."


def test_belief_sentence_may_restate_claim_without_breaking_checks():
    # belief 句复述 claim 是常态（见 guideline 示例）
    assert BA.count(CA) == 1
    assert not codes(check_minimal_pairs(_render(), CA, CC, BA, BC))


# ----------------------------------------------------------------- 占位符错误：必须明确拒绝
@pytest.mark.parametrize("bad, expected", [
    ("Ann reads. {{BELIEF_INSERTION}}", "placeholder_claim_count"),
    ("Ann reads that {{CLAIM_SPAN}}.", "placeholder_belief_count"),
    ("{{CLAIM_SPAN}}. {{CLAIM_SPAN}}.{{BELIEF_INSERTION}}", "placeholder_claim_count"),
    ("Ann reads that {{CLAIM_SPAN}}.{{BELIEF_INSERTION}} Then {{BELIEF_INSERTION}}", "placeholder_belief_count"),
    ("Ann {{BELIEF_INSERTION}} reads that {{CLAIM_SPAN}}.", "placeholder_order"),
    ("Ann reads that {{CLAIM_SPAN}}.{{BELIEF_INSERTION}} {{SECRET}} Then.", "placeholder_unknown"),
])
def test_bad_backbones_rejected(bad, expected):
    assert expected in codes(check_backbone(bad))
    with pytest.raises(RenderError):
        _render(bad)


# ----------------------------------------------------------------- 插入点：整句 claim / 补句号 / 错误位置
FULL_BB = "Maya reads the penguin entry: {{CLAIM_SPAN}}{{BELIEF_INSERTION}} Later, a colleague asks for a badge."


def test_full_sentence_claim_spans_are_valid():
    """真实出现过的写法：claim span 自带句号，骨架里 {{CLAIM_SPAN}} 后直接跟 {{BELIEF_INSERTION}}。"""
    ca, cc = "Penguins are birds.", "Penguins are fish."
    ba, bc = "Maya believes that penguins are birds.", "Maya believes that penguins are fish."
    v = render_variants(FULL_BB, ca, cc, ba, bc)
    assert v.implicit_conflicting == "Maya reads the penguin entry: Penguins are fish. Later, a colleague asks for a badge."
    assert v.explicit_conflicting == f"Maya reads the penguin entry: Penguins are fish. {bc} Later, a colleague asks for a badge."
    assert not codes(check_minimal_pairs(v, ca, cc, ba, bc))


@pytest.mark.parametrize("bb, ca, cc", [
    (FULL_BB, "Penguins are birds", "Penguins are fish"),                       # 没有句末标点就插入 belief
    ("It says that {{CLAIM_SPAN}}.{{BELIEF_INSERTION}} Then.", "cats are small.", "cats are big."),   # 重复句号
    ("It says that {{CLAIM_SPAN}}. Extra sentence here.{{BELIEF_INSERTION}} Then.", "cats are small", "cats are big"),  # 夹了另一句话
    ("It says that {{CLAIM_SPAN}} and goes on{{BELIEF_INSERTION}} Then.", "cats are small", "cats are big"),
])
def test_belief_must_follow_a_finished_source_sentence(bb, ca, cc):
    with pytest.raises(RenderError, match="belief_not_after_sentence"):
        render_variants(bb, ca, cc, BA, BC)


def test_placeholder_inside_content_rejected():
    with pytest.raises(RenderError):
        render_variants(BB, "cats {{CLAIM_SPAN}}", CC, BA, BC)


# ----------------------------------------------------------------- 检测"不允许的改写"
def _tamper(field, old, new):
    d = _render().as_dict()
    assert old in d[field]
    d[field] = d[field].replace(old, new)
    return Variants(**d)


@pytest.mark.parametrize("field, old, new, expected", [
    # 公共文字被偷偷改写（其中一个版本）
    ("implicit_conflicting", "Later she plans", "Afterwards she plans", "implicit_pair_differs"),
    ("explicit_conflicting", "the afternoon", "the morning", "explicit_vs_implicit_conflicting"),
    ("explicit_aligned", "Later she", "Later, she", "explicit_vs_implicit_aligned"),
    # explicit 额外改了别处：既与 implicit 不一致，也与另一个 explicit 不一致
    ("explicit_conflicting", "reads the manual", "studies the manual", "explicit_pair_differs"),
])
def test_unauthorized_rewrites_detected(field, old, new, expected):
    issues = check_minimal_pairs(_tamper(field, old, new), CA, CC, BA, BC)
    assert expected in codes(issues)


def test_belief_sentence_leaking_into_implicit_detected():
    d = _render().as_dict()
    d["implicit_conflicting"] = d["explicit_conflicting"]
    assert "belief_in_implicit" in codes(check_minimal_pairs(Variants(**d), CA, CC, BA, BC))


def test_belief_sentence_in_wrong_place_detected():
    d = _render().as_dict()
    d["explicit_aligned"] = d["implicit_aligned"] + " " + BA          # 放到了故事末尾
    assert "belief_not_after_source_sentence" in codes(check_minimal_pairs(Variants(**d), CA, CC, BA, BC))


def test_belief_after_quoted_source_sentence_is_fine():
    bb = 'The sign says, "{{CLAIM_SPAN}}."{{BELIEF_INSERTION}} Then Ann plans something new.'
    v = render_variants(bb, CA, CC, BA, BC)
    assert v.explicit_aligned.startswith(f'The sign says, "{CA}." {BA} Then')
    assert not codes(check_minimal_pairs(v, CA, CC, BA, BC))


def test_two_belief_sentences_detected():
    d = _render().as_dict()
    d["explicit_aligned"] = d["explicit_aligned"].replace(BA, BA + " " + BA)
    assert "belief_sentence_count" in codes(check_minimal_pairs(Variants(**d), CA, CC, BA, BC))


def test_identical_claim_spans_rejected():
    v = render_variants(BB, CA, CA, BA, BC)
    assert "claim_spans_identical" in codes(check_minimal_pairs(v, CA, CA, BA, BC))


def test_identical_belief_sentences_rejected():
    v = render_variants(BB, CA, CC, BA, BA)
    assert "belief_sentences_identical" in codes(check_minimal_pairs(v, CA, CC, BA, BA))


def test_multi_sentence_belief_is_only_a_warning():
    ba2 = "Ann believes that cats have four legs. She is sure."
    v = render_variants(BB, CA, CC, ba2, BC)
    issues = check_minimal_pairs(v, CA, CC, ba2, BC)
    assert not codes(issues) and "belief_sentence_multi" in codes(issues, "warning")


def test_tokens_are_the_documented_literals():
    assert CLAIM_TOKEN == "{{CLAIM_SPAN}}" and BELIEF_TOKEN == "{{BELIEF_INSERTION}}"
