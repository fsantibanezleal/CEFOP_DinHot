"""The benchmark protocol runner (algorithms D4.3 items 3 to 8) over the method registry.

Per method, geometry, device (ideal or the C08 device) and parameter set (the method's defaults, or the best of a small
shared tuning grid), over ``seeds`` seeds (seed ``s`` is the engine seed, so every method of a cell starts from the same
random numbers), six runs per seed:

- iteration budgets 10, 30 and 100: a run of exactly that many iterations;
- wall-clock budgets 50 ms and 1 s: a run capped at that time (and at the converged cap);
- converged: a run to the cap ``CONVERGED_CAP`` iterations, which is also the 60 s row (the cap is reached well before 60 s
  on the benchmark grids; a run that reaches 60 s first is cut there by the budget itself).

Every run is scored by ``core/score.py`` from its final phase, through the device when there is one (the offline hologram
is scored against the device model, D4.3 item 6), never by the method's own history. A row reports the median and the
inter-quartile range over seeds of efficiency, uniformity, relative standard deviation (percent), the wall-clock seconds of
the run and the iterations performed.

Tuning (item 5): a method that declares ``TUNING`` (a list of exactly ``TUNING_CANDIDATES`` keyword dictionaries for its
``run``), or has an entry in ``FALLBACK_TUNING`` whose names its ``run`` accepts, is tuned: each candidate runs on
``TUNING_SEEDS`` seeds (different from the protocol seeds) at 30 iterations and the one with the lowest median relative
standard deviation among those with at least half the best median efficiency is used for the ``tuned`` rows. The number of
tuning runs is the same for every tuned method (``TUNING_CANDIDATES * TUNING_SEEDS``). A method without a tuning grid has
``default`` rows only; no row ever mixes one method's tuned parameters with another's defaults, and the ``params`` field of
each row says which it is.

A cell that cannot run is listed in ``skipped`` with its reason (the method is not registered, its spec does not take the
geometry's target, or a device model cannot be read off the focal plane), never silently absent (ADR-0069).
"""
from __future__ import annotations

import inspect
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from .. import __version__
from ..io.formats import read_json, write_json
from ..model.holo import methods as registry
from ..model.holo.core.types import Budget
from ..stages import infer
from . import geometries as G

LADDER = [f"M{k:02d}" for k in range(1, 20)] + [f"B{k}" for k in range(1, 6)]
TUNING_CANDIDATES = 4
TUNING_SEEDS = 3
TUNING_SEED_OFFSET = 1000
TUNING_ITERATIONS = 30
MAX_WORKERS = 12
# A group runs seeds until it has used GROUP_BUDGET_S of wall-clock time, never fewer than MIN_SEEDS: every row records the
# seeds it ran (n_seeds), so a group that stopped early says so instead of holding the whole run.
GROUP_BUDGET_S = 600.0
MIN_SEEDS = 2
# the dossier's tuned parameters (D4.3 item 5); applied only when the method's run accepts the name
FALLBACK_TUNING: dict[str, list[dict]] = {
    "M05": [{"alpha": a} for a in (0.25, 0.5, 0.75, 1.0)],
    "M08": [{"mixing": p} for p in (0.3, 0.4, 0.55, 0.7)],
    # t is an even cost power (Harte et al. 2014, Eq. 10): the basic cost, the powered one, and the sequential schedule.
    "M10": [{"t": 2}, {"t": 4}, {"t": (4, 2)}, {"t": (4, 2), "efficiency": 0.8}],
    # around the measured step of the quadratic loss (m11_wirtinger_adam docstring: 1.0 to 2.0 best, 4.0 diverges)
    "M11": [{"lr": r} for r in (0.5, 1.0, 2.0, 4.0)],
}


@dataclass(frozen=True)
class Protocol:
    seeds: int = 8
    iterations: tuple = (10, 30, 100)
    times: tuple = (0.05, 1.0)
    cap: int = 300
    converged_s: float = 20.0
    reduced: bool = False

    def grids(self) -> list[int]:
        return sorted({G.grid_of(g, self.reduced) for g in G.GEOMETRIES})


