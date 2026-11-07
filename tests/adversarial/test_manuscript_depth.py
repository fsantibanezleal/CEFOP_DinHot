"""The manuscript content bar (check_manuscript_depth.py; conventions/manuscript-content-bar.md). Each test builds a throwaway
product whose technical report and manuscript meet the bar, breaks one requirement, and runs the real check; the intact
product is the control."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[2] / "scripts"
SCRIPT = HERE / "check_manuscript_depth.py"
sys.path.insert(0, str(HERE))
import check_manuscript_depth as depth  # noqa: E402

VOCAB = ("the integrator advances the compartment model over each step while the controller bounds the local error "
         "against the reference solution computed with a tighter tolerance on the same epidemic cases and the measured "
         "peak fraction attack rate and timing are compared across solvers on every case").split()
REPORT_TITLE = "Adaptive Runge-Kutta integration halves the peak error of compartment epidemic models"
PAPER_TITLE = "An error-controlled step policy for compartment epidemic models"


def prose(n: int) -> str:
    out = [VOCAB[i % len(VOCAB)] for i in range(n)]
    return " ".join(" ".join(out[i:i + 18]) + "." for i in range(0, n, 18))


def eqs(n: int, tag: str) -> str:
    return "\n".join(f"\\begin{{equation}}\\label{{eq:{tag}{i}}} x_{{{i}}} = \\beta S I / N\\end{{equation}}" for i in range(n))


def floats(kind: str, n: int, tag: str) -> str:
    env = "figure" if kind == "fig" else "table"
    body = "\\includegraphics{a.pdf}" if env == "figure" else "\\begin{tabular}{ll}a & b\\end{tabular}"
    out = []
    for i in range(n):
        out.append(f"As \\ref{{{kind}:{tag}{i}}} shows, {prose(30)}\n\\begin{{{env}}}{body}"
                   f"\\caption{{{prose(20)}}}\\label{{{kind}:{tag}{i}}}\\end{{{env}}}")
    return "\n".join(out)


HEADER = "\n".join(f"\\newcommand{{\\{m}}}{{x}}" for m in depth.HEADER_MACROS)


def tex(title: str, sections: list[str], refs: int) -> str:
    items = "\n".join(f"\\bibitem{{r{i}}} A. Author{i}, A paper on solvers, 20{i % 25:02d}." for i in range(refs))
    return (f"\\documentclass{{article}}\n{HEADER}\n\\title{{{title}}}\n\\begin{{document}}\n\\maketitle\n"
            + "\n".join(sections)
            + f"\n\\begin{{thebibliography}}{{99}}\n{items}\n\\end{{thebibliography}}\n\\end{{document}}\n")


def sec(title: str, text: str, label: str = "") -> str:
    return f"\\section{{{title}}}" + (f"\\label{{{label}}}" if label else "") + "\n" + text


def report_tex(title: str = REPORT_TITLE) -> str:
    cites = "\\cite{" + ",".join(f"r{i}" for i in range(30)) + "}"
    algos = "\n".join(f"\\begin{{algorithm}}\\caption{{{prose(20)}}}\\label{{alg:a{i}}}\\end{{algorithm}} See \\ref{{alg:a{i}}}."
                      for i in range(3))
    return tex(title, [
        sec("Introduction", f"{prose(1700)} {cites}"),
        sec("Problem formulation", prose(900) + eqs(21, "p")),
        sec("Notation", prose(400)),
        sec("Data and data contracts", prose(400)
            + "".join(f"\\subsection{{The {c} document}}\\label{{sec:data-{c}}}\n{prose(200)}" for c in ("trace", "case-index"))),
        sec("System architecture", prose(900)),
        sec("Methods", prose(300)
            + "".join(f"\\subsection{{Solver {i}}}\\label{{sec:m{i}}}\n{prose(700)}{eqs(2, f'm{i}')}" for i in (1, 2))
            + algos),
        sec("Experimental protocol", prose(900)),
        sec("Results", prose(500) + floats("fig", 10, "r") + floats("tab", 8, "r")),
        sec("Validation", prose(800)),
        sec("Discussion", prose(1500)),
        sec("Limitations", prose(500)),
        sec("Reproducibility", prose(300)),
        sec("Conclusions", prose(400)),
    ], 30)


def paper_tex(title: str = PAPER_TITLE, *, ablation: bool = True, uncertainty: bool = True) -> str:
    cites = "\\cite{" + ",".join(f"r{i}" for i in range(25)) + "}"
    results = prose(600) + floats("fig", 6, "p") + floats("tab", 4, "p") + (" The error is $0.12 \\pm 0.01$." if uncertainty else "")
    return tex(title, [
        sec("Introduction", f"{prose(800)} {cites}"),
        sec("Related work", prose(800)),
        sec("Problem formulation", prose(500) + eqs(4, "f")),
        sec("Proposed method", prose(1600) + eqs(6, "pm") + "\\begin{algorithm}\\caption{" + prose(20)
            + "}\\label{alg:p}\\end{algorithm} See \\ref{alg:p}.", "sec:proposed"),
        sec("Theoretical analysis", prose(500) + eqs(2, "t")),
        sec("Experimental design", prose(700)),
        sec("Results", results),
        sec("Ablation study" if ablation else "Sensitivity", prose(400)),
        sec("Discussion", prose(500)),
        sec("Limitations", prose(400)),
        sec("Reproducibility", prose(200)),
        sec("Conclusions", prose(200)),
    ], 25)


SDD = ("# SDD\n\n## Method ladder\n\n| id | tier | method | acceptance criterion | gate |\n|---|---|---|---|---|\n"
       "| M-1 | classical | Forward Euler | x | y |\n| M-2 | sota | RK45 | x | y |\n\n"
       "## Beyond the state of the art\n\n- BS-1: an error-controlled step policy.\n\n## Next\n")
CATALOG = ("# Catalog\n\n| id | version | owner |\n|---|---|---|\n| trace | 1.0.0 | a |\n| case-index | 2.0.0 | b |\n\n"
           "## History\n\n| id | version |\n|---|---|\n| other | 1.0.0 |\n")
REPORT_COV = {"kind": "technical-report", "title_support": ["tab:r0", "fig:r1"],
              "methods": {"M-1": "sec:m1", "M-2": "sec:m2"},
              "contracts": {"trace": "sec:data-trace", "case-index": "sec:data-case-index"}}
PAPER_COV = {"kind": "manuscript", "title_support": ["tab:p0"], "claims": {"BS-1": "sec:proposed"}}


def product(tmp: Path, *, report: str | None = None, paper: str | None = None, report_cov: dict | None = None,
            paper_cov: dict | None = None, titles: tuple[str, str] = (REPORT_TITLE, PAPER_TITLE), sdd: str = SDD,
            extra: dict[str, str] | None = None) -> Path:
    (tmp / "docs" / "design").mkdir(parents=True)
    (tmp / "docs" / "contracts").mkdir(parents=True)
    (tmp / "docs" / "design" / "SDD.md").write_text(sdd, encoding="utf-8")
    (tmp / "docs" / "contracts" / "catalog.md").write_text(CATALOG, encoding="utf-8")
    (tmp / "product.json").write_text(json.dumps({"manuscripts": [
        {"kind": "technical-report", "title": titles[0]}, {"kind": "manuscript", "title": titles[1]}]}), encoding="utf-8")
    for slug, source, cov in (("technical-report", report if report is not None else report_tex(), report_cov or REPORT_COV),
                              ("step-policy", paper if paper is not None else paper_tex(), paper_cov or PAPER_COV)):
        d = tmp / "manuscripts" / slug
        d.mkdir(parents=True)
        (d / "main.tex").write_text(source, encoding="utf-8")
        (d / "coverage.json").write_text(json.dumps(cov), encoding="utf-8")
    for name, text in (extra or {}).items():
        (tmp / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp / name).write_text(text, encoding="utf-8")
    return tmp


def has(findings: list[str], *needles: str) -> bool:
    return any(all(n in f for n in needles) for f in findings)


def test_a_product_at_the_bar_passes(tmp_path):
    findings = depth.check(product(tmp_path))
    assert findings == [], findings
    r = subprocess.run([sys.executable, str(SCRIPT), str(tmp_path)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


def test_adversarial_a_manuscript_not_in_latex_fails(tmp_path):
    root = product(tmp_path, extra={"manuscripts/notes/report.md": "# Report\n\nShort.\n"})
    assert has(depth.check(root), "manuscripts/notes", "no LaTeX", ".md")


def test_adversarial_a_short_report_fails_its_floors(tmp_path):
    thin = tex(REPORT_TITLE, [sec("Introduction", prose(400)), sec("Methods", prose(400))], 6)
    f = depth.check(product(tmp_path, report=thin))
    for needle in ("words, the technical-report floor", "equations, the technical-report floor",
                   "figures, the technical-report floor", "references, the technical-report floor",
                   "no section for Data and data contracts", "no section for Results"):
        assert has(f, needle), needle


def test_adversarial_a_section_too_short_to_inform_fails(tmp_path):
    source = report_tex().replace(sec("Discussion", prose(1500)), sec("Discussion", prose(120)))
    assert has(depth.check(product(tmp_path, report=source)), "section 'Discussion' has", "floor is 350")


def test_adversarial_a_method_or_contract_left_out_of_the_report_fails(tmp_path):
    cov = {**REPORT_COV, "methods": {"M-1": "sec:m1"}, "contracts": {"trace": "sec:data-trace"}}
    f = depth.check(product(tmp_path, report_cov=cov))
    assert has(f, "methods does not map M-2") and has(f, "contracts does not map case-index")


def test_adversarial_a_method_covered_in_a_thin_section_fails(tmp_path):
    source = report_tex().replace(f"\\label{{sec:m2}}\n{prose(700)}{depth_eqs('m2')}", f"\\label{{sec:m2}}\n{prose(200)}")
    assert has(depth.check(product(tmp_path, report=source)), "covers M-2", "floor is 600 words and 2 equations")


def depth_eqs(tag: str) -> str:
    return eqs(2, tag)


def test_adversarial_a_proposed_method_without_a_manuscript_fails(tmp_path):
    sdd = SDD.replace("- BS-1: an error-controlled step policy.", "- BS-1: a step policy.\n- BS-2: a learned error model.")
    assert has(depth.check(product(tmp_path, sdd=sdd)), "proposed method BS-2", "has no manuscript")


def test_adversarial_a_title_not_kept_with_the_results_fails(tmp_path):
    f = depth.check(product(tmp_path, titles=("An older title the results no longer sustain", PAPER_TITLE)))
    assert has(f, "manuscripts/technical-report", "is not the title of any product.json manuscripts entry")
    cov = {**PAPER_COV, "title_support": []}
    assert has(depth.check(product(tmp_path / "s", paper_cov=cov)), "title_support is empty")
    cov = {**PAPER_COV, "title_support": ["sec:proposed"]}
    assert has(depth.check(product(tmp_path / "l", paper_cov=cov)), "not the label of a figure or a table")


def test_adversarial_floats_not_read_in_the_text_fail(tmp_path):
    source = report_tex().replace("As \\ref{fig:r3} shows,", "Then").replace(
        f"\\caption{{{prose(20)}}}\\label{{tab:r2}}", "\\caption{Errors.}\\label{tab:r2}")
    f = depth.check(product(tmp_path, report=source))
    assert has(f, "figure fig:r3 is never referenced") and has(f, "table tab:r2: caption of 1 words")


def test_adversarial_a_manuscript_without_ablation_or_uncertainty_fails(tmp_path):
    f = depth.check(product(tmp_path, paper=paper_tex(ablation=False, uncertainty=False)))
    assert has(f, "no section for Ablation") and has(f, "no uncertainty is reported")


def test_adversarial_internal_ids_and_vague_wording_fail(tmp_path):
    source = report_tex().replace(sec("Limitations", prose(500)), sec("Limitations", prose(500) + " M-2 drifts, etc."))
    f = depth.check(product(tmp_path, report=source))
    assert has(f, "internal id M-2") and has(f, "vague wording 'etc.'")


def test_adversarial_a_missing_coverage_file_or_header_fails(tmp_path):
    root = product(tmp_path, report=report_tex().replace(HEADER, ""))
    (root / "manuscripts" / "step-policy" / "coverage.json").unlink()
    f = depth.check(root)
    assert has(f, "header block lacks") and has(f, "step-policy: coverage.json is missing")


def test_inputs_are_read_and_support_folders_skipped(tmp_path):
    full = report_tex()
    head, rest = full.split("\\section{Introduction}", 1)
    root = product(tmp_path, report=head + "\\input{body}\n\\end{document}\n",
                   extra={"manuscripts/shared/macros.tex": "\\newcommand{\\x}{y}\n"})
    body = "\\section{Introduction}" + rest.rsplit("\\end{document}", 1)[0]
    (root / "manuscripts" / "technical-report" / "body.tex").write_text(body, encoding="utf-8")
    assert depth.check(root) == []


@pytest.mark.parametrize("only", ["technical-report", "step-policy"])
def test_only_checks_one_folder(tmp_path, only):
    sdd = SDD.replace("- BS-1: an error-controlled step policy.", "- BS-1: a.\n- BS-2: b.")
    assert depth.check(product(tmp_path, sdd=sdd), only=only) == []


def test_the_publishers_gate_a_product_manuscript_and_only_one(tmp_path):
    root = product(tmp_path, report=report_tex().replace(sec("Discussion", prose(1500)), sec("Discussion", prose(50))))
    assert has(depth.bar_for_source(root / "manuscripts" / "technical-report" / "main.tex"), "section 'Discussion'")
    assert depth.bar_for_source(root / "manuscripts" / "step-policy") == []
    other = tmp_path / "elsewhere" / "manuscripts" / "paper"
    other.mkdir(parents=True)
    assert depth.bar_for_source(other) is None


def test_adversarial_ladder_ids_without_a_hyphen_are_still_checked(tmp_path):
    """A ladder named M1, B-lin (not M-1) is read: a report that leaves one out fails, never passes unchecked."""
    sdd = SDD.replace("| M-1 |", "| M1 |").replace("| M-2 |", "| B-lin |")
    f = depth.check(product(tmp_path, sdd=sdd, report_cov={**REPORT_COV, "methods": {"M1": "sec:m1"}}))
    assert has(f, "methods does not map B-lin"), f
    assert depth.sdd_ids(product(tmp_path / "b", sdd=sdd))[0] == ["M1", "B-lin"]


def test_ladder_coverage_stops_at_the_end_of_its_table(tmp_path):
    sdd = SDD + "\n| Classification | Method |\n|---|---|\n| Classical | Bond |\n| Statistical | Sobol |\n"
    assert depth.sdd_ids(product(tmp_path, sdd=sdd))[0] == ["M-1", "M-2"]
