# The method interface and the registry

Every method of the ladder is one module with the same shape, so that the bake, the benchmark, the notebooks and the TypeScript port can all call it the same way. The types are in
`data-pipeline/pipeline/model/holo/core/types.py` and the registry in `data-pipeline/pipeline/model/holo/methods/__init__.py`.

## The module contract

A method module exposes `SPEC`, a `MethodSpec`, and a `run` function:

```
SPEC = MethodSpec(id="M06", name="Weighted GS", family="GS", lane="live", targets=("traps",), dims=(2, 3))

def run(setup, target, *, device=None, budget, rng, init=None) -> Result: ...
```

- `MethodSpec`: `id` (a letter then letters, digits, underscores or hyphens), `name`, `family`, `lane` (`live`, `baked` or `both`), `targets` (a non-empty subset of `traps` and `field`) and `dims` (a subset of 2 and 3).
- `Budget(iterations, time_s=None)`: an iteration cap and an optional wall-clock cap in seconds.
- `Target`: either a `TrapSet` (point traps) or a shaped field, an `amplitude` on the FFT grid and a boolean signal `mask`; exactly one.
- `Result`: `phi` (float64, `n_pix` by `n_pix`, finite), `history` (a list of dicts, each with at least `iteration, efficiency, uniformity, rel_std, time_s`), `fields` (the final trap fields $V_m$ or the focal field) and a free `meta`.
- `device=None` means the ideal device; `init` is an optional starting phase (`None`: the method's own start, drawn through `rng`); `rng` is the only source of randomness (ADR-0054).
- The missing-data rule: a method that does not take the target kind raises `ValueError` naming the kinds it does take, never a wrong answer.

## The registry

`methods.discover` imports every module below the subpackages `baseline`, `control`, `optim` and `beyond` recursively, collects `SPEC` and `run`, and returns the methods sorted by id. A missing subpackage is skipped; any
other import error is raised, so a broken method cannot vanish silently; a module without `run`, or a duplicate id, is an error. `all_specs()` lists the specs; `get(id)` returns the method or a `KeyError` naming the
registered ids. The learned methods (M17, B3) join the registry through their own subpackage when it lands.

| Subpackage | Methods |
|---|---|
| `baseline` | M01 to M08, M19 (with the shared Gerchberg-Saxton engine and helpers) |
| `control` | M12, M14, M15, M16 |
| `optim` | M09, M10, M11, M13, M18 (with the shared optimizers and costs) |
| `beyond` | B1, B2, B4, B5 |

Tests: `tests/engine/test_types_registry.py` (planted temporary packages: a nested subpackage is found, an unscanned name is ignored, no `run`, a duplicate id, a broken import), `tests/methods/baseline/test_registry_e2.py`
(the thirteen baseline and control ids are discovered and every trap-only method refuses a field target).

## Why the lane is on the spec

`SPEC.lane` is what the lane gate and the benchmark read: `live` means the TypeScript port exists and a run fits the live budget, `baked` means the Python engine runs it offline and the site replays it, `both` means a small
size runs live and the full size is baked ([the lane gate](03_the-gate.md)).