def reduced_protocol(seeds: int = 4) -> Protocol:
    return Protocol(seeds=seeds, iterations=(2, 4, 8), times=(0.05, 0.2), cap=12, converged_s=1.0, reduced=True)


def _text(en: str, es: str) -> dict:
    return {"en": en, "es": es}


def skip_reason(mid: str, geometry: str, reduced: bool) -> dict | None:
    """Why the (method, geometry) cell cannot run at all (None when the ideal-device cell can)."""
    known = {s.id: s for s in registry.all_specs()}
    if mid not in known:
        return _text("The method is not registered in this build.", "El método no está registrado en esta versión.")
    rec = G.record(geometry, device=False, seed=0, reduced=reduced)
    problem = infer.spec_problem(known[mid], rec)
    if problem:
        return _text(problem[0].upper() + problem[1:] + ".", "La especificación del método no admite este objetivo.")
    return None


def device_skip_reason(geometry: str) -> dict | None:
    if G.is_3d(geometry):
        return _text("Device cell not run: a device model is read at the focal plane and this geometry has several planes.",
                     "Celda con dispositivo no ejecutada: el modelo del dispositivo se lee en el plano focal y esta "
                     "geometría tiene varios planos.")
    return None


def tuning_grid(mid: str) -> list[dict] | None:
    """The method's ``TUNING`` list, else the fallback entries its ``run`` accepts; None when it is not tunable."""
    method = registry.get(mid)
    mod = sys.modules.get(method.run.__module__)
    grid = getattr(mod, "TUNING", None)
    if grid is None and mid in FALLBACK_TUNING:
        params = inspect.signature(method.run).parameters
        grid = [c for c in FALLBACK_TUNING[mid] if all(k in params for k in c)]
    if not grid or len(grid) != TUNING_CANDIDATES:
        return None
    return [dict(c) for c in grid]


def _stat(values: list[float]) -> dict:
    q1, med, q3 = np.percentile(np.asarray(values, dtype=np.float64), [25, 50, 75])
    return {"median": round(float(med), 6), "q1": round(float(q1), 6), "q3": round(float(q3), 6)}


def _row(mid, geometry, device, kind, budget, params, outs) -> dict:
    return {"method": mid, "geometry": geometry, "device": "device" if device else "ideal", "budget_kind": kind,
            "budget": budget, "params": params, "n_seeds": len(outs),
            "efficiency": _stat([o.score["efficiency"] for o in outs]), "uniformity": _stat([o.score["uniformity"] for o in outs]),
            "rel_std_pct": _stat([o.score["rel_std_pct"] for o in outs]), "time_s": _stat([o.seconds for o in outs]),
            "iterations": _stat([float(o.iterations) for o in outs])}


def _record(geometry: str, device: bool, seed: int, reduced: bool) -> dict:
    return G.record(geometry, device=device, seed=seed, reduced=reduced)


def tune(mid: str, geometry: str, device: bool, reduced: bool) -> dict | None:
    """The best candidate of the method's tuning grid on this cell (see the module docstring)."""
    grid = tuning_grid(mid)
    if grid is None:
        return None
    results = []
    for cand in grid:
        outs = []
        for k in range(TUNING_SEEDS):
            rec = _record(geometry, device, TUNING_SEED_OFFSET + k, reduced)
            outs.append(infer.run_method(rec, mid, budget=Budget(TUNING_ITERATIONS), extra=infer._accepted(
                registry.get(mid).run, cand)))
        results.append((cand, float(np.median([o.score["efficiency"] for o in outs])),
                        float(np.median([o.score["rel_std_pct"] for o in outs]))))
    floor = 0.5 * max(r[1] for r in results)
    return min((r for r in results if r[1] >= floor), key=lambda r: r[2])[0]


