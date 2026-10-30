"""The three method tiers in the SDD gate (CAOS_MANAGE ``conventions/method-tiers-and-manuscripts.md``, template 0.13.000). Each
test builds a throwaway tree and runs the real script on it: a product SDD needs a method in each tier (classical, sota, beyond) and
at least one ``BS-<n>`` claim; the template, recognised by ``.template-source``, keeps its teaching example. The notebook side is in
tests/test_method_tiers_notebooks.py and the checks on the template's own example in tests/template/test_method_tiers_example.py."""
from __future__ import annotations

from pathlib import Path

import pytest
from test_spec_guards import BEYOND, GOOD_VALIDATION, LADDER, put, run, sdd_text, sdd_tree

RULE = "method-tiers-and-manuscripts.md"
OLD_LADDER = "| method | acceptance criterion | gate |\n|---|---|---|\n| the model | it works | `tests/test_x.py::test_a` |\n"


def check(tmp_path: Path, *, template: bool = False, **kw):
    tree = sdd_tree(tmp_path, validation=GOOD_VALIDATION, sdd=sdd_text(**kw))
    if template:
        put(tree, ".template-source", "")
    return run("check_sdd.py", str(tree))


def without_row(ladder: str, tier: str) -> str:
    return "".join(ln for ln in ladder.splitlines(keepends=True) if f"| {tier} |" not in ln)


# ---------------------------------------------------------------- check_sdd: a product

def test_a_product_with_the_three_tiers_and_a_claim_passes(tmp_path):
    r = check(tmp_path)
    assert r.returncode == 0, r.stdout


@pytest.mark.parametrize("tier", ["classical", "sota", "beyond"])
def test_adversarial_a_product_without_a_method_in_a_tier_fails_naming_the_tier_and_the_rule(tmp_path, tier):
    r = check(tmp_path, ladder=without_row(LADDER, tier))
    assert r.returncode == 1 and f"no {tier} method" in r.stdout and RULE in r.stdout, r.stdout


def test_adversarial_a_product_that_says_none_claimed_fails(tmp_path):
    r = check(tmp_path, beyond="None claimed. This product is a teaching model.\n", ladder=without_row(LADDER, "beyond"))
    assert r.returncode == 1 and "None claimed" in r.stdout and RULE in r.stdout, r.stdout


def test_none_claimed_next_to_a_claim_fails(tmp_path):
    r = check(tmp_path, beyond="None claimed.\n\n" + BEYOND)
    assert r.returncode == 1 and "None claimed" in r.stdout, r.stdout


def test_a_product_with_no_claim_in_the_beyond_section_fails(tmp_path):
    r = check(tmp_path, beyond="A validation protocol and a calibration plan.\n", ladder=without_row(LADDER, "beyond"))
    assert r.returncode == 1 and "BS-<n>" in r.stdout and RULE in r.stdout, r.stdout


def test_a_product_without_the_beyond_section_fails(tmp_path):
    r = check(tmp_path, beyond=None)
    assert r.returncode == 1 and "Beyond the state of the art" in r.stdout and RULE in r.stdout, r.stdout


def test_adversarial_a_ladder_without_the_tier_column_fails_saying_how_to_add_it(tmp_path):
    r = check(tmp_path, ladder=OLD_LADDER)
    assert r.returncode == 1 and "tier" in r.stdout and "classical, sota, beyond" in r.stdout and RULE in r.stdout, r.stdout


def test_a_ladder_that_is_prose_fails_like_a_missing_column(tmp_path):
    r = check(tmp_path, ladder="One method, the engine.\n")
    assert r.returncode == 1 and "tier" in r.stdout, r.stdout


def test_adversarial_a_tier_that_is_not_one_of_the_three_fails(tmp_path):
    r = check(tmp_path, ladder=LADDER.replace("| sota |", "| learned |"))
    assert r.returncode == 1 and "learned" in r.stdout and "classical, sota, beyond" in r.stdout, r.stdout


def test_a_ladder_row_with_an_empty_method_or_a_repeated_id_fails(tmp_path):
    r = check(tmp_path, ladder=LADDER.replace("the current solver", "TBD"))
    assert r.returncode == 1 and "M-2" in r.stdout, r.stdout
    r = check(tmp_path / "b", ladder=LADDER.replace("| M-2 |", "| M-1 |"))
    assert r.returncode == 1 and "M-1" in r.stdout and "twice" in r.stdout, r.stdout


def test_adversarial_a_beyond_row_must_be_a_claim_of_the_section_and_a_claim_needs_its_row(tmp_path):
    r = check(tmp_path, ladder=LADDER.replace("| BS-1 |", "| BS-7 |"))
    assert r.returncode == 1 and "BS-7" in r.stdout and "BS-1" in r.stdout, r.stdout


def test_a_ladder_inside_a_code_fence_does_not_count(tmp_path):
    fenced = "```\n" + LADDER + "```\n"
    r = check(tmp_path, ladder=fenced)
    assert r.returncode == 1 and "tier" in r.stdout, r.stdout


def test_adversarial_a_claim_with_only_a_validation_protocol_still_needs_a_beyond_method_row(tmp_path):
    # the claim exists in the section, but no ladder row of tier beyond carries it: a protocol is not a method
    r = check(tmp_path, ladder=without_row(LADDER, "beyond"))
    assert r.returncode == 1 and "BS-1" in r.stdout and "no beyond method" in r.stdout, r.stdout


# ---------------------------------------------------------------- check_sdd: the template

def test_adversarial_the_template_keeps_none_claimed_and_no_beyond_row(tmp_path):
    r = check(tmp_path, template=True, beyond="None claimed. The example is a teaching model.\n", ladder=without_row(LADDER, "beyond"))
    assert r.returncode == 0, r.stdout


def test_the_template_still_needs_the_ladder_table_with_its_tier_column(tmp_path):
    r = check(tmp_path, template=True, beyond="None claimed.\n", ladder=OLD_LADDER)
    assert r.returncode == 1 and "tier" in r.stdout, r.stdout


def test_the_template_does_not_need_all_three_tiers(tmp_path):
    r = check(tmp_path, template=True, ladder=without_row(without_row(LADDER, "sota"), "beyond"), beyond="None claimed.\n")
    assert r.returncode == 0, r.stdout
