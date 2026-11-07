"""Real admission witnesses from the independent manuscript-base review."""
import pytest

from test_manuscript_depth import (
    depth, product, has, SDD, REPORT_COV, PAPER_COV, PAPER_TITLE,
    REPORT_TITLE, report_tex, paper_tex,
)


def test_novel_contribution_ids_remain_internal_in_visible_prose(tmp_path):
    source = report_tex().replace('\\end{document}', '\nNC-1 is an internal inventory identifier.\n\\end{document}')
    findings = depth.check(product(tmp_path, report=source))
    assert has(findings, 'internal id NC-1 appears in the text'), findings


@pytest.mark.parametrize('indent', ['', '  '])
def test_authoritative_inline_method_ids_cannot_disappear_from_required_coverage(tmp_path, indent):
    sdd = SDD.replace('| M-1 |', '| `M-1` |').replace('| M-2 |', '| `M-2` |')
    sdd = '\n'.join(indent + line if line.startswith('|') else line for line in sdd.splitlines())
    root = product(tmp_path, sdd=sdd, report_cov={**REPORT_COV, 'methods': {}})
    findings = depth.check(root)
    assert has(findings, 'methods does not map M-1'), findings
    assert has(findings, 'methods does not map M-2'), findings


@pytest.mark.parametrize('second', ['sec:m1', 'sec:alias'])
def test_distinct_method_ids_cannot_reuse_one_coverage_region(tmp_path, second):
    source = report_tex().replace('\\label{sec:m1}', '\\label{sec:m1}\\label{sec:alias}')
    cov = {**REPORT_COV, 'methods': {'M-1': 'sec:m1', 'M-2': second}}
    findings = depth.check(product(tmp_path, report=source, report_cov=cov))
    assert has(findings, 'methods M-1 and M-2', 'overlapping coverage regions'), findings


def test_a_parent_region_cannot_double_count_its_child_method(tmp_path):
    source = report_tex().replace('\\section{Methods}', '\\section{Methods}\\label{sec:parent}')
    cov = {**REPORT_COV, 'methods': {'M-1': 'sec:parent', 'M-2': 'sec:m2'}}
    assert has(depth.check(product(tmp_path, report=source, report_cov=cov)), 'overlapping coverage regions')


def test_related_proposals_each_need_their_own_substantial_region(tmp_path):
    sdd = SDD.replace('- BS-1: an error-controlled step policy.', '- BS-1: an error-controlled step policy.\n- BS-2: another policy.')
    cov = {**PAPER_COV, 'claims': {'BS-1': 'sec:proposed', 'BS-2': 'sec:proposed'}}
    assert has(depth.check(product(tmp_path, sdd=sdd, paper_cov=cov)), 'claims BS-1 and BS-2', 'overlapping coverage regions')


@pytest.mark.parametrize('conditional', ['\\iffalse', '\\iftrue', '\\ifnum0=1'])
def test_active_conditional_content_cannot_claim_static_depth(tmp_path, conditional):
    def hide(source):
        return source.replace('\\begin{document}', '\\begin{document}\n' + conditional).replace('\\end{document}', '\\fi\n\\end{document}')
    findings = depth.check(product(tmp_path, report=hide(report_tex()), paper=hide(paper_tex())))
    assert has(findings, 'manuscripts/technical-report', 'conditional', 'unmeasurable'), findings
    assert has(findings, 'manuscripts/step-policy', 'conditional', 'unmeasurable'), findings


def test_literal_conditional_code_is_not_executed_or_counted(tmp_path):
    literal = '\\begin{verbatim}\n\\iffalse\n\\section{Not active}\n\\fi\n\\end{verbatim}\n\\verb|\\iffalse|'
    source = paper_tex().replace('\\end{document}', literal + '\n\\end{document}')
    assert depth.check(product(tmp_path, paper=source)) == []


@pytest.mark.parametrize('actual,declared', [('999', '1'), ('-1', '1'), ('0.1', '01'), ('CO', 'Co'), (r'\$1', '1'), (r'1\%', '1'), ('$x=-1$', '$x=1$')])
def test_value_bearing_title_identity_is_not_alphabetic_words_only(tmp_path, actual, declared):
    source = paper_tex(title=PAPER_TITLE + ' ' + actual)
    findings = depth.check(product(tmp_path, paper=source, titles=(REPORT_TITLE, PAPER_TITLE + ' ' + declared)))
    assert has(findings, 'is not the title of any product.json manuscripts entry'), findings


def test_presentation_only_title_wrapping_keeps_the_same_identity(tmp_path):
    assert depth.check(product(tmp_path, paper=paper_tex(title='\\textbf{' + PAPER_TITLE + '}'))) == []


def test_a_valid_custom_title_macro_cannot_be_erased_as_a_known_wrapper_prefix(tmp_path):
    source = paper_tex(title=PAPER_TITLE + r' \textbfExtra{999}')
    source = source.replace('\\begin{document}', '\\newcommand{\\textbfExtra}[1]{0}\n\\begin{document}')
    findings = depth.check(product(tmp_path, paper=source, titles=(REPORT_TITLE, PAPER_TITLE + ' Extra999')))
    assert has(findings, 'is not the title of any product.json manuscripts entry'), findings


def test_nested_inputs_use_the_main_compile_working_directory(tmp_path):
    root = product(tmp_path)
    folder = root / 'manuscripts/technical-report'
    main = folder / 'main.tex'
    source = main.read_text(encoding='utf8')
    start, end = source.index('\\section{Introduction}'), source.index('\\section{Problem formulation}')
    intro = source[start:end]
    (folder / 'parts').mkdir()
    (folder / 'intro.tex').write_text(intro, encoding='utf8')
    (folder / 'parts/outer.tex').write_text('\\input{intro}', encoding='utf8')
    (folder / 'parts/intro.tex').write_text('This is not the file TeX reads from the main working directory.', encoding='utf8')
    main.write_text(source[:start] + '\\input{parts/outer}\n' + source[end:], encoding='utf8')
    assert depth.check(root) == []
    assert intro.strip() in depth.load(folder).body


def test_a_root_support_tex_file_does_not_mask_the_allowed_tex_subfolder_main(tmp_path):
    root = product(tmp_path)
    folder = root / 'manuscripts/technical-report'
    (folder / 'tex').mkdir()
    (folder / 'tex/main.tex').write_bytes((folder / 'main.tex').read_bytes())
    (folder / 'main.tex').unlink()
    (folder / 'base.tex').write_text('% Preamble support, not the document main.\n', encoding='utf8')
    assert depth.check(root) == []
