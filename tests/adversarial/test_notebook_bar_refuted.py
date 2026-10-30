"""Planted defects for the floors of the notebook bar (template 0.12.000): the failures Felipe saw on 2026-10-26 and the findings of the gate
review, rebuilt as synthetic notebooks, each of which must fail the gate. They build their own notebooks, so they need nothing of the
template's example; the plants on a copy of the example set are in tests/template/adversarial/test_notebooks_refuted.py."""
from __future__ import annotations

from pathlib import Path

import pytest
from notebook_bar_helpers import bar_notebook, floors_of, unit_module


@pytest.fixture
def pipe(tmp_path: Path) -> Path:
    return unit_module().bar_repo(tmp_path)


def test_adversarial_a_notebook_that_only_reads_derived_json_and_prints_it_fails_the_method_and_figure_floors(pipe: Path) -> None:
    """OreFlow's level 2 notebook: load a baked file, print its keys, print a table of one block, plot nothing."""
    steps = [("Load the baked case.", "# read the baked case\nimport json\n\ncase = json.loads(Path('data/derived/case.json').read_text())\nprint(case.keys())", "dict_keys(['a'])\n"),
             ("Print its schema.", "# the schema\nprint(case['schema'])", "x/v1\n"),
             ("Print a table of the nominal block.", "# the nominal block\nfor key, value in case['nominal'].items():\n    print(key, value)", "a 1\n"),
             ("Print the engine version.", "# the version\nprint(case['engine'])", "0.1\n"),
             ("Print the top-level keys.", "# the keys\nprint(sorted(case))", "['a']\n"),
             ("Print the table again.", "# the table\nprint(case['nominal'])", "{}\n")]
    findings = floors_of(pipe, bar_notebook("en", 2, "a", steps))
    assert any("method cells 0" in f for f in findings), findings
    assert any("figures 0" in f for f in findings), findings


def test_adversarial_prose_pasted_from_a_neighbour_fails_the_repetition_floor(pipe: Path) -> None:
    pasted = " ".join(f"The question here is what artifact number {n} represents and where its evidence stops being valid." for n in range(5))
    steps = [("Run it.", "# run the engine\nr = run(1)\nprint(r)", "1.5\n")] * 5
    one, other = bar_notebook("en", 2, "a", steps, figure=True, answer="1.5 here"), bar_notebook("en", 2, "b", steps, figure=True, answer="1.5 there")
    for doc in (one, other):
        doc["cells"][1]["source"] += " " + pasted
    findings = floors_of(pipe, one, others=(other,))
    assert len([f for f in findings if "are shared with another notebook of the tree" in f]) == 2, findings


def test_adversarial_chained_one_liners_fail_the_statement_floor(pipe: Path) -> None:
    """Geophysics' diagnostics: ``rows=cal["rows"]; truth=...; cover=...`` in one cell."""
    chained = "# diagnostics\nrows = run(1); truth = run(2); cover = run(3); gap = rows - truth\nprint(rows, truth, cover, gap)"
    findings = floors_of(pipe, bar_notebook("en", 2, "a", [("Diagnostics.", chained, "1.5 3.0 4.5 -1.5\n")] * 5, figure=True, answer="gap -1.5"))
    assert any("holds 4 statements" in f for f in findings), findings


def test_adversarial_verifying_the_engine_in_three_cells_fails_the_reproduction_floor(pipe: Path) -> None:
    """The template's example of the previous release spent a quarter of its code cells checking the engine against itself."""
    check = "# the engine against itself\nimport numpy as np\n\nprint(np.allclose(run(2), run(2)))"
    steps = [("Run it.", "# run the engine\nr = run(1)\nprint(r)", "1.5\n")] * 4 + [("Check.", check, "True\n")] * 3
    findings = floors_of(pipe, bar_notebook("en", 2, "a", steps, figure=True, answer="1.5 here"))
    assert any("reproduction checks 3" in f for f in findings), findings


def test_adversarial_a_helper_and_numpy_do_not_inflate_the_method_cells(pipe: Path) -> None:
    """A wrapper the notebook defines around the engine, and any amount of numpy, earn no method cell."""
    wrapper = "# a helper around the engine\ndef wrapper(x):\n    return run(x)\n\n\nprint(wrapper(1))"
    steps = [("Define.", wrapper, "1.5\n")] + [("Call the helper.", f"# call the helper\nv{n} = wrapper({n})\nprint(v{n})", "1.5\n") for n in range(6)]
    steps += [("Numpy.", f"# numpy work\nz{n} = np.linspace(0, 1, {n + 3})\nprint(z{n}.sum())", "1.0\n") for n in range(6)]
    findings = floors_of(pipe, bar_notebook("en", 2, "a", steps, figure=True, answer="1.5 here"))
    assert any("method cells 0" in f or "method cells 1" in f for f in findings), findings


