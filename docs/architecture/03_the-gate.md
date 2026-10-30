# The gates: lane, expected ranges and units

Three pipeline gates stand between a method's output and a committed artifact. A fourth, measured on the built site, belongs to the web (`npm run gate`, see [07, deploy](07_deploy.md)).

## The lane gate

`data-pipeline/pipeline/core/gate.py`, function `classify_lane`, decides by measurement whether a case may be re-run live in the browser. The reading of the gate in DinHot:

- the unit of judgement is the case's **reference method**, the one whose maps the replay shows. The case is `live` when the reference method's spec lane is `live` or `both`, **and** one run of it at the case's own
  grid and budget takes at most `RUN_MS_GATE` = 1500 ms (the Python numpy engine is the measured proxy for the TypeScript port; the browser's own timing is measured by the web gate), **and** the trace is within
  `TRACE_BYTES_GATE` = 256 KiB (`gate.py` lines 21 to 23);
- the engine is light: pure Python with wheels within the allowed set, here numpy only (`LIVE_WHEELS`);
- every method of the case also gets a lane of its own, `method_lane`: `live` when its spec lane is live or both and its measured run fits the budget, otherwise `baked`. A method labelled live that does not fit is
  baked, never silently live.

Otherwise the case is `precompute`: the pipeline bakes it and the web only replays it. Either way a committed artifact exists, so the site shows every case on first load. The cost judged is one run after a warm-up as
the median of three (`measure_ms`), because timing the whole case once, validation and cold start included, made the verdict depend on bake order (found 2026-10-04).

The verdict and the deterministic budgets go into the manifest (`gate`), never the milliseconds, so the manifest is a pure function of `(params, seed)`. `scripts/check_artifacts.py` fails when a manifest's `lane`
disagrees with its gate, so a heavy case cannot be labelled live. Tests: `tests/bake/test_gates.py`.

## The expected ranges

An expectation written only as prose can be wrong for months without anyone noticing (the template's own epidemic case promised an attack rate that its engine did not produce, found 2026-10-04). Every case therefore states a
numeric range for named metrics, and `data-pipeline/pipeline/core/expect.py` fails the bake on a value outside it, naming the case, the method and the metric. The manifest carries the ranges so the web can judge a live
run against them too. A key is a metric of the reference method (`efficiency`, `uniformity`, `rel_std_pct`, `zero_order`, `ghost`, `iterations`), a case metric measured by a driver (`feedback_initial_rel_std_pct`,
`feedback_final_rel_std_pct`, `fc_ratio`, `boltzmann_tv`, `min_transient`, `final_filling`), or `<method>.<metric>`. The ranges and their basis, anchor or provisional, are on each [case card](../cases/README.md).

## The units gate

`data-pipeline/pipeline/core/units.py` checks, in the bake and again over the shipped artifacts, that every observable is in its physical domain and in the units of the question it answers:

| Observable | Domain and unit |
|---|---|
| efficiency, uniformity, zero-order fraction, ghost fraction, filling | 0 to 1 |
| relative standard deviation | percent (not a fraction), 0 to 1000 |
| trap intensity in a trace | relative to the mean trap (mean 1) |
| positions | micrometres, inside the unaliased field of view (a position in metres would be about 1e-5) |
| times, stiffness, frequencies | seconds; pN per micrometre; Hz |

The check that a method's output is in the units of the question is the consistency between numbers a trace carries twice: the relative standard deviation and the uniformity are recomputed from the per-trap intensities (for an
all-equal-weights case) and must agree, so a fraction written where a percent belongs, or a metric of another quantity under the right name, fails. Tests include a plant of that failure
(`tests/bake/test_gates.py`). Standard library only, so the check also runs over a shipped tree without numpy.

## The web gate

`npm run gate` serves the built `dist/` as Pages would and walks every route, tab and case at five sizes, in both themes and both languages. A person reads its captures: the gate measures, it does not judge content.
