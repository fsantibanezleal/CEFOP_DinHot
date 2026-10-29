# M17: Unsupervised CNN hologram (DeepCGH form, three planes)

| Item | Value |
|---|---|
| Ladder row | M17, tier sota (SDD, Method ladder) |
| Family, lane | learned; `SPEC.lane` is `live`, inference by onnxruntime-web, training offline |
| Targets, dimensions | traps as point voxels on three planes, 3D (`SPEC.dims` is `(3,)`) |
| Module | `data-pipeline/pipeline/model/holo/methods/learned/m17_cgh_net.py` (`SPEC` line 40, `GRID` line 41, `BASELINE_ITERATIONS` line 42, `LIMIT_BINS` line 43, `planes_from_traps` line 57, `run` line 82); network and training in `data-pipeline/pipeline/model/holo/learned/` |
| Gate | `tests/learned/test_m17_cgh_net.py` |
| Released model | `models/cgh-net.onnx` and its card `models/cgh-net.json`; metrics `data/derived/models/metrics.json`, detail `data/derived/models/evaluation-detail.json` |
| Live port | no TypeScript method in `frontend/src/engine/holo/` (not in `liveMethodIds`); the inference is `frontend/src/lib/ort.ts` |
| Card | [M17](../../frameworks/M17_unsupervised-cnn-hologram.md) |

## Tier and role

