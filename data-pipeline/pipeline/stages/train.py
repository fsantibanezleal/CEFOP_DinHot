"""Stage 3, train (OFFLINE, GPU lane): train and release one of the two learned model slots.

    .venv-gpu/Scripts/python.exe -m pipeline.stages.train --slot cgh-net|warmstart-model [--run-dir ...] [--export-only]

Training never runs in CI (ADR-0069, ADR-0074). The run directory (checkpoints, logs) is in the training root, the datasets
(held-out files) in the data root; only the final ONNX graph, its card and the training record are written into the repository:
``models/<stem>.onnx`` + ``models/<stem>.json`` and ``data/derived/models/<slot>-training.json``. ``release`` exports a trained
checkpoint, measures the parity of the graph with torch, checks the operator list and writes the card.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ..io.contract import REPO_ROOT

TRAINING_ENV = "DINHOT_TRAINING_DIR"   # <training root>/dinhot on the training device
SLOTS = ("cgh-net", "warmstart-model")


def card_texts(slot: str, ck: dict, held_hash: str, held_n: int) -> tuple[dict, dict]:
    c, step = ck["cfg"], ck["step"]
    if slot == "cgh-net":
        en = (f"{step} steps of batch {c['batch']} on three-plane targets drawn on the fly from a seeded generator (data seed {c['data_seed']}, "
              f"initialisation seed {c['init_seed']}): point voxels at integer bins, equal counts per plane, random sets, shifted lattices, rings, "
              f"mixed; planes at -8, 0, +8 SLM-limited Rayleigh ranges on the 128 x 128 focal crop (SLM 128 x 128, padding 1). Unsupervised: the "
              f"loss is 1 - AC, the mean over the planes, through the differentiable FFT model with the plane lens phases.")
        es = (f"{step} pasos de lote {c['batch']} con objetivos de tres planos generados al vuelo por un generador con semilla (semilla de datos "
              f"{c['data_seed']}, semilla de inicializacion {c['init_seed']}): voxeles puntuales en bins enteros, igual numero por plano, conjuntos "
              f"aleatorios, redes desplazadas, anillos, mezclas; planos en -8, 0, +8 rangos de Rayleigh limitados por el SLM en el recorte focal de "
              f"128 x 128 (SLM de 128 x 128, relleno 1). Sin supervision: la perdida es 1 - AC, promedio sobre los planos, a traves del modelo FFT "
              f"diferenciable con las fases de lente de cada plano.")
        what_en, what_es = "volumes", "volumenes reservados"
    else:
        en = (f"{step} steps of batch {c['batch']} on trap sets drawn on the fly from a seeded generator (data seed {c['data_seed']}, "
              f"initialisation seed {c['init_seed']}): square and hexagonal lattices, rings, random sets with a minimum spacing, 3D stacks, up "
              f"to 1024 traps, SLM 256 x 256 padding 2, no quasi-periodic sets. Unsupervised: the loss is the log relative standard deviation "
              f"along {c['unroll']} unrolled phase-fixed WGS iterations.")
        es = (f"{step} pasos de lote {c['batch']} con conjuntos de trampas generados al vuelo por un generador con semilla (semilla de "
              f"datos {c['data_seed']}, semilla de inicializacion {c['init_seed']}): redes cuadradas y hexagonales, anillos, conjuntos aleatorios "
              f"con separacion minima, pilas 3D, hasta 1024 trampas, SLM de 256 x 256 relleno 2, sin conjuntos cuasiperiodicos. Sin supervision: "
              f"la perdida es el logaritmo de la desviacion estandar relativa a lo largo de {c['unroll']} iteraciones WGS con fase fija desenrolladas.")
        what_en, what_es = "geometries", "geometrias reservadas"
    ho_en = (f"{held_n} held-out {what_en}, written before training with other seeds (file sha256 {held_hash}); they include the "
             f"benchmark geometries.")
    ho_es = (f"{held_n} {what_es}, escritos antes del entrenamiento con otras semillas (sha256 del archivo {held_hash}); incluyen las "
             f"geometrias del banco de pruebas.")
    return {"en": en, "es": es}, {"en": ho_en, "es": ho_es}


def release(slot: str, run_dir: Path, repo_root: Path = REPO_ROOT) -> dict:
    """Export the checkpoint of ``run_dir`` into ``repo_root/models`` with its card; returns the training record."""
    import numpy as np
    import torch

    from ..model.holo.learned import export, generators, heldout, nets
    ck = torch.load(run_dir / "ckpt.pt", map_location="cpu", weights_only=False)
    c = ck["cfg"]
    out = repo_root / "models" / f"{export.SLOT_STEM[slot]}.onnx"
    out.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(5)
    if slot == "cgh-net":
        net = nets.CghVolNet(c["channels"])
        net.load_state_dict(ck["net"])
        export.export_cgh(net, out)
        probes = [(generators.sample_volume(rng)[0][None],) for _ in range(8)]
        held = heldout.learned_root() / "cgh-vol-heldout.npz"
        n = len(heldout.load_cgh_vol(held)[1])
    else:
        net = nets.SetNet(c["d"], c["heads"], c["layers"], c["ff"])
        net.load_state_dict(ck["net"])
        export.export_warm(net, out)
        probes = [generators.pad_batch([generators.sample_traps(rng)], 1024) for _ in range(8)]
        held = heldout.learned_root() / "warmstart-heldout.npz"
        gen, bench = heldout.load_warm(held)
        n = len(gen) + len(bench)
    bad = export.check_ops(out)
    if bad:
        raise RuntimeError(f"operators outside the web-safe list: {sorted(bad)}")
    err = export.parity_stats(net, out, probes)
    inten = export.intensity_parity(net, out, probes) if slot == "cgh-net" else None
    trained_on, held_out = card_texts(slot, ck, heldout.sha256_file(held), n)
    if inten is not None:
        trained_on = {"en": trained_on["en"] + f" ONNX parity with torch is stated on the reconstructed plane intensities (max |dI| / max I over the planes = {inten:.2e}), "
                      f"not on the phase, which is ill-conditioned where the SLM field is near zero.",
                      "es": trained_on["es"] + f" La paridad ONNX con torch se declara sobre las intensidades de plano reconstruidas (max |dI| / max I = {inten:.2e}), "
                      f"no sobre la fase, mal condicionada donde el campo del SLM es casi nulo."}
    card = export.write_card(slot, out, repo_root, trained_on, held_out)
    rec = {"slot": slot, "config": c, "steps": ck["step"], "onnx_bytes": card["bytes"], "opset": card["opset"],
           "operators": sorted(export.onnx_ops(out)), "parity_wrapped_abs_diff": err, "parity_intensity_rel_max": inten, "heldout_sha256": heldout.sha256_file(held)}
    export.dump(rec, repo_root / "data" / "derived" / "models" / f"{slot}-training.json")
    return rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--slot", required=True, choices=SLOTS)
    ap.add_argument("--run-dir", type=Path, default=None)
    ap.add_argument("--steps", type=int, default=None)
    ap.add_argument("--unroll", type=int, default=None)
    ap.add_argument("--export-only", action="store_true", help="skip training, release the checkpoint in the run directory")
    a = ap.parse_args(argv)
    if a.run_dir is None and not os.environ.get(TRAINING_ENV):
        ap.error(f"give --run-dir or set {TRAINING_ENV}")
    run_dir = a.run_dir or Path(os.environ[TRAINING_ENV]) / a.slot
    if not a.export_only:
        from ..model.holo.learned import training
        if a.slot == "cgh-net":
            training.train_cgh_vol(training.CghVolConfig(**({"steps": a.steps} if a.steps else {})), run_dir)
        else:
            kw = {k: v for k, v in (("steps", a.steps), ("unroll", a.unroll)) if v}
            training.train_warmstart(training.WarmConfig(**kw), run_dir)
    print(json.dumps(release(a.slot, run_dir), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
