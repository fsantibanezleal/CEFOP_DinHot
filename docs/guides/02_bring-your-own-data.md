# Guide: bring your own case

DinHot applies to a reader's own task, not only to its fourteen cases: a trap geometry or a shaped potential on an optical setup and an SLM that the reader states. The door is contract 1
(`data-pipeline/pipeline/io/contract.py`), which validates a params record against `docs/contracts/schemas/params-record.schema.json`. A complete example record is
[`docs/contracts/examples/params-record.json`](../contracts/examples/params-record.json); the twelve built-in records are in `data/examples/cases.json`.

1. Write one record per case in an array (a copy of `data/examples/cases.json` is the starting point; the field table is in
   [the data contracts](../architecture/08_data-contracts.md)). The units are fixed: the wavelength in nm, the focal length in mm, the pixel pitch in um, trap positions in um, the aberration in waves (Noll indices), the phase
   flicker in rad. A trap carries an id, a position, a relative weight and a topological charge; a shaped target names its shape and dimensions.
2. Choose the methods of the ladder that fit the target (the point-trap methods take traps; M04, M08, M10, M11, M13, M17 and M18 take shaped fields) and one reference method, whose maps the replay shows.
3. Run the pipeline on it into a sandbox, for example `python data-pipeline/run.py <case_id> --output <sandbox>`. Contract 1 validates each record: **rejected with its reason** when it breaks the schema or a rule (a trap outside the
   unaliased field of view `lambda f / (2 p)` is refused with that bound in the reason), **flagged** when plausible but unusual (the scalar model beyond a numerical aperture of 0.7, traps closer than the focal spot),
   accepted otherwise. Nothing is coerced.
4. The pipeline writes a manifest and a trace in the same shapes as the built-in cases, and checks the result against the expected ranges declared for the record. A record with no expected ranges of its own should declare the
   ones it needs: a range is how a case states what it expects.
5. In the web, the live engine re-runs any case with the reader's values, the method and the device the reader picks, and the traps the reader edits: a reader exploring a task does not need a bake at all for the live methods.
   The baked methods (direct search, the device-aware optimizers, OT-initialized MRAF and the robust and Pareto methods) need the bake.

If the data does not fit, extend contract 1 and its tests deliberately; never loosen it to let bad data through. A case outside the engine's validity (a numerical aperture far above 0.7) is computed with the validity flag shown,
never silently.