State of the art, replicated in the setting of its own paper: DeepCGH, Eybposh et al., Opt. Express 28, 26636 (2020),
https://doi.org/10.1364/OE.399624 trains a U-Net, unsupervised, that maps the target amplitudes of several planes to one SLM phase with a loss
through a differentiable propagation to every plane. The paper reports at least 10 times faster than GS and 9 to 43 percent more accurate on
volume targets (up to 3500 iterations for each iterative method, 1000 test samples; 1035 nm, focal length 200 mm, pixel 9.2 um). DinHot's M17 is
that setting at DinHot's size. A first version on a single plane tied with GS and was rejected; on the decision of the main session M17 was rebuilt in
DeepCGH's own setting, a volume (M1 report, Update 2). No source read compares a learned method against WGS on the uniformity of hundreds of
point traps; a supervised variant for tweezers (Ren et al. 2024, https://arxiv.org/abs/2401.06014) reports 0.16 s per hologram against about 6 s for
GS and about 10 percent trap-depth variation on about 20 sites.

## Problem it answers

A hologram for a three-plane point target by one network pass, in about 35 ms, when the target changes at interaction rate; the baseline it must beat is
the volumetric 3D GS (M19) at the same wall-clock.

## Inputs and outputs

- Setup: only the SLM of 128 by 128 pixels with padding 1 (`check_geometry`, `m17_cgh_net.py` line 47); another setup raises a `ValueError`.
- Target: traps (a shaped field is refused naming `traps`) at integer lateral bins within 60 bins of the axis (`LIMIT_BINS`, line 43), no vortex, on the
  three depths $z = -8, 0, +8$ SLM-limited Rayleigh ranges to within 0.05 (`planes_from_traps`, lines 57 to 74); the SLM-limited Rayleigh range is
  $z_R = \lambda f^2/(\pi R^2)$ with $R = n_{pix}\,p/2$ (`learned/convert.py` line 15), which makes the defocus phase at the aperture edge exactly $Z$ radians.
- Network input (card): `target`, float32 of shape `[1, 3, 128, 128]`: the unit-energy amplitudes of the three planes on the focal crop (Gaussian spots of
  sigma 1 bin, `generators.render_spots`). Output `phase`, float32 `[1, 1, 128, 128]`, radians.
- Output of `run`: a `Result` with `phi` (128 by 128), `fields` (the trap fields), one `history` entry, and `meta` including `provenance` (`real` when the released
  model answered, `baseline` otherwise), `network_s`, `refine_iterations`, `refine_kept`.

## The method

Network `CghVolNet` (`learned/nets.py`): a U-Net of 14 channels with 0.99 million parameters that predicts one complex focal field per plane; a constant inverse DFT
(a matrix product) and the lens phase of each plane carry each to the SLM; they are summed and the output is the phase of the sum (`atan2`); ONNX opset 17,
4 671 540 bytes (limit 5 MB), every operator in the web-safe list (`learned/webops.py`).

Loss and accuracy (defined in the module docstring; DeepCGH's own accuracy formula was not read, UNVERIFIED, and this definition is used for the loss, the baseline and
the evaluation alike): the plane field is the centred orthonormal FFT of $A e^{i(\phi - Z q)}$ with $q$ the quadratic lens term; with $T$ and $I$ the unit-sum plane
intensities of the target and of the hologram,

$$AC = \frac1P\sum_{p}\frac{2\sum T_p I_p}{\sum T_p^2 + \sum I_p^2},\qquad \mathcal L = 1 - AC$$

(`methods/learned/_planes.py` line 11; `learned/torch_forward.py`). The torch forward model is verified against the engine's `point_trap_fields` at a trap of that
depth (`tests/learned/test_torch_forward.py::test_plane_intensity_matches_the_engine_point_trap_model_at_depth`).

Inference. With the model released, the hybrid runs the network and then M19 from the network's phase in what is left of `budget.time_s`, at most `budget.iterations`
iterations and at least one; the refinement is kept only if it raises the volume accuracy of the network's mask (`m17_cgh_net.py` lines 106 to 118), because M19 is a
point-voxel method and its refinement can lower the accuracy of the full plane images. `refine=False` returns the network's phase alone. With no released model
the baseline answers: M19 at 30 iterations (`BASELINE_ITERATIONS`), `provenance = 'baseline'` (the missing-data rule of the catalog row `cgh-net`).

## Defaults

| Parameter | Default | Where | Source of the value |
|---|---|---|---|
| geometry | 128 by 128 pixels, `pad` 1 | `m17_cgh_net.py` lines 41 and 47 | the size the released graph is trained for |
| plane depths | $-8, 0, +8$ Rayleigh ranges (`PLANE_Z = 8.0`) | `learned/generators.py` line 213 | DinHot's choice: the defocus phase at the aperture edge is 8 rad (M1 report) |
| baseline | M19, 30 iterations | `m17_cgh_net.py` line 42 | the catalog row `cgh-net` |
| lateral limit | 60 bins | line 43 | DinHot's choice (the crop is 128 bins) |
| `refine` | `True` | `run`, line 82 | the M1 report recommends calling with `refine=False`: the refinement was never kept on the held-out set |
| training | 16 000 steps, batch 32, data seed 20261103, init seed 13, learning rate 0.001 | `data/derived/models/cgh-net-training.json` | M1 report; the schedule was restarted once at step 3500 with a shorter total |

## Complexity and lane

Inference is one pass of a 0.99M-parameter U-Net (median 34.9 ms in the committed evaluation, `network_ms_median` of `evaluation-detail.json`), on one thread of
onnxruntime-web (GitHub Pages sends no cross-origin isolation headers). Training is offline on a GPU (about 1.3 h, the SDD limit is 3 h and 7 GB) and never in CI
or in the browser (ADR-0069, ADR-0074). The baseline M19 takes a median 7.35 s at 30 iterations on the held-out volumes on the development machine.

## Acceptance criterion and gate

The ladder row of the SDD reads: "on 162 held-out three-plane volumes, the network start followed by M19 refinement inside the same wall-clock budget
reaches a higher accuracy than M19 alone". The superseded single-plane version (record `data/derived/models/cgh-net-2d-rejected.json`: ratio 0.9994 hybrid,
0.9983 network alone) was measured against GS and not released. The criterion the code and the test implement: on held-out volumes, the accuracy of the hybrid is
above that of M19 alone at the same wall-clock (median per-volume ratio above 1). Gate `tests/learned/test_m17_cgh_net.py`:

- `::test_committed_metrics_meet_the_criterion`: reads `data/derived/models/metrics.json`; `held_out_n` at least 150 and the median `accuracy_vs_gs` above 1;
- `::test_sampled_held_out_volumes_beat_m19_at_the_same_wall_clock`: needs the released graph, onnxruntime and the held-out file (`DINHOT_LEARNED_DIR`); every eighth
  volume, the budget the median M19 time at 30 iterations, the median ratio above 1;