def test_adversarial_a_level_three_notebook_that_only_cites_the_state_of_the_art_fails(pipe: Path) -> None:
    u = unit_module()
    doc = u.bar_doc("en", 3, sota_method=False, sota_figure=False)
    findings = floors_of(pipe, doc)
    assert any("no method cell under State of the art" in f for f in findings) and any("no figure under State of the art" in f for f in findings)


def test_adversarial_the_spanish_tree_does_not_escape_a_floor_the_english_tree_meets(pipe: Path) -> None:
    u = unit_module()
    for knob, needle in (({"methods": 4}, "method cells 4"), ({"figures": 1}, "figures 1"), ({"prose": 200}, "explanatory prose words"),
                         ({"after": 30}, "followed by 30 words"), ({"question": False}, "**Pregunta:**"), ({"answer": False}, "**Respuesta:**"),
                         ({"setups": 3}, "setup and input/output cells 3"),
                         ({"answer_text": "El total fue de 99,9 en la corrida."}, "quotes no number")):
        findings = floors_of(pipe, u.bar_doc("es", 2, **knob), "es")
        assert any(needle in f for f in findings), (knob, findings)
    es = u.bar_doc("es", 2)
    es["cells"][1]["source"] += "\n\nInterprete el metodo con sus unidades y su contrato."
    assert any("generic filler sentence" in f for f in floors_of(pipe, es, "es"))


def test_adversarial_a_level_four_notebook_without_a_figure_or_a_table_under_beyond_fails(pipe: Path) -> None:
    findings = floors_of(pipe, unit_module().bar_doc("en", 4, beyond="none"))
    assert any("no figure or table under Beyond the state of the art" in f for f in findings), findings


def test_adversarial_a_notebook_with_no_valid_level_is_measured_at_level_two(pipe: Path) -> None:
    findings = floors_of(pipe, unit_module().bar_doc("en", 1, metadata_level=9))
    assert any("method cells 3" in f and "level 2 (no valid level declared)" in f for f in findings), findings


def test_adversarial_review_b1_readers_loaders_versions_and_dunders_earn_no_method_cell(tmp_path: Path) -> None:
    unit_module().test_b1_readers_loaders_versions_and_dunder_chains_are_no_method_cells(tmp_path)


def test_adversarial_review_b2_import_names_never_come_from_the_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    unit_module().test_b2_import_names_are_static_and_never_read_from_the_environment(tmp_path, monkeypatch)


def test_adversarial_review_b3_an_object_api_is_a_lesson(tmp_path: Path) -> None:
    unit_module().test_b3_an_object_built_from_a_method_class_and_its_calls_are_method_cells(tmp_path)


def test_adversarial_review_b4_the_answer_is_not_a_version_a_year_or_a_rounding_miss(tmp_path: Path) -> None:
    u = unit_module()
    for n, (answer, shown) in enumerate((("The tools of release 2.4 are used.", "42.5"), ("Saved in 2026 as planned.", "saved on 2026-10-27"),
                                         ("The value is 0.43 here.", "0.4213"), ("12,346 cases in all.", "12345"))):
        u.test_b4_a_version_a_year_or_a_number_that_rounds_elsewhere_is_not_the_answer(tmp_path / f"no{n}", answer, shown)
    for n, (answer, shown) in enumerate((("The value is 0.42 here.", "0.4213"), ("About 42 % of cases.", "0.42"), ("12.345 cases in all.", "12345"))):
        u.test_b4_the_answer_is_matched_at_the_precision_a_reader_writes_it(tmp_path / f"yes{n}", answer, shown)
    u.test_b4_what_a_setup_cell_prints_is_not_a_computed_number(tmp_path / "setup")


def test_adversarial_review_m1_padding_and_repetition_are_not_prose(tmp_path: Path) -> None:
    u = unit_module()
    u.test_m1_hidden_repeated_and_tabular_text_is_no_prose()
    u.test_m1_one_sentence_repeated_is_counted_once_and_is_a_finding(tmp_path)


def test_adversarial_review_m2_read_and_print_cells_are_input_output_cells(tmp_path: Path) -> None:
    unit_module().test_m2_cells_that_only_read_and_print_are_input_output_cells(tmp_path)


