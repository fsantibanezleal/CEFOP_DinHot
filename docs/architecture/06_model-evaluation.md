# Model evaluation (the TEST stage)

`stages/evaluate.py` reports held-out, **leakage-safe** metrics, the holdout is a disjoint draw, never the
training set. EXAMPLE: surrogate-vs-engine on the peak-infected fraction → R² + RMSE (RMSE, not MAPE: MAPE blows
up on the near-zero peaks of sub-critical cases and would mislead). The metrics are written into each case's
manifest (`metrics`) and surfaced on the web's Benchmark/Experiments views.

For a real product this is where the honesty lives: held-out (never calibration-leaked) metrics, negative
controls, and, when a surrogate emulates a physics engine, a clear statement that "accurate" means *agrees with
the calibrated engine*, NOT *matches a real plant*. Keep calibration anchors strictly disjoint from validation.
