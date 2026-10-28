"""The two networks. Both are written with operators that onnxruntime-web's WASM provider and the WebGL table share (Conv,
ConvTranspose, MatMul, Gemm, Add, Mul, Relu, Softmax, Concat, Reshape, Transpose, Sin, Cos, Atan, Where, ...): no
LayerNormalization, no GroupNorm, no DFT, no scaled_dot_product_attention node; the Fourier transform of the cgh-net is a pair
of constant DFT matrices applied with MatMul.

``SetNet`` (warmstart-model): a permutation-equivariant set transformer, one phase per trap. Input ``traps`` (B, M, 4) in
focal bins, Rayleigh ranges and weight; ``mask`` (B, M). Fourier features of the positions let it write the quadratic and
periodic phase laws of regular arrays. Output ``trap_phase`` (B, M) wrapped to (-pi, pi]; padded entries are 0.

``CghNet`` (cgh-net): DeepCGH's image-plane form. A small U-Net maps the target amplitude to a complex field in the focal
plane, a constant inverse DFT carries it to the SLM, and the output is the phase of that field (the SLM amplitude is the
illumination, so only the phase is kept). The U-Net therefore learns the local phase law and the transform does the global
propagation.
"""
from __future__ import annotations

import math

import torch
from torch import nn

POS_SCALE = 128.0      # bins; the inputs are divided by it inside the graph
Z_SCALE = 4.0
FREQS = (1, 2, 4, 8, 16, 32)


def wrap(theta: torch.Tensor) -> torch.Tensor:
    """Wrap to (-pi, pi] with Sin, Cos and Atan (exported as Atan with Where corrections)."""
    return torch.atan2(torch.sin(theta), torch.cos(theta))


class Block(nn.Module):
    def __init__(self, d: int, heads: int, ff: int):
        super().__init__()
        self.h, self.dh = heads, d // heads
        self.qkv = nn.Linear(d, 3 * d)
        self.proj = nn.Linear(d, d)
        self.f1, self.f2 = nn.Linear(d, ff), nn.Linear(ff, d)
        nn.init.zeros_(self.proj.weight), nn.init.zeros_(self.proj.bias)
        nn.init.zeros_(self.f2.weight), nn.init.zeros_(self.f2.bias)

    def forward(self, x, bias):
        b, m, d = x.shape
        q, k, v = self.qkv(x).reshape(b, m, 3, self.h, self.dh).permute(2, 0, 3, 1, 4).unbind(0)
        att = torch.softmax(torch.matmul(q, k.transpose(-1, -2)) * (1.0 / math.sqrt(self.dh)) + bias, dim=-1)
        x = x + self.proj(torch.matmul(att, v).transpose(1, 2).reshape(b, m, d))
        return x + self.f2(torch.relu(self.f1(x)))


