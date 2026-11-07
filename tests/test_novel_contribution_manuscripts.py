"""A reusable evaluation study must not masquerade as a forecasting proposal."""
from test_check_manuscripts import REPORT, PAPER, SDD, tree, run


def test_novel_protocol_and_dataset_have_their_own_coverage(tmp_path):
    sdd = SDD + "\n## Novel contributions\n\nNC-1: a replay protocol.\nNC-2: a dataset.\n"
    study = {**PAPER, "covers": ["NC-1", "NC-2"]}
    result = run(tree(tmp_path, [REPORT, study], sdd=sdd))
    assert result.returncode == 0, result.stdout


def test_adversarial_novel_id_from_an_unrelated_section_is_not_a_declaration(tmp_path):
    sdd = SDD + "\n## Other notes\n\nNC-1 is discussed but not declared here.\n"
    result = run(tree(tmp_path, [REPORT, {**PAPER, "covers": ["NC-1"]}], sdd=sdd))
    assert result.returncode == 1 and "Novel contributions" in result.stdout


def test_adversarial_unknown_novel_id_is_refused(tmp_path):
    result = run(tree(tmp_path, [REPORT, {**PAPER, "covers": ["NC-9"]}]))
    assert result.returncode == 1 and "NC-9" in result.stdout


def test_adversarial_fenced_novel_id_is_not_a_declaration(tmp_path):
    sdd = SDD + "\n## Novel contributions\n\n```text\nNC-1: example only.\n```\n"
    result = run(tree(tmp_path, [REPORT, {**PAPER, "covers": ["NC-1"]}], sdd=sdd))
    assert result.returncode == 1 and "NC-1" in result.stdout


def test_adversarial_method_id_in_novel_section_does_not_authorize_a_method(tmp_path):
    sdd = SDD + "\n## Novel contributions\n\nBS-9: deliberately misplaced.\n"
    result = run(tree(tmp_path, [REPORT, {**PAPER, "covers": ["BS-9"]}], sdd=sdd))
    assert result.returncode == 1 and "BS-9" in result.stdout
