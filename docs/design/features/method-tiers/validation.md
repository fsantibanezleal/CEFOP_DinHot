# Adversarial validation: the method tiers and the manuscripts

For each requirement of [`requirements.md`](requirements.md), the check that tries to break it: what was planted or
refuted, and the test that plants it, in a throwaway tree with the real guard run as a subprocess (the unplanted tree is the
control and passes). `scripts/check_sdd.py` fails when a requirement has no row here (or two), when a check is empty, and
when a gate names a test that does not exist.

| requirement | adversarial check | gate |
|---|---|---|
| MT-001 | a ladder with the old three columns, one that is prose, one with the tier `learned`, one with an empty method or a repeated id, and one inside a code fence are planted: each fails and the first names the column to add | `tests/test_method_tiers.py::test_adversarial_a_ladder_without_the_tier_column_fails_saying_how_to_add_it` |
| MT-002 | the ladder of a product that passes loses its classical, its sota and its beyond row in turn: each fails naming the tier and the rule file | `tests/test_method_tiers.py::test_adversarial_a_product_without_a_method_in_a_tier_fails_naming_the_tier_and_the_rule` |
| MT-003 | a product that says `None claimed.` (alone, and next to a claim), has no beyond section, lists no BS identifier, keeps a claim with no beyond row or a beyond row with no claim is planted: each fails | `tests/test_method_tiers.py::test_adversarial_a_product_that_says_none_claimed_fails` |
| MT-004 | the template tree (with `.template-source`) is planted with `None claimed.`, no beyond row and no sota row, and the real template is checked: both pass; without the marker the same files fail | `tests/test_method_tiers.py::test_adversarial_the_template_keeps_none_claimed_and_no_beyond_row` |
| MT-005 | a repository whose ladder has two sota methods is planted with one named, none named, an unknown id, a classical id, methods on a level 2 notebook, a string, and the two languages disagreeing: each fails; all named passes | `tests/test_method_tiers_notebooks.py::test_adversarial_a_sota_method_no_level_3_notebook_names_is_found_in_each_language` |
| MT-006 | a product.json without the field, with an empty list and with only a manuscript is planted: each fails with the rule file; the same files with `.template-source` pass | `tests/test_check_manuscripts.py::test_adversarial_a_product_without_the_field_fails_with_the_rule` |
| MT-007 | thirteen malformed entries (kind, concept DOI in four wrong forms, title, version, covers) and a claim the SDD does not list are planted: each fails naming `manuscripts[0]` and the field | `tests/test_check_manuscripts.py::test_adversarial_a_malformed_entry_fails_naming_the_field` |
| MT-008 | a report at 0.14.000 with VERSION 0.13.000 is planted (ahead), and a report at 0.12.000 run with and without `--release`: only the release run fails | `tests/test_check_manuscripts.py::test_adversarial_a_report_version_behind_the_release_passes_unless_the_release_changes_a_result` |
| MT-009 | the default run is planted on a valid tree and a stand-in for Zenodo answers a missing record, another concept DOI and an older version: the default run reads nothing and each stand-in answer is a finding | `tests/test_check_manuscripts.py::test_adversarial_the_default_run_never_touches_the_network` |
