# Cases + categories

Each case (`data-pipeline/pipeline/cases/`) declares a **CATEGORY** (the domain problem-type taxonomy), its
params, an expected band (what a domain expert should see), and a real|synthetic flag. `registry.list_categories()`
groups them. The **App shows ONE selected case**; **Experiments/Benchmark show cross-case summaries by category**
(never mixed into the App).

## Coverage matrix (EXAMPLE, SIR; replace with your real, varied matrix)

| id | category | expected band | real/synthetic |
|---|---|---|---|
| `EX01_subcritical` | sub-critical (R0<1) | no outbreak; attack rate ≈ 0 | synthetic |
| `EX02_epidemic` | epidemic (R0>1) | clear single peak; attack rate ≈ 0.7–0.9 | synthetic |
| `EX03_fast_burn` | fast-burn (high R0) | early sharp peak; attack rate → ~1 | synthetic |
| `EX04_slow_spread` | slow-spread (R0~1.2) | broad low peak | synthetic |
| `CTRL_degenerate` | control: degenerate | `I0=0` → no dynamics (must not crash) | synthetic |

A real product fills a matrix spanning its real axes (not "two of everything") + explicit negative/sanity
controls, and adds one `docs/cases/<category>/<case-id>.md` per case (formalization + expected results + anchor).
Copy [`00_TEMPLATE.md`](00_TEMPLATE.md) as the starting point for each per-case page.
