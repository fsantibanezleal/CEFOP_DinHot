# Guide: bring your own data

A product applies to new data, not only to its baked cases. The door is contract 1
(`data-pipeline/pipeline/io/contract.py`).

1. Put the input in the documented format (see [`data/README.md`](../../data/README.md); in the example, a parameters
   CSV with `case_id,beta,gamma,N,I0[,days]`) under `data/raw/`, which git ignores.
2. Run the pipeline on it with a sandbox output, for example
   `python data-pipeline/run.py <case> --output build/mine`. Contract 1 validates each record: rejected with its
   reason when it breaks the schema or a range, flagged when plausible but unusual, accepted otherwise.
3. The pipeline writes an artifact and a manifest in the same shapes as the built-in cases, and checks the result
   against the expected ranges declared for it.
4. In the web, the live engine re-runs any case with the reader's values; a reader exploring a parameter set does
   not need a bake at all.

If your data does not fit, extend contract 1 and its tests deliberately; never loosen it to let bad data through.
