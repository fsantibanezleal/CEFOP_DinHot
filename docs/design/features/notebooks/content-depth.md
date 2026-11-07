# Current notebook content depth

This supplements the historical structural guard and its measured anatomy bar.
The binding source is CAOS `conventions/notebook-content-bar.md`, effective
2026-11-02. Both checks run statically in CI. Executing notebooks and independently
reading the lessons and figures remain separate local release gates.

## Requirements

| id | requirement | gate |
|---|---|---|
| ND-001 | THE portable depth check SHALL require at least1000 explanatory words and2 distinct image outputs at level1, and1500 words and3 distinct image outputs at levels2 to4, using the existing structural reader's hidden/repeated/tabular-text and repeated-image defenses. | `tests/adversarial/test_check_notebook_depth.py::test_adversarial_depth_floors_and_duplicate_images` |
| ND-002 | THE check SHALL require at least1 displayed equation and3 distinct reference sources at level1, and2 equations and4 sources at levels2 to4; code fences, comments, repeated equations and repeated DOI/URL spellings SHALL earn no additional credit. | `tests/adversarial/test_check_notebook_depth.py::test_adversarial_equations_and_sources_are_distinct_visible_content` |
| ND-003 | EACH level2 to4 lesson SHALL have third-level sensitivity/limits and own-data headings in its own language, and no lesson title/question SHALL describe a generic validation run or artifact viewer. | `tests/adversarial/test_check_notebook_depth.py::test_adversarial_sensitivity_own_data_and_generic_questions` |
| ND-004 | `notebooks/coverage.json` SHALL map every SDD ladder method, catalog contract, pipeline stage and method package to existing notebook paths in both languages; method mappings SHALL reach level2 or higher in each language. | `tests/adversarial/test_check_notebook_depth.py::test_adversarial_complete_tool_coverage` |
| ND-005 | The coverage map's mappings SHALL be nonempty lists of unique relative topic/notebook `.ipynb` paths contained by each language tree; malformed roots, empty values, escaping paths and links resolving outside a tree SHALL fail with a finding instead of a traceback. | `tests/adversarial/test_check_notebook_depth.py::test_adversarial_malformed_and_escaping_coverage_fails_closed` |
| ND-006 | INVENTORY readers SHALL fail on missing/malformed source documents or unreadable inventories rather than interpreting errors as an empty product; stages SHALL be the real stage modules plus any explicit `product.json` `pipeline_stage_sources` map to existing Python source files. An empty stage inventory SHALL fail. | `tests/adversarial/test_check_notebook_depth.py::test_adversarial_inventory_admission` |
| ND-007 | THE CLI SHALL emit a nonzero status on any finding, work without network or third-party dependencies, and optionally report notebook measures; CI SHALL run it without executing notebooks. | `tests/adversarial/test_check_notebook_depth.py::test_cli_and_ci_are_static` |
| ND-008 | THE example curriculum SHALL independently teach the whole actual example product at these floors in both languages; a passing structural count SHALL not replace content, mathematical, figure or fresh-execution review. | `tests/adversarial/test_check_notebook_depth.py::test_committed_curriculum_meets_current_depth` and independent lesson review |

## Design

`scripts/check_notebook_depth.py` loads the colocated structural reader by its exact
file path. It reuses that reader for prose and figure accounting rather than
introducing a weaker duplicate prose counter. The structural `scripts/notebook_bar.json` carries the raised prose and figure
floors; the supplementary `scripts/notebook_depth.json` carries equation and
source floors. Each threshold has one policy source. Both are mandatory. Markdown display equations and distinct
reference identities are measured only in visible prose. Source provenance and
correctness are independently reviewed, not inferred from URL counts.

The coverage file is an index, not the source of its own required IDs. Required
inventories come from the SDD ladder table, contract catalog, actual stage source
files and the product's package declarations. An explicitly declared stage source
allows repositories with differently named pipeline modules to expose their real
responsibilities; paths must identify actual in-repository Python files. The check
cannot prove that a mapped lesson teaches a boundary well. That remains a required
independent whole-tool review.

## Dependency order and status

First plant the portable CLI failures, then implement the policy/reader and its
adversaries, then deepen and freshly execute the example set, then independently
review the exact candidate and CI. Product adoption follows a released base.
This worktree is isolated from the concurrently owned showcase-template work.
No new template release, CI acceptance or example-content acceptance is claimed.