def run_group(task: dict) -> dict:
    """One (method, geometry, device, parameter set) group over all seeds: its rows, and B5's Pareto points if any.
    Runs in a worker process; ``task`` is plain data."""
    for p in task.get("sys_path", []):
        if p not in sys.path:
            sys.path.insert(0, p)
    if task.get("base_package"):
        registry.reload(task["base_package"])
    proto = Protocol(**{**task["protocol"], "iterations": tuple(task["protocol"]["iterations"]),
                        "times": tuple(task["protocol"]["times"])})
    mid, geometry, device, kind = task["method"], task["geometry"], task["device"], task["params"]
    run_fn = registry.get(mid).run
    extra = {} if kind == "default" else (tune(mid, geometry, device, proto.reduced) or {})
    extra = infer._accepted(run_fn, extra)
    per: dict[tuple, list] = {}
    pareto = None
    t_group = time.perf_counter()
    for seed in range(proto.seeds):
        if seed >= MIN_SEEDS and not proto.reduced and time.perf_counter() - t_group > GROUP_BUDGET_S:
            break
        rec = _record(geometry, device, seed, proto.reduced)
        ctx = infer.case_context(rec)
        runs = [("iterations", n, Budget(n)) for n in proto.iterations]
        runs += [("time", t, Budget(proto.cap, t)) for t in proto.times]
        runs += [("converged", float(proto.cap), Budget(proto.cap, proto.converged_s))]
        for bk, b, budget in runs:
            out = infer.run_method(rec, mid, budget=budget, extra=extra, ctx=ctx)
            per.setdefault((bk, b), []).append(out)
            if bk == "converged":
                front = out.meta.get("pareto")
                if seed == 0 and mid == "B5" and not device and isinstance(front, list) and front:
                    pareto = [{"lambda": float(p["lambda"]), "efficiency": round(float(p["efficiency"]), 6),
                               "uniformity": round(float(p["uniformity"]), 6)} for p in front]
    rows = [_row(mid, geometry, device, bk, b, kind, outs) for (bk, b), outs in per.items()]
    return {"rows": rows, "pareto": pareto, "geometry": geometry}


def _order(row: dict) -> tuple:
    return (row["method"], row["geometry"], row["device"], row["params"], ("iterations", "time", "converged").index(row["budget_kind"]),
            row["budget"])


def _group_key(row: dict) -> tuple:
    return (row["method"], row["geometry"], row["device"], row["params"])


def document(proto: Protocol, rows: list[dict], pareto: list[dict], skipped: list[dict]) -> dict:
    doc = {
        "schema": "dinhot.benchmark/v1", "engine_version": __version__,
        "protocol": {"grids": proto.grids(), "seeds": proto.seeds,
                     "budgets": {"iterations": list(proto.iterations), "time_s": list(proto.times)},
                     "device": _text("Ideal, and the C08 device (4-bit phase, crosstalk sigma 1.24 q 1.80 on 3 x 3 sub-pixels, "
                                     "fill factor 0.85, flicker 0.05 rad). Every hologram is scored against its device. The "
                                     "device rows run with the default parameters only (the tuning is done on the ideal "
                                     "model) and not on the multi-plane geometries (a device model is read at one focal "
                                     "plane). The converged row runs to 300 iterations or 20 s; a group runs its seeds until 600 s of wall clock "
                                     "(at least 2, n_seeds says how many). Times are wall-clock "
                                     "seconds of the machine that ran the benchmark, under shared load, and differ "
                                     "between runs.",
                                     "Ideal, y el dispositivo C08 (fase de 4 bits, diafonía sigma 1,24 q 1,80 en 3 x 3 "
                                     "subpíxeles, factor de llenado 0,85, parpadeo 0,05 rad). Cada holograma se evalúa contra "
                                     "su dispositivo. Las filas con dispositivo usan solo los parámetros por defecto (el ajuste "
                                     "se hace sobre el modelo ideal) y no se ejecutan en las geometrías de varios planos (el "
                                     "modelo del dispositivo se lee en un solo plano focal). La fila convergida corre hasta "
                                     "300 iteraciones o 20 s; un grupo corre semillas hasta 600 s de reloj (al menos 2, n_seeds dice cuántas). "
                                     "Los tiempos son segundos de reloj de la máquina que ejecutó el "
                                     "benchmark, con carga compartida, y difieren entre ejecuciones.")},
        "geometries": [{"id": g, "name": G.GEOMETRIES[g][0], "n_traps": G.n_traps(g, proto.reduced), "dims": G.GEOMETRIES[g][2]}
                       for g in G.GEOMETRIES],
        "rows": sorted(rows, key=_order), "pareto": sorted(pareto, key=lambda p: p["geometry"]),
    }
    if skipped:
        doc["skipped"] = sorted(skipped, key=lambda s: (s["method"], s["geometry"], s["reason"]["en"]))
    return doc


