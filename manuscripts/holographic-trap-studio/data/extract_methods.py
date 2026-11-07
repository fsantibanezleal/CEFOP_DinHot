#!/usr/bin/env python3
"""Second extraction of the DinHot technical report: the parameters, the contracts, the bake by method and the guards.

Run from the repository root after ``acceptance.py``, ``params.py`` and ``extract.py`` (standard library only):

    python manuscripts/holographic-trap-studio/data/extract_methods.py

It reads only committed files and writes, next to this script, ``methods_numbers.tex`` (macros) and the table files below.

  * ``params.json`` (``params.py``: the keyword defaults of every ``run`` function): ``\\defv{gaa}{alpha}`` and ``table_defaults.tex``.
  * ``acceptance.json`` (``acceptance.py``): ``\\acc{gs}``, the measured acceptance text of each method, and ``table_nfix.tex``.
  * ``docs/contracts/catalog.md`` and the schema files: ``table_contracts.tex``, ``table_contract_<id>.tex`` (the top-level fields of
    each contract with their type, unit and range), ``appendix_fields.tex`` (the nested fields) and ``\\cver{<id>}``.
  * ``data-pipeline/pipeline/cases/measured_ranges.json`` (three seeds per case, the canonical bake): ``table_bake_sigma.tex``,
    ``table_bake_eff.tex``, ``table_seeds.tex`` and the counts of the macros ``bake*``.
  * ``tests/``: the number of test functions per folder, ``\\nTests{<folder>}``.
  * ``data/derived/benchmark/results.json``: ``table_pareto.tex`` (the stored fronts) and the ranks behind ``bench*`` macros.
  * ``docs/design/SDD.md``: the notation table is typed here (symbol, meaning, unit), the one table of definitions.
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import beyond_rows  # noqa: E402
from method_names import ID, NAME, RUN, named, slug  # noqa: E402

ROOT = HERE.parents[2]
DERIVED = ROOT / "data" / "derived"
CONTRACTS = ROOT / "docs" / "contracts"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def esc(s: str) -> str:
    return (str(s).replace("\\", "\\textbackslash{}").replace("_", "\\_").replace("&", "\\&").replace("%", "\\%")
            .replace("#", "\\#").replace("$", "\\$").replace("{", "\\{").replace("}", "\\}"))


def fmt(x: float, d: int = 3) -> str:
    return f"{x:.{d}f}"


def sig(x: float) -> str:
    """A spread in percent: two significant digits, a bound below the resolution of the files."""
    if x < 1e-3:
        return "$<$0.001"
    return f"{x:.0f}" if x >= 100 else f"{x:.2g}"


def csname_macro(name: str, value: str) -> str:
    return f"\\expandafter\\newcommand\\csname {name}\\endcsname{{{value}}}\n"


def defval(v) -> str:
    if v is None:
        return "unset"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, list):
        return (f"{v[0]} to {v[-1]}" if all(isinstance(x, int) for x in v) and v == list(range(v[0], v[-1] + 1))
                else ", ".join(defval(x) for x in v))
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


# ------------------------------------------------------------------------------------------------------ notation table

NOTATION = [
    (r"$\lambda$", "vacuum wavelength of the laser", "nm"),
    (r"$f$", "focal length of the lens in the pupil of which the SLM sits", "mm"),
    (r"$\mathrm{NA}$", "numerical aperture of the objective", "1"),
    (r"$n_{\mathrm{imm}}$", "refractive index of the immersion medium", "1"),
    (r"$n_{\mathrm{pix}}$", "SLM pixels per side", "1"),
    (r"$N_{\mathrm{pix}}$", r"number of SLM pixels, $n_{\mathrm{pix}}^2$", "1"),
    (r"$p$", "SLM pixel pitch", r"$\mu$m"),
    (r"$\mathrm{pad}$", "zero-padding factor of the focal grid", "1"),
    (r"$n_{\mathrm{fft}}$", r"focal grid size, $\mathrm{pad}\,n_{\mathrm{pix}}$", "1"),
    (r"$j$", "index of an SLM pixel, at position $(x_j,y_j)$ from the optical axis", "m"),
    (r"$m,\ M$", "index and number of traps", "1"),
    (r"$(x_m,y_m,z_m)$", "position of trap $m$ in the focal volume", r"$\mu$m"),
    (r"$l_m$", "vortex (topological) charge of trap $m$", "1"),
    (r"$w_m,\ a_m$", r"target weight of trap $m$ and its target amplitude $\sqrt{w_m}$", "1"),
    (r"$A_j$", r"input beam amplitude, normalised so that $\sum_jA_j^2=N_{\mathrm{pix}}$", "1"),
    (r"$\phi_j$", "phase displayed at pixel $j$", "rad"),
    (r"$\Delta_j^m$", "phase delay from pixel $j$ to trap $m$ (Eq.~\\eqref{eq:delay})", "rad"),
    (r"$V_m,\ I_m$", r"complex field at trap $m$ and its intensity $|V_m|^2$ (fraction of the input power)", "1"),
    (r"$e$", "efficiency, the sum of the trap intensities", "1"),
    (r"$u$", r"uniformity, $1-(\max I-\min I)/(\max I+\min I)$", "1"),
    (r"$\sigma$", "relative standard deviation of the trap intensities", "percent"),
    (r"$\eta$", "root-mean-square fractional error of a shaped potential in its measure region", "1"),
    (r"$\Delta x,\ X_{1/2}$", "width of one focal bin and half of the unaliased field", r"$\mu$m"),
    (r"$K,\ \sigma_K,\ q$", "crosstalk kernel of the device and its fitted width and exponent", "1"),
    (r"$Z_j,\ c_j$", "Zernike mode $j$ (Noll order) and its coefficient", "waves"),
    (r"$N$ (or $n_{\mathrm{fix}}$)", "iteration after which the focal phase is frozen", "1"),
    (r"$\alpha$", "exponent of the assignment cost of the Hungarian rearrangement or weight of the generalized adaptive additive GS", "1"),
    (r"$m$ (mixing)", "mixing parameter of the mixed-region rule", "1"),
    (r"$G,\ \rho_m$", "feedback gain and measured intensity relative to its target", "1"),
    (r"$\lambda_{\mathrm{EU}}$", "trade-off parameter of the efficiency-uniformity Pareto front", "1"),
    (r"$\mathrm{AC}$", "accuracy of a volume hologram, mean over planes of the overlap of unit-sum intensities", "1"),
    (r"$z_{R,\mathrm{SLM}}$", r"SLM-limited Rayleigh range of the volume network (Eq.~\eqref{eq:m17-zr}), the depth unit of its planes", "mm"),
    (r"$\kappa,\ \gamma,\ f_c$", "trap stiffness, drag coefficient and corner frequency of a bead", r"pN/$\mu$m, kg/s, Hz"),
    (r"$U,\ \hat U,\ \omega_r,\ \omega_z$", "dipole potential, trap depth of an atom and its radial and axial trap angular frequencies", "J, J, rad/s, rad/s"),
    (r"$w_{\mathrm b}$", r"waist of the input Gaussian beam at the SLM, $w_{\mathrm{frac}}\,n_{\mathrm{pix}}\,p/2$ (not the trap weight $w_m$)", r"$\mu$m"),
    (r"$w_0,\ z_R$", r"waist and Rayleigh range $\pi w_0^2/\lambda$ of the focus of an atom trap (Eq.~\eqref{eq:atom})", r"$\mu$m"),
    (r"$\omega_0,\ \Gamma,\ \Delta$", r"resonance angular frequency, natural linewidth and detuning of the atomic transition (Eq.~\eqref{eq:atom}); the detuning $\Delta$ carries no indices, unlike the delay $\Delta_j^m$", "rad/s"),
    (r"$c,\ \epsilon_0$", "speed of light and vacuum permittivity", "m/s, F/m"),
    (r"$n_m,\ n_p,\ r$", r"index of the medium, index and radius of a bead; $m=n_p/n_m$ in the polarizability is an index ratio and not the trap index", r"1, 1, $\mu$m"),
    (r"$\alpha$ (polarizability)", r"polarizability of the bead of Eq.~\eqref{eq:bead}, the third meaning of $\alpha$", r"F\,m$^2$"),
    (r"$D,\ P(f)$", r"diffusion coefficient $k_BT/\gamma$ and power spectral density of the bead position at frequency $f$", r"m$^2$/s, m$^2$/Hz"),
    (r"$H,\ \boldsymbol\xi,\ \lambda_m$", r"angular-spectrum transfer function, spatial frequency and wavelength in the medium, $\lambda/n_{\mathrm{imm}}$ (Eq.~\eqref{eq:angspec})", r"1, 1/$\mu$m, nm"),
    (r"$T_m,\ t$", r"target intensity of trap $m$ in the cost of the optimizers, and the power of that cost (Eq.~\eqref{eq:m10})", "1"),
    (r"$L,\ \epsilon$", "loss of an optimizer (a quadratic intensity loss unless stated) and a small positive constant that keeps a logarithm or a quotient finite", "1"),
    (r"$g_i,\ B_i,\ \psi$", r"weights, focal amplitude relative to its target and focal phase of the phase-fixed iteration $i$ (Eq.~\eqref{eq:m07})", "1, 1, rad"),
    (r"$\theta_m,\ h(\tau)$", r"phase given to trap $m$ (random in the random superposition, learned in the learned warm start, locked in the flicker-bounded sequence) and the minimal-jerk profile of $\tau=s/S$ (Eq.~\eqref{eq:b2-traj})", "rad, 1"),
]


def table_notation() -> str:
    out = ["\\begin{table}[t]\\centering\\footnotesize\n",
           "\\caption{Notation: the symbols used in more than one section of the report, with their meaning and unit; a symbol that "
           "belongs to one derivation only (the sigma points of one method, the statistics of one test) is defined where it appears. "
           "A unit of 1 marks a dimensionless quantity or a count, and the intensities are fractions of the input power.}\\label{tab:notation}\n",
           "\\begin{tabular}{@{}>{\\raggedright\\arraybackslash}p{0.2\\textwidth} >{\\raggedright\\arraybackslash}p{0.56\\textwidth} "
           ">{\\raggedright\\arraybackslash}p{0.16\\textwidth}@{}}\\toprule Symbol & Meaning & Unit\\\\\\midrule\n"]
    for s, m, u in NOTATION:
        out.append(f"{s} & {m} & {u}\\\\\n")
    out.append("\\bottomrule\\end{tabular}\\end{table}\n")
    return "".join(out)


# ------------------------------------------------------------------------------------------------------ defaults

def table_defaults(params: dict) -> str:
    """The keyword defaults in two blocks side by side, so that the table fits one page."""
    rows: list[tuple[str, str, str]] = []
    for mid, m in params.items():
        if not m["params"]:
            rows.append((RUN[mid], "(none)", ""))
            continue
        for k, (name, v) in enumerate(m["params"].items()):
            rows.append((esc(RUN[mid]) if k == 0 else "", f"\\texttt{{{esc(name)}}}", esc(defval(v))))
    half = (len(rows) + 1) // 2
    left, right = rows[:half], rows[half:]
    out = ["\\begin{table}[t]\\centering\\scriptsize\\setlength{\\tabcolsep}{4pt}\n",
           "\\caption{Keyword defaults of every method, read from the signature of its \\texttt{run} function by "
           "\\texttt{params.py}, in two blocks; a default of \\texttt{unset} is chosen at run time from the target, as the method "
           "section states, and methods with no keyword take only the interface arguments.}\\label{tab:defaults}\n",
           "\\begin{tabular}{@{}>{\\raggedright\\arraybackslash}p{0.17\\textwidth} l l @{\\hskip 1.2em} >{\\raggedright\\arraybackslash}p{0.17\\textwidth} l l@{}}\\toprule Method & Keyword & Default & Method & Keyword & Default\\\\\\midrule\n"]
    for i in range(half):
        l = left[i]
        r = right[i] if i < len(right) else ("", "", "")
        out.append(f"{l[0]} & {l[1]} & {l[2]} & {r[0]} & {r[1]} & {r[2]}\\\\\n")
    out.append("\\bottomrule\\end{tabular}\\end{table}\n")
    return "".join(out)


def table_nfix(acc: dict) -> str:
    sweep = acc[ID["pfwgs"]]["numbers"]["n_fix_sweep_min_rel_std_150"]
    out = ["\\begin{table}[t]\\centering\\footnotesize\n",
           "\\caption{Phase-fixed weighted GS on the crowded $50\\times30$ array: the minimum relative standard deviation reached "
           "in 150 iterations against the freeze index $N$ (one seed, Fourier form), measured by \\texttt{acceptance.py}. "
           "The source value does not transfer to this grid.}\\label{tab:nfix}\n",
           "\\begin{tabular}{@{}r r@{}}\\toprule $N$ & minimum $\\sigma$ (percent)\\\\\\midrule\n"]
    for n, v in sweep.items():
        out.append(f"{n} & {v:.3f}\\\\\n")
    out.append("\\bottomrule\\end{tabular}\\end{table}\n")
    return "".join(out)


# ------------------------------------------------------------------------------------------------------ contracts

UNITS = (("_nm", "nm"), ("_um", r"$\mu$m"), ("_mm", "mm"), ("_m", "m"), ("_rad", "rad"), ("_hz", "Hz"), ("_ms", "ms"), ("_s", "s"),
         ("_pct", "percent"), ("_waves", "waves"), ("_bytes", "bytes"), ("_per_um", r"1/$\mu$m"), ("_k", "K"), ("_thz", "THz"),
         ("_mw", "mW"), ("_amu", "amu"), ("_pa_s", "Pa s"), ("_bins", "bins"))
FRACTIONS = {"efficiency", "uniformity", "zero_order", "ghost", "filling", "fill_factor", "loading_p", "weight"}


def unit_of(name: str) -> str:
    base = name.split(".")[-1].rstrip("[]")
    for suf, u in UNITS:
        if base.endswith(suf):
            return u
    return "fraction" if base in FRACTIONS else "-"


def resolve(s: dict, root: dict) -> dict:
    while isinstance(s, dict) and "$ref" in s:
        ref = s["$ref"]
        if ref.startswith("#/"):
            node = root
            for part in ref[2:].split("/"):
                node = node[part]
            s = node
        else:
            break
    return s


def type_of(s: dict, root: dict) -> str:
    s = resolve(s, root)
    if "const" in s:
        return "const"
    if "enum" in s:
        return "enum"
    if "oneOf" in s or "anyOf" in s:
        return " or ".join(dict.fromkeys(type_of(x, root) for x in s.get("oneOf") or s.get("anyOf")))
    t = s.get("type")
    if isinstance(t, list):
        return " or ".join(t)
    if t == "array":
        item = resolve(s.get("items", {}), root)
        return f"array of {item.get('type', 'items')}"
    return t or "object"


def range_of(s: dict, root: dict) -> str:
    s = resolve(s, root)
    if "oneOf" in s or "anyOf" in s:
        alts = [range_of(x, root) for x in s.get("oneOf") or s.get("anyOf")]
        alts = [a for a in alts if a != "-"]
        return "; ".join(dict.fromkeys(alts)) or "-"
    bits = []
    if "const" in s:
        bits.append(f"= {s['const']}")
    if "enum" in s:
        e = s["enum"]
        bits.append("{" + ", ".join(str(x) for x in e[:5]) + (", ..." if len(e) > 5 else "") + "}")
    lo = s.get("minimum", s.get("exclusiveMinimum"))
    hi = s.get("maximum")
    if lo is not None or hi is not None:
        bits.append(f"{'>' if 'exclusiveMinimum' in s and 'minimum' not in s else ''}{lo if lo is not None else ''} to {hi if hi is not None else ''}".strip())
    if "minItems" in s or "maxItems" in s:
        bits.append(f"{s.get('minItems', 0)} to {s.get('maxItems', '')} items".replace("  ", " "))
    if "minLength" in s:
        bits.append(f"length >= {s['minLength']}")
    if "pattern" in s:
        bits.append("pattern")
    return "; ".join(bits) or "-"


def flatten(schema: dict, root: dict, prefix: str, depth: int, limit: int, rows: list) -> None:
    schema = resolve(schema, root)
    props = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    for name, sub in props.items():
        s = resolve(sub, root)
        path = f"{prefix}{name}"
        rows.append((path, type_of(sub, root), name in required, range_of(sub, root)))
        if depth + 1 >= limit:
            continue
        if s.get("type") == "object" and (s.get("properties") or isinstance(s.get("additionalProperties"), dict)):
            if s.get("properties"):
                flatten(s, root, path + ".", depth + 1, limit, rows)
            else:
                flatten(s["additionalProperties"], root, path + "{id}.", depth + 1, limit, rows)
        elif s.get("type") == "array":
            item = resolve(s.get("items", {}), root)
            if isinstance(item, dict) and item.get("properties"):
                flatten(item, root, path + "[].", depth + 1, limit, rows)


def parse_catalog() -> list[dict]:
    lines = (CONTRACTS / "catalog.md").read_text(encoding="utf-8").splitlines()
    out, head = [], None
    for line in lines:
        if not line.lstrip().startswith("|"):
            if head and out:
                break
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells[:2] == ["id", "version"]:
            head = cells
            continue
        if head and cells and not set(cells[0]) <= set("-: "):
            out.append(dict(zip(head, cells)))
    return out


def contract_tables(catalog: list[dict]) -> tuple[dict[str, str], str, str, dict[str, str]]:
    tables, versions, appendix = {}, {}, []
    summary = ["\\begin{table}[t]\\centering\\footnotesize\n",
               "\\caption{The data contracts of the build, from the catalog: identifier, version, owner (the module that produces the "
               "document or checks the boundary) and the committed documents the schema governs.}\\label{tab:contracts}\n",
               "\\begin{tabular}{@{}l l >{\\raggedright\\arraybackslash}p{0.34\\textwidth} >{\\raggedright\\arraybackslash}p{0.34\\textwidth}@{}}"
               "\\toprule Contract & Version & Owner & Documents governed\\\\\\midrule\n"]
    for row in catalog:
        cid = row["id"].strip("`")
        versions[cid] = row["version"]
        docs = row["documents"].replace(", ", "; ") if row["documents"] != "-" else "run-time exchange, no document"
        summary.append(f"\\texttt{{{esc(cid)}}} & {row['version']} & {{\\scriptsize\\path{{{row['owner']}}}}} & "
                       f"{{\\scriptsize\\path{{{docs}}}}}\\\\\n")
        schema_path = ROOT / row["schema file"]
        schema = load(schema_path)
        if cid == "api":
            rows = []
            for p, ops in schema["paths"].items():
                for verb, op in ops.items():
                    codes = ", ".join(sorted(op.get("responses", {})))
                    rows.append((f"{verb.upper()} {p}", op.get("summary") or op.get("operationId") or "", codes))
            t = ["\\begin{table}[t]\\centering\\footnotesize\n",
                 "\\caption{Operations of the dormant read-only API contract (the OpenAPI document of the catalog): method and path, "
                 "the operation and its response codes; every other method is refused.}\\label{tab:contract-api}\n",
                 "\\begin{tabular}{@{}l >{\\raggedright\\arraybackslash}p{0.4\\textwidth} l@{}}\\toprule Operation & Summary & Responses\\\\\\midrule\n"]
            for r in rows:
                t.append(f"\\texttt{{\\scriptsize {esc(r[0])}}} & {esc(r[1])} & {esc(r[2])}\\\\\n")
            t.append("\\bottomrule\\end{tabular}\\end{table}\n")
            tables[cid] = "".join(t)
            continue
        rows: list = []
        flatten(schema, schema, "", 0, 1, rows)
        nested: list = []
        flatten(schema, schema, "", 0, 3, nested)
        t = ["\\begin{table}[t]\\centering\\footnotesize\n",
             f"\\caption{{Top-level fields of the contract \\texttt{{{esc(cid)}}}, read from "
             f"its schema file: type, requirement, unit (a dash marks an identifier, a count or a "
             f"dimensionless quantity) and the range or constant the schema states.}}\\label{{tab:contract-{cid}}}\n",
             "\\begin{tabular}{@{}l l c l >{\\raggedright\\arraybackslash}p{0.3\\textwidth}@{}}\\toprule Field & Type & Req. & Unit & Range\\\\\\midrule\n"]
        for path, ty, req, rg in rows[:30]:
            t.append(f"\\texttt{{\\scriptsize {esc(path)}}} & {esc(ty)} & {'yes' if req else 'no'} & {unit_of(path)} & {esc(named(rg))}\\\\\n")
        if len(rows) > 30:
            t.append(f"\\multicolumn{{5}}{{@{{}}l}}{{\\textit{{{len(rows) - 30} further top-level fields: see Appendix~\\ref{{app:fields}}}}}}\\\\\n")
        t.append("\\bottomrule\\end{tabular}\\end{table}\n")
        tables[cid] = "".join(t)
        if cid in ("params-record", "case-manifest", "trace", "benchmark-results", "model-metrics", "readiness"):
            appendix.append("\\begingroup\\scriptsize\n\\begin{longtable}{@{}l l c l l@{}}\n"
                            f"\\caption{{Nested fields of the contract \\texttt{{{esc(cid)}}}, generated from its schema file: "
                            f"the path of each field, its type, whether it is required, its unit and the range or constant "
                            f"the schema states.}}\\label{{tab:fields-{cid}}}\\\\\n"
                            "\\toprule Field & Type & Req. & Unit & Range\\\\\\midrule\\endfirsthead\n"
                            "\\toprule Field & Type & Req. & Unit & Range\\\\\\midrule\\endhead\n"
                            + "".join(f"\\texttt{{{esc(p)}}} & {esc(ty)} & {'yes' if rq else 'no'} & {unit_of(p)} & {esc(named(rg))}\\\\\n"
                                      for p, ty, rq, rg in nested)
                            + "\\bottomrule\\end{longtable}\n\\endgroup\n")
    summary.append("\\bottomrule\\end{tabular}\\end{table}\n")
    return tables, "".join(summary), "\n".join(appendix), versions


# ------------------------------------------------------------------------------------------------------ the bake

def bake_tables(measured: dict, cases: dict[str, dict]) -> tuple[str, str, str, dict]:
    trap_cases = [c for c in measured if cases.get(c.split("_")[0], {}).get("target_kind") == "traps"]
    shorts = [c.split("_")[0] for c in trap_cases]
    methods = sorted({k.split(".")[0] for c in trap_cases for k in measured[c] if k.endswith(".rel_std_pct")},
                     key=lambda m: (m[0] == "B", m))   # published methods first, then the proposed ones

    def mean_of(c: str, m: str, metric: str):
        v = measured[c].get(f"{m}.{metric}")
        return None if not v else statistics.fmean(v)

    def table(metric: str, label: str, caption: str, fmt_fn) -> str:
        """Mean over the three seeds with the range over the seeds in brackets, in blocks of cases that fit the page width."""
        blocks = [list(range(0, 5)), list(range(5, 9)), list(range(9, len(trap_cases)))]
        width = max(len(b) for b in blocks)
        out = ["\\begingroup\\scriptsize\\setlength{\\tabcolsep}{2pt}\n",
               "\\begin{longtable}{@{}>{\\raggedright\\arraybackslash}p{0.15\\textwidth} " + "r" * width + "@{}}\n",
               f"\\caption{{{caption}}}\\label{{{label}}}\\\\\n"]
        for bi, idx in enumerate(blocks):
            if not idx:
                continue
            head = "Method & " + " & ".join(shorts[i] for i in idx) + " &" * (width - len(idx)) + "\\\\\n"
            out.append(("\\midrule\n" if bi else "\\toprule ") + head + "\\midrule\n")
            for m in methods:
                cells = []
                for i in idx:
                    v = measured[trap_cases[i]].get(f"{m}.{metric}")
                    cells.append("" if not v else f"{fmt_fn(statistics.fmean(v))} [{fmt_fn(min(v))}, {fmt_fn(max(v))}]")
                out.append(f"{NAME[m]} & " + " & ".join(cells) + " &" * (width - len(idx)) + "\\\\\n")
        out.append("\\bottomrule\\end{longtable}\n\\endgroup\n")
        return "".join(out)

    t_sigma = table("rel_std_pct", "tab:bake-sigma",
                    "Relative standard deviation of the trap intensities (percent), mean over the three seeds of the canonical bake with "
                    "the minimum and maximum over the seeds in brackets, every method on every point-trap case it ran on (three blocks "
                    "of cases); blank cells are methods the case does not run.", sig)
    t_eff = table("efficiency", "tab:bake-eff",
                  "Efficiency of the same runs as Table~\\ref{tab:bake-sigma}: mean over the three seeds of the canonical bake with the "
                  "range over the seeds in brackets, the fraction of the input power in the traps, scored on the case's own device.",
                  lambda v: fmt(v, 2))
    sel = tuple(ID[x] for x in ("gs", "wgs", "pfwgs", "wirtadam", "devicewgs", "robust", "paretofront"))
    cs = [c for c in ("C02_grid_feedback", "C08_device_limited", "C09_aberrated") if c in measured]
    out = ["\\begin{table}[t]\\centering\\footnotesize\n",
           "\\caption{Relative standard deviation (percent) of selected methods on three cases: mean over the three seeds of the bake and "
           "the minimum and maximum over the seeds in brackets, the uncertainty the bake supports; C02 is the ideal-device grid, C08 the "
           "device-limited array, C09 the aberrated array.}\\label{tab:seeds}\n",
           "\\begin{tabular}{@{}>{\\raggedright\\arraybackslash}p{0.3\\textwidth} " + "r" * len(cs) + "@{}}\\toprule Method & " + " & ".join(c.split("_")[0] for c in cs) + "\\\\\\midrule\n"]
    for m in sel:
        cells = []
        for c in cs:
            v = measured[c].get(f"{m}.rel_std_pct")
            cells.append("" if not v else f"{sig(statistics.fmean(v))} [{sig(min(v))}, {sig(max(v))}]")
        out.append(f"{NAME[m]} & " + " & ".join(cells) + "\\\\\n")
    out.append("\\bottomrule\\end{tabular}\\end{table}\n")
    # counts behind macros
    wins = ties = n = 0
    for c in trap_cases:
        a, b = mean_of(c, ID["gs"], "rel_std_pct"), mean_of(c, ID["wgs"], "rel_std_pct")
        if a is not None and b is not None:
            n += 1
            wins += b < a
    stats = {"nBothFourSix": n, "winsSixOverFour": wins, "nTrapCases": len(trap_cases)}
    return t_sigma, t_eff, "".join(out), stats


def table_pareto(bench: dict) -> str:
    out = ["\\begin{table}[t]\\centering\\footnotesize\n",
           "\\caption{Stored Pareto fronts of the benchmark (the converged run of the first seed, non-dominated points only): the "
           "number of stored points, and the efficiency $e$ and uniformity $u$ of the first and of the last stored point ordered by the "
           "trade-off parameter, per geometry with a front, on the ideal device.}\\label{tab:pareto}\n",
           "\\begin{tabular}{@{}l r r r r r@{}}\\toprule Geometry & Points & $e$ first & $u$ first & $e$ last & $u$ last\\\\\\midrule\n"]
    for fr in bench.get("pareto", []):
        pts = sorted(fr["points"], key=lambda p: p["lambda"])
        a, b = pts[0], pts[-1]
        out.append(f"{fr['geometry']} & {len(pts)} & {fmt(a['efficiency'])} & {fmt(a['uniformity'])} & {fmt(b['efficiency'])} & "
                   f"{fmt(b['uniformity'])}\\\\\n")
    out.append("\\bottomrule\\end{tabular}\\end{table}\n")
    return "".join(out)


# Quoted from docs/design/measured-resources.md (MR): the bake time and memory, measured by unit I1 on the development workstation.
QUOTED = {"bakeIdleS": ("515", "MR, The bake: time and memory"), "bakeLoadedS": ("761", "MR, The bake: time and memory"),
          "bakeCaseMB": ("322", "MR, The bake: time and memory")}


def headline(measured: dict) -> dict[str, str]:
    """The headline statistic of the abstract: over the cases where plain GS and phase-fixed weighted GS both ran, the median of the three-seed means of the
    spread, with the range of the three per-seed medians (the uncertainty the bake supports), and the cases it covers."""
    gs4, wgs6, pf7 = ID["gs"], ID["wgs"], ID["pfwgs"]
    both = [c for c, v in measured.items() if f"{gs4}.rel_std_pct" in v and f"{pf7}.rel_std_pct" in v]
    out = {"hlN": str(len(both)), "hlCases": ", ".join(c.split("_")[0] for c in both)}
    for m, name in ((gs4, "Four"), (pf7, "Seven")):
        means = statistics.median(statistics.fmean(measured[c][f"{m}.rel_std_pct"]) for c in both)
        per_seed = [statistics.median(measured[c][f"{m}.rel_std_pct"][s] for c in both) for s in range(3)]
        out[f"hlSigmaM{name.lower()}"] = f"{means:.2g}" if means < 1 else f"{means:.0f}"
        out[f"hlSigmaM{name.lower()}Lo"] = f"{min(per_seed):.2g}" if min(per_seed) < 1 else f"{min(per_seed):.0f}"
        out[f"hlSigmaM{name.lower()}Hi"] = f"{max(per_seed):.2g}" if max(per_seed) < 1 else f"{max(per_seed):.0f}"
    out["hlSeeds"] = "3"
    effs = [statistics.fmean(measured[c][f"{pf7}.efficiency"]) for c in both]
    out["hlEffLo"], out["hlEffHi"] = f"{min(effs):.3f}", f"{max(effs):.3f}"
    # the three methods over the cases where all of them ran (one common set, so that the medians are comparable)
    com = [c for c, v in measured.items() if all(f"{m}.rel_std_pct" in v for m in (gs4, wgs6, pf7))]
    out["cmN"] = str(len(com))
    for m, name in ((gs4, "Four"), (wgs6, "Six"), (pf7, "Seven")):
        sg = statistics.median(statistics.fmean(measured[c][f"{m}.rel_std_pct"]) for c in com)
        ef = statistics.median(statistics.fmean(measured[c][f"{m}.efficiency"]) for c in com)
        out[f"cmSigma{name}"] = f"{sg:.2g}" if sg < 1 else f"{sg:.0f}" if sg >= 10 else f"{sg:.1f}"
        out[f"cmEff{name}"] = f"{ef:.2f}"
    return out


GEO_NAMES = {"G1": "10 x 10 square", "G2": "ring of 36", "G3": "100 random", "G4": "quasi-periodic 119"}


def s3(x: float) -> str:
    return f"{x:.3g}"


def table_b1_weights() -> str:
    """The ablation of the weight update of B1 (companion manuscript's measurements): the acceptance task and the benchmark lattices."""
    comp = HERE.parents[1] / "device-aware-flicker-bounded" / "data"
    bj = load(comp / "beyond.json")["ablation"]
    out = ["\\begin{table}[t]\\centering\\footnotesize\n",
           "\\caption{Ablation of the weight update of the device-aware weighted GS, the method run with its weight update and with every "
           "weight kept at one. First block: the $10\\times10$ acceptance task, median [min, max] of the relative standard deviation "
           "$\\sigma$ (\\%) over the seeds. Second block: the four benchmark geometries on the C08 device at 10 outer iterations, median over "
           "three seeds of $\\sigma$ and of the efficiency $e$.}\\label{tab:b1-weights}\n",
           "\\begin{tabular}{@{}l r r r r@{}}\\toprule Task & $\\sigma$ with weights & $\\sigma$ no weights & $e$ with & $e$ no weights"
           "\\\\\\midrule\n"]
    for key, label in (("b1_crosstalk", "acceptance task, crosstalk device"), ("b1_full", "acceptance task, 4-bit device")):
        v = bj[key]["summary"]
        out.append(f"{label} ({v['full']['sigma']['n']} seeds) & {s3(v['full']['sigma']['median'])} "
                   f"[{s3(v['full']['sigma']['min'])}, {s3(v['full']['sigma']['max'])}] & {s3(v['no_weights']['sigma']['median'])} "
                   f"[{s3(v['no_weights']['sigma']['min'])}, {s3(v['no_weights']['sigma']['max'])}] & & \\\\\n")
    for g, nm in GEO_NAMES.items():
        rows = [r for r in load(comp / f"b1_weights_geo_{g}.json") if r["device"]]
        med = lambda k, q: statistics.median(r[k][q] for r in rows)  # noqa: E731
        out.append(f"{g} {nm} (C08 device, {len(rows)} seeds) & {sig(med('weights', 'sigma'))} & {sig(med('no_weights', 'sigma'))} & "
                   f"{fmt(med('weights', 'eff'), 3)} & {fmt(med('no_weights', 'eff'), 3)}\\\\\n")
    out.append("\\bottomrule\\end{tabular}\\end{table}\n")
    return "".join(out)


def table_power(cases: dict[str, dict]) -> str:
    """The power budget (zero order and ghost fractions) of the trap cases, for plain GS, the phase-fixed form and the reference method."""
    idx = load(DERIVED / "manifests" / "index.json")["cases"]
    out = ["\\begin{table}[t]\\centering\\footnotesize\n",
           "\\caption{Power budget of the point-trap cases at the bake seed (one seed per case): the fraction of the input power in the traps "
           "$e$, in the zero order $z_0$ and in the ghost traps $g$ (everything else on the grid, including folded replicas), for plain GS "
           "and phase-fixed weighted GS where they ran. The remainder of the power is zero for the plain Fourier form.}"
           "\\label{tab:power}\n",
           "\\begin{tabular}{@{}l r r r r r r@{}}\\toprule & \\multicolumn{3}{c}{GS} & \\multicolumn{3}{c}{Phase-fixed weighted GS}\\\\\n"
           "\\cmidrule(lr){2-4}\\cmidrule(l){5-7} Case & $e$ & $z_0$ & $g$ & $e$ & $z_0$ & $g$\\\\\\midrule\n"]
    for c in idx:
        if c["status"] != "baked":
            continue
        m = load(DERIVED / "manifests" / f"{c['case_id']}.json")
        gs4, pf7 = ID["gs"], ID["pfwgs"]
        if m["params"]["target"]["kind"] != "traps" or gs4 not in m["methods"] or pf7 not in m["methods"]:
            continue
        cells = []
        for mid in (gs4, pf7):
            v = m["methods"][mid]
            cells += [fmt(v["efficiency"], 3), fmt(v["zero_order"], 3), fmt(v["ghost"], 3)]
        out.append(f"{c['case_id'].split('_')[0]} & " + " & ".join(cells) + "\\\\\n")
    out.append("\\bottomrule\\end{tabular}\\end{table}\n")
    return "".join(out)


def derived_size() -> dict[str, int]:
    files = [p for p in DERIVED.rglob("*") if p.is_file()]
    traces = [p.stat().st_size for p in files if p.name == "trace.json"]
    return {"derivedFiles": len(files), "derivedKiB": round(sum(p.stat().st_size for p in files) / 1024),
            "traceMaxKiB": round(max(traces) / 1024)}


def median_stats(measured: dict, cases: dict[str, dict]) -> dict[str, tuple[str, str, int]]:
    """Per method: the median over the point-trap cases it ran on of the seed-mean spread and efficiency, and the case count."""
    trap_cases = [c for c in measured if cases.get(c.split("_")[0], {}).get("target_kind") == "traps"]
    out = {}
    for m in sorted({k.split(".")[0] for c in trap_cases for k in measured[c]}):
        sig_v = [statistics.fmean(measured[c][f"{m}.rel_std_pct"]) for c in trap_cases if f"{m}.rel_std_pct" in measured[c]]
        eff_v = [statistics.fmean(measured[c][f"{m}.efficiency"]) for c in trap_cases if f"{m}.efficiency" in measured[c]]
        if sig_v:
            out[m] = (sig(statistics.median(sig_v)), fmt(statistics.median(eff_v), 2), len(sig_v))
    return out


def count_tests() -> dict[str, int]:
    out = {}
    for d in sorted(p for p in (ROOT / "tests").iterdir() if p.is_dir() and p.name not in ("__pycache__", "fixtures")):
        out[d.name] = sum(len(re.findall(r"^\s*(?:async\s+)?def test_", f.read_text(encoding="utf-8", errors="replace"), re.M))
                          for f in d.rglob("test_*.py"))
    out["top"] = sum(len(re.findall(r"^\s*def test_", f.read_text(encoding="utf-8", errors="replace"), re.M))
                     for f in (ROOT / "tests").glob("test_*.py"))
    return out


def main() -> int:
    params = load(HERE / "params.json")["methods"]
    acc = {r["id"]: r for r in load(HERE / "acceptance.json")["rows"]}
    studio = load(HERE / "studio.json")
    cases = {c["short"]: c for c in studio["cases"] if c["status"] == "baked"}
    measured = load(ROOT / "data-pipeline" / "pipeline" / "cases" / "measured_ranges.json")["measured"]
    bench = load(DERIVED / "benchmark" / "results.json")
    catalog = parse_catalog()

    L = ["% Generated by data/extract_methods.py from the committed files. Do not edit.\n"]
    for mid, m in params.items():
        for k, v in m["params"].items():
            L.append(csname_macro(f"def:{slug(mid)}:{k.replace('_', '')}", esc(defval(v))))
    for r in beyond_rows.rows():
        acc[r["id"]] = r
    for mid, r in acc.items():
        L.append(csname_macro(f"acc:{slug(mid)}", esc(named(r["text"]))))
    tables, summary, appendix, versions = contract_tables(catalog)
    for cid, ver in versions.items():
        L.append(csname_macro(f"cver:{cid}", ver))
    t_sigma, t_eff, t_seeds, stats = bake_tables(measured, cases)
    for k, v in stats.items():
        L.append(f"\\newcommand{{\\{k}}}{{{v}}}\n")
    for k, (v, src) in QUOTED.items():
        L.append(f"\\newcommand{{\\{k}}}{{{v}}}  % {src}\n")
    for k, v in derived_size().items():
        L.append(f"\\newcommand{{\\{k}}}{{{v}}}\n")
    for m, (sg, ef, n) in median_stats(measured, cases).items():
        L.append(csname_macro(f"medsig:{slug(m)}", sg))
        L.append(csname_macro(f"medeff:{slug(m)}", ef))
        L.append(csname_macro(f"ncases:{slug(m)}", str(n)))
    for k, v in headline(measured).items():
        L.append(f"\\newcommand{{\\{k}}}{{{v}}}\n")
    tests = count_tests()
    total = sum(tests.values())
    for k, v in tests.items():
        L.append(csname_macro(f"nTests:{k}", str(v)))
    L.append(f"\\newcommand{{\\nTestsTotal}}{{{total}}}\n")
    L.append(f"\\newcommand{{\\nParamsTotal}}{{{sum(len(m['params']) for m in params.values())}}}\n")
    L.append(f"\\newcommand{{\\nLiveMethods}}{{{sum(1 for m in params.values() if m['lane'] in ('live', 'both'))}}}\n")
    L.append(f"\\newcommand{{\\nBakedMethods}}{{{sum(1 for m in params.values() if m['lane'] == 'baked')}}}\n")
    (HERE / "methods_numbers.tex").write_text("".join(L), encoding="utf-8")

    (HERE / "table_notation.tex").write_text(table_notation(), encoding="utf-8")
    (HERE / "table_defaults.tex").write_text(table_defaults(params), encoding="utf-8")
    (HERE / "table_nfix.tex").write_text(table_nfix(acc), encoding="utf-8")
    (HERE / "table_contracts.tex").write_text(summary, encoding="utf-8")
    for cid, t in tables.items():
        (HERE / f"table_contract_{cid}.tex").write_text(t, encoding="utf-8")
    (HERE / "appendix_fields.tex").write_text(appendix, encoding="utf-8")
    (HERE / "table_bake_sigma.tex").write_text(t_sigma, encoding="utf-8")
    (HERE / "table_bake_eff.tex").write_text(t_eff, encoding="utf-8")
    (HERE / "table_seeds.tex").write_text(t_seeds, encoding="utf-8")
    (HERE / "table_pareto.tex").write_text(table_pareto(bench), encoding="utf-8")
    (HERE / "table_b1_weights.tex").write_text(table_b1_weights(), encoding="utf-8")
    (HERE / "table_power.tex").write_text(table_power(cases), encoding="utf-8")
    print(f"wrote methods_numbers.tex and {7 + len(tables)} tables; {len(params)} methods, {len(catalog)} contracts, {total} tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
