# The lane gate

`data-pipeline/pipeline/core/gate.py :: classify_lane()` decides, per case and by measurement, whether the case is
light enough to be re-run live in the browser:

- the engine is light (pure Python, with its wheels within a small allowed set: a proxy for an engine small enough to
  port or to run client side), and
- one run finishes within `RUN_MS_GATE` (1500 ms), and
- the committed trace is within `TRACE_BYTES_GATE` (256 KiB).

Otherwise the case is `precompute`: the pipeline bakes it and the web only replays it. Either way a committed
artifact exists, so the site shows every case on first load.

The verdict and the measured numbers are written into the manifest (`gate`), and `scripts/check_artifacts.py`
fails when a manifest's `lane` disagrees with its gate, so a heavy case cannot be labelled live. The Benchmark page
measures the live engine again in the reader's browser against the same run budget.

This is the pipeline's gate. The web has its own, measured on the built site: `npm run gate` (`caos-shell-gate`,
see [07, deploy](07_deploy.md)).