class SetNet(nn.Module):
    def __init__(self, d: int = 64, heads: int = 4, layers: int = 2, ff: int = 128):
        super().__init__()
        n_in = 5 + 4 * len(FREQS)
        self.register_buffer("freq", torch.tensor([math.pi * f for f in FREQS], dtype=torch.float32))
        self.embed = nn.Sequential(nn.Linear(n_in, d), nn.ReLU(), nn.Linear(d, d))
        self.blocks = nn.ModuleList(Block(d, heads, ff) for _ in range(layers))
        self.mix = nn.Sequential(nn.Linear(2 * d, d), nn.ReLU(), nn.Linear(d, 1))
        self.chirp = nn.Linear(d, 1)                       # set-dependent coefficient of the quadratic (Fresnel-like) phase law
        self.chirp0 = nn.Parameter(torch.tensor(80.0))
        nn.init.zeros_(self.chirp.weight), nn.init.zeros_(self.chirp.bias)

    def forward(self, traps: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        kx, ky = traps[..., 0:1] / POS_SCALE, traps[..., 1:2] / POS_SCALE
        z, w = traps[..., 2:3] / Z_SCALE, traps[..., 3:4]
        ax, ay = kx * self.freq, ky * self.freq
        r2 = kx * kx + ky * ky
        x = self.embed(torch.cat([kx, ky, z, w - 1.0, r2, torch.sin(ax), torch.cos(ax), torch.sin(ay), torch.cos(ay)], -1))
        bias = ((1.0 - mask) * -1.0e4)[:, None, None, :]
        for blk in self.blocks:
            x = blk(x, bias)
        m3 = mask[..., None]
        g = (x * m3).sum(1, keepdim=True) / (m3.sum(1, keepdim=True) + 1e-6)
        theta = self.mix(torch.cat([x, g.expand_as(x)], -1))[..., 0]
        theta = theta + (self.chirp0 + 20.0 * self.chirp(g)[..., 0]) * r2[..., 0]
        return wrap(theta) * mask


def dft_matrices(n: int):
    k = torch.arange(n, dtype=torch.float64)
    ang = 2 * math.pi * torch.outer(k, k) / n
    return torch.cos(ang).float(), torch.sin(ang).float()


def _conv(i, o, s=1):
    return nn.Sequential(nn.Conv2d(i, o, 3, s, 1), nn.ReLU(), nn.Conv2d(o, o, 3, 1, 1), nn.ReLU())


class CghNet(nn.Module):
    """Input ``target`` (B, 1, 128, 128) unit-energy amplitude; output ``phase`` (B, 1, 128, 128) in (-pi, pi]."""

    def __init__(self, c: int = 16):
        super().__init__()
        self.e1, self.e2, self.e3, self.e4 = _conv(3, c), _conv(c, 2 * c, 2), _conv(2 * c, 4 * c, 2), _conv(4 * c, 8 * c, 2)
        self.mid = _conv(8 * c, 8 * c, 2)
        self.u4 = nn.ConvTranspose2d(8 * c, 8 * c, 2, 2)
        self.d4 = _conv(16 * c, 8 * c)
        self.u3 = nn.ConvTranspose2d(8 * c, 4 * c, 2, 2)
        self.d3 = _conv(8 * c, 4 * c)
        self.u2 = nn.ConvTranspose2d(4 * c, 2 * c, 2, 2)
        self.d2 = _conv(4 * c, 2 * c)
        self.u1 = nn.ConvTranspose2d(2 * c, c, 2, 2)
        self.d1 = _conv(2 * c, c)
        self.head = nn.Conv2d(c, 2, 1)
        lin = torch.linspace(-1.0, 1.0, 128)
        self.register_buffer("coords", torch.stack(torch.meshgrid(lin, lin, indexing="ij")[::-1])[None])
        cm, sm = dft_matrices(128)
        self.register_buffer("cm", cm)
        self.register_buffer("sm", sm)
        idx = torch.arange(128)
        self.register_buffer("checker", (1.0 - 2.0 * ((idx[:, None] + idx[None, :]) % 2).float())[None, None])

    def focal_field(self, target):
        x = torch.cat([target * 16.0, self.coords.expand(target.shape[0], -1, -1, -1)], 1)   # unit energy: amplitudes ~ 1/16
        e1 = self.e1(x)
        e2 = self.e2(e1)
        e3 = self.e3(e2)
        e4 = self.e4(e3)
        m = self.mid(e4)
        d = self.d4(torch.cat([self.u4(m), e4], 1))
        d = self.d3(torch.cat([self.u3(d), e3], 1))
        d = self.d2(torch.cat([self.u2(d), e2], 1))
        d = self.d1(torch.cat([self.u1(d), e1], 1))
        return self.head(d)   # (B, 2, 128, 128): real and imaginary parts of the focal field

    def forward(self, target: torch.Tensor) -> torch.Tensor:
        f = self.focal_field(target)
        fr, fi = f[:, 0:1], f[:, 1:2]
        # inverse DFT along both axes: W = C + i S (S sign for the +i kernel), field = W f W
        def left(ar, ai):   # W @ (ar + i ai)
            return torch.matmul(self.cm, ar) - torch.matmul(self.sm, ai), torch.matmul(self.cm, ai) + torch.matmul(self.sm, ar)

        def right(ar, ai):  # (ar + i ai) @ W
            return torch.matmul(ar, self.cm) - torch.matmul(ai, self.sm), torch.matmul(ai, self.cm) + torch.matmul(ar, self.sm)

        ar, ai = left(fr, fi)
        sr, si = right(ar, ai)
        return torch.atan2(si * self.checker, sr * self.checker)   # the checkerboard is the ifftshift of the centred focal grid


def param_count(m: nn.Module) -> int:
    return sum(p.numel() for p in m.parameters())
