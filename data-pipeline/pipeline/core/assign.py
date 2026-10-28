"""Rectangular assignment by the Hungarian method (Kuhn 1955, Munkres 1957, in the shortest-augmenting-path form of Jonker and
Volgenant 1987), O(n^2 m). Used by the rearrangement driver: empty target sites (rows) to surplus atoms (columns), cost
``d^alpha`` (Lee, Kim and Ahn 2017, https://doi.org/10.1103/PhysRevA.95.053424: alpha above 1 avoids crossing moves).

Standard library only. ``tests/bake/test_assign.py`` checks it against brute force.
"""
from __future__ import annotations

import math


def assign(cost: list[list[float]]) -> list[int]:
    """For an ``n x m`` cost matrix with ``n <= m``, the column assigned to each row in a minimum-cost matching."""
    n = len(cost)
    m = len(cost[0]) if n else 0
    if n > m:
        raise ValueError(f"need at most as many rows as columns, got {n} x {m}")
    inf = math.inf
    u, v = [0.0] * (n + 1), [0.0] * (m + 1)
    p, way = [0] * (m + 1), [0] * (m + 1)
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv, used = [inf] * (m + 1), [False] * (m + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], inf, 0
            for j in range(1, m + 1):
                if not used[j]:
                    cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j], way[j] = cur, j0
                    if minv[j] < delta:
                        delta, j1 = minv[j], j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
    out = [0] * n
    for j in range(1, m + 1):
        if p[j]:
            out[p[j] - 1] = j - 1
    return out
