"""ONNX export, parity check, operator check and model-card writing of the two slots (needs the GPU lane: torch, onnx,
onnxruntime). The released files are ``models/cgh-net.onnx`` + ``models/cgh-net.json`` and ``models/warmstart.onnx`` +
``models/warmstart.json`` (catalog rows ``cgh-net`` and ``warmstart-model``).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import torch

from ....io.formats import write_json
from . import nets

OPSET = 17
from .webops import WEB_SAFE_OPS  # noqa: E402
SLOT_STEM = {"cgh-net": "cgh-net", "warmstart-model": "warmstart"}


def onnx_ops(path: Path) -> set[str]:
    return {n.op_type for n in onnx.load(str(path)).graph.node}


def check_ops(path: Path) -> set[str]:
    """The operators of the graph that are not in ``WEB_SAFE_OPS`` (empty when the graph is web-safe)."""
    return onnx_ops(path) - WEB_SAFE_OPS


def export_cgh(net: nets.CghNet, path: Path) -> None:
    net = net.eval().cpu()
    torch.onnx.export(net, (torch.zeros(1, 1, 128, 128),), str(path), input_names=["target"], output_names=["phase"],
                      opset_version=OPSET, dynamo=False)


def export_warm(net: nets.SetNet, path: Path) -> None:
    net = net.eval().cpu()
    torch.onnx.export(net, (torch.zeros(1, 1024, 4), torch.ones(1, 1024)), str(path), input_names=["traps", "mask"],
                      output_names=["trap_phase"], opset_version=OPSET, dynamo=False)


def session(path: Path) -> ort.InferenceSession:
    so = ort.SessionOptions()
    so.intra_op_num_threads = 1
    return ort.InferenceSession(str(path), so, providers=["CPUExecutionProvider"])


def wrapped_diff(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    d = np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    return np.abs(np.arctan2(np.sin(d), np.cos(d)))


def parity_stats(net: torch.nn.Module, path: Path, inputs: list[tuple[np.ndarray, ...]]) -> dict:
    """Wrapped absolute difference between torch (CPU) and onnxruntime outputs over ``inputs``: the maximum, the 99.9th
    percentile and the share of entries above 1e-5."""
    net = net.eval().cpu()
    sess = session(path)
    names = [i.name for i in sess.get_inputs()]
    diffs = []
    for arrs in inputs:
        with torch.no_grad():
            ref = net(*[torch.as_tensor(a) for a in arrs]).numpy()
        got = sess.run(None, dict(zip(names, arrs)))[0]
        diffs.append(wrapped_diff(ref, got).ravel())
    d = np.concatenate(diffs)
    return {"max": float(d.max()), "p999": float(np.percentile(d, 99.9)), "share_above_1e-5": float(np.mean(d > 1e-5))}


def parity(net: torch.nn.Module, path: Path, inputs: list[tuple[np.ndarray, ...]]) -> float:
    """Largest wrapped absolute difference between torch (CPU) and onnxruntime outputs over ``inputs``."""
    return parity_stats(net, path, inputs)["max"]


def intensity_parity(net: torch.nn.Module, path: Path, inputs: list[tuple[np.ndarray, ...]]) -> float:
    """cgh-net parity on the reconstructed focal intensity: the largest ``max|I_torch - I_onnx| / max(I_torch)`` over ``inputs``,
    with ``I`` the unit-sum focal intensity of the phase mask. The phase itself is ill-conditioned where the SLM field is near zero
    (atan2), the intensity the mask makes is not."""
    from . import torch_forward as tf
    net = net.eval().cpu()
    sess = session(path)
    amp = tf.input_amplitude(128)
    worst = 0.0
    for (a,) in inputs:
        with torch.no_grad():
            p_t = net(torch.as_tensor(a))
        p_o = torch.as_tensor(sess.run(None, {"target": a})[0])
        i_t, i_o = tf.focal_intensity(p_t[:, 0], amp), tf.focal_intensity(p_o[:, 0], amp)
        worst = max(worst, float((i_t - i_o).abs().max() / i_t.max()))
    return worst


def io_spec(path: Path) -> tuple[list[dict], list[dict]]:
    m = onnx.load(str(path))

    def one(v):
        dims = [d.dim_value for d in v.type.tensor_type.shape.dim]
        return {"name": v.name, "shape": dims, "dtype": "float32"}

    return [one(v) for v in m.graph.input], [one(v) for v in m.graph.output]


def sha256_bytes(path: Path) -> tuple[str, int]:
    data = Path(path).read_bytes()
    return hashlib.sha256(data).hexdigest(), len(data)


def write_card(slot: str, onnx_path: Path, repo_root: Path, trained_on: dict, held_out: dict) -> dict:
    """Write ``models/<stem>.json`` for the graph at ``onnx_path`` (already under ``repo_root/models``)."""
    ins, outs = io_spec(onnx_path)
    sha, nbytes = sha256_bytes(onnx_path)
    card = {
        "schema": "dinhot.model-card/v1", "slot": slot, "onnx": f"models/{onnx_path.name}", "sha256": sha, "bytes": nbytes,
        "opset": OPSET, "inputs": ins, "outputs": outs, "trained_on": trained_on, "held_out": held_out,
        "metrics_path": "data/derived/models/metrics.json",
    }
    if slot == "cgh-net":
        card["grid"] = 128
    write_json(repo_root / "models" / f"{SLOT_STEM[slot]}.json", card)
    return card


def dump(obj, path: Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