def test_adversarial_review_m3_the_forms_of_reproduction_check_are_counted_and_validation_is_not(tmp_path: Path) -> None:
    u = unit_module()
    u.test_m3_the_forms_of_reproduction_check_the_review_found_are_counted(tmp_path / "a")
    u.test_m3_input_validation_and_a_selector_are_no_reproduction_checks(tmp_path / "b")


def test_adversarial_review_m4_a_question_is_not_shared_inside_a_tree(tmp_path: Path) -> None:
    unit_module().test_m4_two_notebooks_of_a_tree_do_not_share_a_question(tmp_path)


def test_adversarial_review_m5_the_reference_implementation_alone_does_not_fill_level_three(tmp_path: Path) -> None:
    unit_module().test_m5_at_level_three_the_reference_implementation_alone_does_not_fill_the_floor(tmp_path)


def test_adversarial_review_m7_the_src_skeleton_of_the_pipeline_counts(tmp_path: Path) -> None:
    unit_module().test_m7_the_modules_of_the_templates_src_skeleton_are_method_modules(tmp_path)


def test_adversarial_review_nb1_a_lookup_is_no_method_and_the_product_declares_its_entry_points(tmp_path: Path) -> None:
    u = unit_module()
    u.test_nb1_a_lookup_of_the_registry_is_no_method_cell_and_the_product_decides(tmp_path / "a")
    u.test_nb1_a_product_must_declare_its_method_entrypoints(tmp_path / "b")


def test_adversarial_review_nb2_an_object_built_by_a_chain_a_factory_or_a_table_is_a_lesson(tmp_path: Path) -> None:
    unit_module().test_nb2_a_chained_constructor_a_factory_and_a_table_of_objects_bind_their_objects(tmp_path)


def test_adversarial_review_nb3_short_repeated_sentences_do_not_pad_the_prose(tmp_path: Path) -> None:
    unit_module().test_nb3_short_sentences_and_paragraphs_repeated_are_counted_once(tmp_path)


def test_adversarial_review_nb4_residuals_against_measurements_are_not_reproduction_checks(tmp_path: Path) -> None:
    unit_module().test_nb4_only_declared_artifacts_are_committed_results_whatever_the_call_form(tmp_path)


def test_adversarial_review_minors_n1_n3_n4_n5(tmp_path: Path) -> None:
    u = unit_module()
    u.test_n1_an_unconsumed_generator_and_utility_packages_earn_no_method_cell(tmp_path / "a")
    u.test_n3_the_answer_is_matched_by_magnitude_and_a_bare_exponent_is_no_answer()
    u.test_n4_a_head_and_a_display_of_what_was_read_are_input_output_cells(tmp_path / "c")
    u.test_n5_an_input_check_and_a_selector_with_a_reduction_are_no_reproduction_checks(tmp_path / "d")


def test_adversarial_review_r21_short_repeated_sentences_do_not_pad_the_prose(tmp_path: Path) -> None:
    unit_module().test_r21_a_short_sentence_repeated_is_counted_once_and_more_than_twice_is_a_finding(tmp_path)


def test_adversarial_review_r22_the_result_of_a_function_and_container_methods_are_no_method(tmp_path: Path) -> None:
    unit_module().test_r22_the_return_value_of_a_function_and_a_container_method_earn_no_method_cell(tmp_path)


def test_adversarial_review_r1_to_r4_aliases_re_exports_and_empty_comprehensions(tmp_path: Path) -> None:
    u = unit_module()
    u.test_r1_an_alias_made_by_assignment_is_followed_and_a_rebound_name_loses_its_alias(tmp_path / "a")
    u.test_r2_a_re_export_is_resolved_statically_from_the_package_or_from_the_map(tmp_path / "b")
    u.test_r3_a_comprehension_over_an_empty_literal_never_runs(tmp_path / "c")


def test_adversarial_review_m31_a_repeated_heading_label_or_pointer_is_no_padding(tmp_path: Path) -> None:
    unit_module().test_m31_a_heading_a_label_and_a_short_pointer_may_come_back(tmp_path)


def test_adversarial_review_m32_a_declared_factory_builds_a_method_object(tmp_path: Path) -> None:
    unit_module().test_m32_a_declared_factory_builds_a_method_object(tmp_path)


def test_adversarial_review_m33_a_method_of_an_attribute_of_the_object_does_not_count(tmp_path: Path) -> None:
    unit_module().test_m33_a_method_of_an_attribute_of_the_object_is_not_a_method_of_the_object(tmp_path)
