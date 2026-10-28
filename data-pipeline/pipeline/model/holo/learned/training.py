"""Training loops of the two slots (offline, GPU; needs the GPU lane). Checkpoints and logs go to the training root, never to
the repository. Everything is seeded: the data stream is ``numpy.random.default_rng(data_seed)``, the network
initialisation ``torch.manual_seed(init_seed)``; the seeds are recorded in the model card.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import torch

from . import generators, nets
from . import torch_forward as tf

WARM_N_PIX = 256
WARM_PAD = 2
CGH_N_PIX = 128


@dataclass
class WarmConfig:
    data_seed: int = 20261101
    init_seed: int = 7
    steps: int = 6000
    batch: int = 8
    lr: float = 8e-4
    unroll: int = 8
    n_fix: int = 12
    max_hours: float = 1.2
    d: int = 64
    layers: int = 2
    heads: int = 4
    ff: int = 128
    dense_bias: float = 0.6   # probability to keep only sets of at least 40 traps (the sparse ones are solved by any start)


@dataclass
class CghConfig:
    data_seed: int = 20261102
    init_seed: int = 11
    steps: int = 20000
    batch: int = 32
    lr: float = 1e-3
    max_hours: float = 1.2
    channels: int = 14


def _log(path: Path, rec: dict) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")


def warm_batch(rng: np.random.Generator, cfg: WarmConfig, device):
    sets = []
    while len(sets) < cfg.batch:
        s = generators.sample_traps(rng, half_field=WARM_N_PIX * WARM_PAD / 2)
        if len(s) < 40 and rng.random() < cfg.dense_bias:
            continue
        sets.append(s)
    t, m = generators.pad_batch(sets)
    return torch.as_tensor(t, device=device), torch.as_tensor(m, device=device)


def warm_loss(theta, traps, mask, cfg: WarmConfig):
    out = tf.unrolled_wgs(theta, traps, mask, WARM_N_PIX, WARM_PAD, cfg.unroll, cfg.n_fix)
    logs = torch.stack([torch.log(s**2 + 0.01) for s, _e in out])   # (K + 1, B)
    wts = torch.ones(len(out), device=theta.device)
    wts[0] = 0.3
    return (logs * wts[:, None]).sum(0).mean() / wts.sum(), out


def train_warmstart(cfg: WarmConfig, run_dir: Path, resume: bool = True) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    dev = torch.device("cuda")
    torch.manual_seed(cfg.init_seed)
    net = nets.SetNet(cfg.d, cfg.heads, cfg.layers, cfg.ff).to(dev)
    opt = torch.optim.AdamW(net.parameters(), lr=cfg.lr, weight_decay=1e-5)
    rng = np.random.default_rng(cfg.data_seed)
    ck = run_dir / "ckpt.pt"
    step = 0
    if resume and ck.is_file():
        st = torch.load(ck, map_location=dev, weights_only=False)
        net.load_state_dict(st["net"]), opt.load_state_dict(st["opt"])
        step, rng.bit_generator.state = st["step"], st["rng"]
    log = run_dir / "log.jsonl"
    t0 = time.time()
    while step < cfg.steps and (time.time() - t0) < cfg.max_hours * 3600:
        lr = cfg.lr * min(1.0, (step + 1) / 300) * 0.5 * (1 + math.cos(math.pi * min(1.0, step / cfg.steps))) + 1e-5
        for g in opt.param_groups:
            g["lr"] = lr
        traps, mask = warm_batch(rng, cfg, dev)
        theta = net(traps, mask)
        loss, out = warm_loss(theta, traps, mask, cfg)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
        opt.step()
        step += 1
        if step % 50 == 0:
            with torch.no_grad():
                rnd = tf.unrolled_wgs(math.pi * (2 * torch.rand_like(theta) - 1), traps, mask, WARM_N_PIX, WARM_PAD, cfg.unroll, cfg.n_fix)
            rec = {"step": step, "loss": float(loss.detach()), "lr": lr, "M": int(traps.shape[1]), "t": round(time.time() - t0),
                   "sig": [round(float(o[0].median()), 3) for o in out[1:]], "sig_random": [round(float(o[0].median()), 3) for o in rnd[1:]],
                   "eff": round(float(out[-1][1].mean()), 3)}
            _log(log, rec)
            if step % 500 == 0:
                print(rec, flush=True)
        if step % 200 == 0:
            torch.save({"net": net.state_dict(), "opt": opt.state_dict(), "step": step, "rng": rng.bit_generator.state, "cfg": asdict(cfg)}, ck)
    torch.save({"net": net.state_dict(), "opt": opt.state_dict(), "step": step, "rng": rng.bit_generator.state, "cfg": asdict(cfg)}, ck)
    return ck


def cgh_batch(rng: np.random.Generator, batch: int, device):
    return torch.as_tensor(np.stack([generators.sample_target(rng) for _ in range(batch)])[:, None], device=device)


def cgh_loss(net, target, amp_in):
    phase = net(target)
    inten = tf.focal_intensity(phase[:, 0], amp_in)
    ac = tf.accuracy(target[:, 0], inten)
    return (1.0 - ac).mean(), ac


def train_cgh(cfg: CghConfig, run_dir: Path, resume: bool = True) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    dev = torch.device("cuda")
    torch.manual_seed(cfg.init_seed)
    net = nets.CghNet(cfg.channels).to(dev)
    opt = torch.optim.AdamW(net.parameters(), lr=cfg.lr, weight_decay=1e-6)
    rng = np.random.default_rng(cfg.data_seed)
    amp_in = tf.input_amplitude(CGH_N_PIX, device=dev)
    ck = run_dir / "ckpt.pt"
    step = 0
    if resume and ck.is_file():
        st = torch.load(ck, map_location=dev, weights_only=False)
        net.load_state_dict(st["net"]), opt.load_state_dict(st["opt"])
        step, rng.bit_generator.state = st["step"], st["rng"]
    log = run_dir / "log.jsonl"
    t0 = time.time()
    while step < cfg.steps and (time.time() - t0) < cfg.max_hours * 3600:
        lr = cfg.lr * 0.5 * (1 + math.cos(math.pi * min(1.0, step / cfg.steps))) + 1e-5
        for g in opt.param_groups:
            g["lr"] = lr
        target = cgh_batch(rng, cfg.batch, dev)
        loss, ac = cgh_loss(net, target, amp_in)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
        opt.step()
        step += 1
        if step % 50 == 0:
            rec = {"step": step, "loss": float(loss.detach()), "ac_median": float(ac.median()), "lr": lr, "t": round(time.time() - t0)}
            _log(log, rec)
            if step % 500 == 0:
                print(rec, flush=True)
        if step % 500 == 0:
            torch.save({"net": net.state_dict(), "opt": opt.state_dict(), "step": step, "rng": rng.bit_generator.state, "cfg": asdict(cfg)}, ck)
    torch.save({"net": net.state_dict(), "opt": opt.state_dict(), "step": step, "rng": rng.bit_generator.state, "cfg": asdict(cfg)}, ck)
    return ck