- `::test_the_baseline_answers_while_unreleased`, `::test_the_hybrid_runs_the_network_then_m19_inside_the_budget`, `::test_planes_from_traps_renders_three_unit_energy_planes`,
  `::test_geometry_and_target_errors_name_the_requirement`.

## Evaluation that confirms or refutes it

Confirmed if the median per-volume accuracy ratio hybrid over M19 at equal wall-clock exceeds 1 on held-out volumes written before the training run. The single-plane
version was refuted by the same test (ratio 0.998) and not released; the record is kept.

## Measured result

Committed evaluation (`data/derived/models/metrics.json` and `evaluation-detail.json`, produced by the evaluate stage on the released graph; M1 report Update 2). Conditions:
162 held-out volumes (160 generated, 40 per kind of random, lattice, ring and mixed, data seed 20269004, plus two benchmark layouts: the 3D lattice G5 and the three-plane
layout of the M19 acceptance test), sha256 `3c974555676078b4756443e750793ae8c3a5bced595d673a0fa3092f1d316cb0` (the file lives in the data root, not in the repository);
wall-clock budget $T$ = 7354.6 ms (the median of M19 at 30 iterations on those volumes); one machine.

| Quantity | Measured |
|---|---|
| Ratio hybrid over M19 at equal wall-clock, median [q1, q3] | 1.140 [1.102, 1.160]; above 1 on 162 of 162 volumes |
| Median volume accuracy AC | hybrid 0.6869, M19 0.5997 |
| By kind | lattice 1.162, random 1.147, mixed 1.118, ring 1.100, G5 lattice 1.065, M19 three-plane layout 1.188 |
| Budget curve (54 volumes each) | 1.149 at 0.33 $T$ (2.4 s), 1.148 at 0.6 $T$ (4.4 s), above 1 on 100 percent |
| Refinement | never kept: the hybrid AC equals the network alone, so the network (34.9 ms) answers, about 200 times faster than the budget |
| ONNX parity with torch | reconstructed plane intensities, max $|\Delta I|/\max I$ = 8.42e-6 (inside 1e-5); the phase differs up to 4.2e-3 (99.9th percentile 3.9e-4), reported, not claimed |

The committed canonical bake has no M17 rows: its manifests flag "methods not registered in this build: M17" (for example `data/derived/manifests/C04_disc_crosstalk.json`), because that bake (I1 report) was run before the learned package was registered.

Caveat stated in the report: M19 is a point-voxel method scored here on full plane images (ghosts and blur count), which is what the network optimizes; the trap-uniformity
objective of M19 is not what AC measures. The single-plane record: median ratio 0.9994 (hybrid) and 0.9983 (network alone) on 219 held-out targets, network 35.8 ms; GS at
30 iterations 0.9873 and at 300 iterations 0.9925 against the network alone 0.9745.

## Limits and failure modes

- The model is specific to its crop and planes (128 by 128, pad 1, three depths); DeepCGH also trains one model per resolution and plane set.
- The accuracy is DinHot's AC definition (UNVERIFIED against the paper's formula); the advantage is on plane images, not on trap uniformity.
- The web encoder `frontend/src/lib/ort.ts` (`encodeCghPlanes`, line 83; `predictCghPhase`, line 252) builds the three-plane input `[1, 3, 128, 128]` the card declares.
- The phase of a near-zero SLM field is ill-conditioned (`atan2`), hence the parity claim on intensities.

## References

- Eybposh et al. 2020, Opt. Express 28, 26636, https://doi.org/10.1364/OE.399624
- Whyte and Courtial 2005, New J. Phys. 7, 117, https://doi.org/10.1088/1367-2630/7/1/117 (the baseline M19)
- Ren et al. 2024, https://arxiv.org/abs/2401.06014
- Shi et al. 2021, Nature 591, https://doi.org/10.1038/s41586-020-03152-0 (the size of a hologram network; abstract only read)