def _load_done(path: Path, proto: Protocol) -> tuple[list[dict], list[dict]]:
    """Rows and Pareto fronts of an earlier run of this version with this protocol (for ``--resume``)."""
    if not path.is_file():
        return [], []
    old = read_json(path)
    same = (old.get("engine_version") == __version__ and old["protocol"]["seeds"] == proto.seeds
            and old["protocol"]["budgets"] == {"iterations": list(proto.iterations), "time_s": list(proto.times)}
            and old["protocol"]["grids"] == proto.grids())
    return (old["rows"], old.get("pareto", [])) if same else ([], [])


def run(derived_root: str | Path, *, seeds: int = 20, workers: int = 12, reduced: bool = False,
        geometries: list[str] | None = None, methods: list[str] | None = None, resume: bool = False,
        protocol: Protocol | None = None, base_package: str | None = None, sys_path: list[str] | None = None) -> dict:
    """Run the protocol and write ``<derived_root>/benchmark/results.json`` after every finished group (resumable)."""
    proto = protocol or (reduced_protocol(seeds) if reduced else Protocol(seeds=seeds))
    for p in sys_path or []:
        if p not in sys.path:
            sys.path.insert(0, p)
    if base_package:
        registry.reload(base_package)
    out_path = Path(derived_root) / "benchmark" / "results.json"
    geos = geometries or list(G.GEOMETRIES)
    ids = methods or LADDER
    rows, pareto = _load_done(out_path, proto) if resume else ([], [])
    done = {_group_key(r) for r in rows}
    skipped: list[dict] = []
    tasks: list[dict] = []
    base = {"protocol": asdict(proto), "base_package": base_package, "sys_path": sys_path or []}
    for mid in ids:
        for geo in geos:
            why = skip_reason(mid, geo, proto.reduced)
            if why is not None:
                skipped.append({"method": mid, "geometry": geo, "reason": why})
                continue
            for device in (False, True):
                if device and device_skip_reason(geo):
                    continue
                dkey = "device" if device else "ideal"
                if (mid, geo, dkey, "default") not in done:
                    tasks.append({**base, "method": mid, "geometry": geo, "device": device, "params": "default"})
                # tuned parameters are chosen on the ideal model, so they run on the ideal model only (protocol text)
                if not device and tuning_grid(mid) is not None and (mid, geo, dkey, "tuned") not in done:
                    tasks.append({**base, "method": mid, "geometry": geo, "device": device, "params": "tuned"})

    def flush() -> dict:
        d = document(proto, rows, pareto, skipped)
        tmp = out_path.with_suffix(".tmp")
        write_json(tmp, d)
        os.replace(tmp, out_path)
        return d

    n_workers = max(1, min(int(workers), MAX_WORKERS))

    def absorb(res: dict) -> None:
        nonlocal pareto
        rows.extend(res["rows"])
        if res["pareto"]:
            pareto = [p for p in pareto if p["geometry"] != res["geometry"]] + [
                {"geometry": res["geometry"], "method": "B5", "points": res["pareto"]}]
        flush()

    if n_workers == 1:
        for t in tasks:
            absorb(run_group(t))
    else:
        with ProcessPoolExecutor(max_workers=n_workers) as pool:
            # absorb each group as it finishes, so a slow group never holds back the flush of the others
            for fut in as_completed([pool.submit(run_group, t) for t in tasks]):
                absorb(fut.result())
    return flush()
