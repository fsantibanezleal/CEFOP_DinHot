"""Real CLI/source refusals added to the exported content guard; no numerical execution."""
import json
import subprocess
import sys
from pathlib import Path

from test_manuscript_depth import depth, product, has, SCRIPT, report_tex, paper_tex, SDD, PAPER_COV, prose, sec, eqs


def test_prescribed_class_and_section_based_paper_are_enforced(tmp_path):
    root = product(tmp_path, report=report_tex().replace('{article}', '{book}'))
    assert has(depth.check(root), 'unsupported document class')
    root = product(tmp_path / 'paper', paper=paper_tex().replace('\\begin{document}', '\\begin{document}\n\\chapter{Wrong structure}'))
    assert has(depth.check(root), 'research paper uses sections')


def test_literal_latex_source_examples_do_not_become_chapter_structure(tmp_path):
    source = paper_tex().replace('\\end{document}', '\\begin{verbatim}\n\\chapter{Literal example}\n\\end{verbatim}\n\\verb|\\chapter{Quoted}|\n\\end{document}')
    assert not has(depth.check(product(tmp_path, paper=source)), 'research paper uses sections')


def test_unknown_or_escaping_requested_manuscript_cannot_pass_an_empty_scope(tmp_path):
    root = product(tmp_path)
    for slug in ('missing', '../technical-report', 'shared'):
        assert has(depth.check(root, only=slug), 'requested manuscript folder'), slug


def test_wrong_typed_coverage_is_a_finding_not_a_traceback(tmp_path):
    root = product(tmp_path)
    path = root / 'manuscripts/technical-report/coverage.json'
    original = json.loads(path.read_text(encoding='utf8'))
    for group, value in [('methods', []), ('contracts', True), ('claims', {'BS-1': None}), ('title_support', [3])]:
        path.write_text(json.dumps({**original, group: value}), encoding='utf8')
        assert has(depth.check(root), group), group


def test_missing_cyclic_and_escaping_tex_inputs_fail_before_counting(tmp_path):
    root = product(tmp_path)
    main = root / 'manuscripts/technical-report/main.tex'
    original = main.read_text(encoding='utf8')
    outside = tmp_path / 'outside.tex'
    outside.write_text('Outside scope content must not be read.', encoding='utf8')
    for include, reason in [('absent.tex', 'Missing LaTeX'), ('main.tex', 'cyclic LaTeX'), (str(outside), 'escapes manuscripts/')]:
        main.write_text(original + f'\n\\input{{{include}}}\n', encoding='utf8')
        assert has(depth.check(root), reason), (include, depth.check(root))


def test_no_argument_cli_checks_its_repository_and_is_read_only():
    root = Path(__file__).resolve().parents[2]
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
    before = {name: (root / name).read_bytes() for name in tracked if name and (root / name).is_file()}
    result = subprocess.run([sys.executable, str(SCRIPT)], cwd=root, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'check_manuscript_depth: OK' in result.stdout
    assert all((root / name).read_bytes() == raw for name, raw in before.items())


def test_missing_hidden_and_duplicate_authorities_cannot_shrink_coverage(tmp_path):
    root = product(tmp_path)
    sdd = root / 'docs/design/SDD.md'
    original = sdd.read_text(encoding='utf8')
    sdd.unlink()
    assert has(depth.check(root), 'cannot read inventory')
    sdd.write_text('<!--\n' + original + '\n-->', encoding='utf8')
    assert has(depth.check(root), 'nonempty inventory')
    sdd.write_text(original.replace('| M-1 | classical | Forward Euler | x | y |', '| M-1 | classical | Forward Euler | x | y |\n| M-1 | classical | Duplicate | x | y |'), encoding='utf8')
    assert has(depth.check(root), 'duplicate inventory ID')
    sdd.write_text(original, encoding='utf8')
    (root / 'docs/contracts/catalog.md').unlink()
    assert has(depth.check(root), 'cannot read inventory')


def test_fenced_fake_claims_do_not_become_real_but_novel_contributions_require_papers(tmp_path):
    sdd = SDD + '\n```md\n## Novel contributions\n- NC-99: quoted example\n```\n'
    assert depth.check(product(tmp_path / 'quoted', sdd=sdd)) == []
    sdd = SDD + '\n## Novel contributions\n- NC-1: a reusable benchmark design.\n'
    root = product(tmp_path / 'novel', sdd=sdd)
    assert has(depth.check(root), 'NC-1', 'has no manuscript')
    coverage = {**PAPER_COV, 'claims': {**PAPER_COV['claims'], 'NC-1': 'sec:benchmark'}}
    (root / 'manuscripts/step-policy/coverage.json').write_text(json.dumps(coverage), encoding='utf8')
    main = root / 'manuscripts/step-policy/main.tex'
    source = main.read_text(encoding='utf8').replace('\\end{document}', sec('Benchmark construction', prose(1600) + eqs(6, 'benchmark'), 'sec:benchmark') + '\n\\end{document}')
    main.write_text(source, encoding='utf8')
    assert depth.check(root) == []


def test_quoted_tex_inputs_and_structure_are_not_active_source(tmp_path):
    source = paper_tex().replace('\\end{document}', '\\begin{verbatim}\n\\input{missing-example}\n\\section{Quoted not a section}\n\\end{verbatim}\n\\verb|\\input{also-missing}|\n\\end{document}')
    root = product(tmp_path, paper=source)
    assert depth.check(root) == []
    document = depth.load(root / 'manuscripts/step-policy')
    assert all('Quoted' not in section.title for section in document.sections)


def longtable_report():
    return report_tex().replace(r"\begin{table}\begin{tabular}{ll}a & b\end{tabular}",
                                r"\begin{longtable}{ll}a & b\\").replace(r"\end{table}", r"\end{longtable}").replace(
                                    r"\section{Discussion}", prose(200) + r"\section{Discussion}")


def test_captioned_longtables_count_without_relaxing_the_table_floor(tmp_path):
    root = product(tmp_path, report=longtable_report())
    doc = depth.load(root / "manuscripts/technical-report")
    assert depth.measures(doc)["tables"] == 8
    assert depth.float_labels(doc.body)["tab:r0"] == "longtable"
    assert depth.check(root) == []


def test_adversarial_longtables_keep_caption_and_text_reference_requirements(tmp_path):
    source = longtable_report().replace("As \\ref{tab:r3} shows,", "Then").replace(
        f"\\caption{{{prose(20)}}}\\label{{tab:r2}}", "\\caption{Errors.}\\label{tab:r2}")
    findings = depth.check(product(tmp_path, report=source))
    assert has(findings, "longtable tab:r3 is never referenced")
    assert has(findings, "longtable tab:r2: caption of 1 words")
