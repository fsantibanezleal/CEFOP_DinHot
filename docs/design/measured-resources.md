# Measured resources and the numbers of the example

The committed evidence behind the numbers that [`SDD.md`](SDD.md) and the example's technical view state in the Lanes, the
Resources and the Deploy driver. The example's executive view (`content/executive.json`) states none of them: it frames
a problem space with sourced industry figures only. Measured on 2026-10-12 on the development workstation (Windows 11, Python 3.13, Node
24.14.1) on a `git archive` copy of the release branch, so that nothing of the working tree was touched. A product
measures its own and replaces this record. Sizes are bytes of file content unless a line says "on disk" (allocated
blocks, which is what `du -sk` reports and is larger).

## Stored size of the committed artifacts

```
$ find data/derived -type f | xargs du -cb | tail -1
35145	total
$ find data/derived -type f | wc -l
14
$ du -sk data/derived | cut -f1
112
```

The artifacts hold 35,145 bytes in 14 files (34.3 KiB). The 112 is kilobytes allocated on disk, not content. The
SDD says 35 KB.

## The bake: time and memory

A throwaway root, so the committed artifacts stay as they are. The script prints the wall time of `run_all` (five
cases, the released surrogate) and the peak working set of the process (`GetProcessMemoryInfo`).

```python
"""Bake all five cases into a throwaway root and print the wall time, the peak working set and the bytes written."""
import ctypes
import ctypes.wintypes as wt
import sys
import time
from pathlib import Path

sys.path.insert(0, "data-pipeline")
from pipeline import pipeline  # noqa: E402


class Counters(ctypes.Structure):
    _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t)]


out = Path(sys.argv[1])
start = time.perf_counter()
entries = pipeline.run_all(seed=42, output_root=out)
elapsed = time.perf_counter() - start
c = Counters()
c.cb = ctypes.sizeof(c)
kernel = ctypes.windll.kernel32
psapi = ctypes.windll.psapi
kernel.GetCurrentProcess.restype = wt.HANDLE
psapi.GetProcessMemoryInfo.argtypes = [wt.HANDLE, ctypes.POINTER(Counters), wt.DWORD]
psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(c), c.cb)
size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
print(f"cases={len(entries)} seconds={elapsed:.3f} peak_working_set_mb={c.PeakWorkingSetSize / 1048576:.1f} bytes_written={size}")
```

```
$ python measure_bake.py <a throwaway directory>      (three runs, the directory emptied before each)
cases=5 seconds=0.083 peak_working_set_mb=32.9 bytes_written=35293
cases=5 seconds=0.138 peak_working_set_mb=33.0 bytes_written=35293
cases=5 seconds=0.132 peak_working_set_mb=33.1 bytes_written=35293
```

So the bake of five cases takes 0.1 s (0.08 to 0.14 s) and peaks at 33 MB. The SDD says 0.1 s and 33 MB.

## The live engine: median time of one run

`frontend/src/engine/sir.ts` run by Node 24 on the parameters of each committed manifest, 2000 timed runs after 200
warm-up runs (`node bench_live.mjs` from the repository root; Node strips the types itself).

```js
// Median wall time of one live run (frontend/src/engine/sir.ts) for each committed case, 2000 timed runs after 200 warm-up runs.
import { readFileSync, readdirSync } from 'node:fs';
import { simulate } from './frontend/src/engine/sir.ts';

const dir = 'data/derived/manifests';
for (const f of readdirSync(dir).filter((n) => n.endsWith('.json') && n !== 'index.json').sort()) {
  const m = JSON.parse(readFileSync(`${dir}/${f}`, 'utf8'));
  const p = m.params;
  for (let i = 0; i < 200; i++) simulate(p);
  const times = [];
  for (let i = 0; i < 2000; i++) {
    const t = performance.now();
    simulate(p);
    times.push(performance.now() - t);
  }
  times.sort((a, b) => a - b);
  console.log(`${m.case_id} median_ms=${times[1000].toFixed(4)} p95_ms=${times[1900].toFixed(4)} budget_ms=${m.gate.run_ms_budget}`);
}
console.log(`node ${process.version}`);
```

```
CTRL_degenerate median_ms=0.0055 p95_ms=0.0199 budget_ms=1500
EX01_subcritical median_ms=0.0090 p95_ms=0.0224 budget_ms=1500
EX02_epidemic median_ms=0.0096 p95_ms=0.0121 budget_ms=1500
EX03_fast_burn median_ms=0.0090 p95_ms=0.0113 budget_ms=1500
EX04_slow_spread median_ms=0.0090 p95_ms=0.0115 budget_ms=1500
node v24.14.1
```

The medians are 0.006 to 0.010 ms per run, against the run budget of 1500 ms that every manifest carries
(`gate.run_ms_budget`, set by `data-pipeline/pipeline/core/gate.py`). The SDD of 2026-10-04 said 0.02 to 0.08 ms; this
measurement replaces it.

## The site: build and deploy payload

`npm ci` then `npm run build` in `frontend/` (87 packages added in 2 min with a cold cache; Vite reports the bundle
built in 4.72 s).

```
$ find dist -type f | xargs du -cb | tail -1
1917973	total
$ find dist -type f | wc -l
83
$ find dist -path '*data*' -type f | xargs du -cb | tail -1      (the artifacts the site serves)
35145	total
$ find dist -type f -not -path '*data*' | xargs du -cb | tail -1  (the site itself)
1882828	total
$ find dist -name '*.woff*' -o -name '*.ttf' | xargs du -cb | tail -1   (the KaTeX fonts)
1072948	total
$ du -sk dist | cut -f1                                           (allocated on disk)
2274
```

The deploy payload is the whole of `frontend/dist`: 1,917,973 bytes (1.9 MB) in 83 files, made of 1,882,828 bytes of
site files (1.88 MB, 1.07 MB of them KaTeX fonts) and 35,145 bytes of artifacts (35 KB, the same bytes as
`data/derived`). The 2.2 MB the SDD used to state is the allocation on disk (2274 KB), not the payload that is uploaded.

## The numbers of the example's technical view that come from committed files

- Epidemic case: `data/derived/manifests/EX02_epidemic.json` holds `beta 0.55`, `gamma 0.2`, `N 100000.0`, so the
  reproduction number is 0.55 / 0.2 = 2.75 for 100000 people; `data/derived/EX02_epidemic/trace.json` holds
  `peak_I 27345.24` and `t_peak 24.25` (27345 people on day 24.25).
- Fast-burn case: `data/derived/manifests/EX03_fast_burn.json` holds `beta 1.2`, `gamma 0.2` (a reproduction number
  of 6); `data/derived/EX03_fast_burn/trace.json` holds `t_peak 9.25`.
- Herd threshold: computed as 1 - 1/2.75 = 0.636 from the relation of the cited work
  (https://doi.org/10.1007/BF00178324 defines the basic reproduction ratio); the paper does not state 63.6 itself.
- Held-out error of the fast approximation: `data/derived/manifests/EX02_epidemic.json` holds
  `surrogate_peakfrac_rmse 0.00732` and `n_holdout 20`.
- Run budget: `gate.run_ms_budget 1500.0` in each manifest.
