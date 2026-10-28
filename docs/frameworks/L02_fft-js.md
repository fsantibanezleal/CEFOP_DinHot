# L02, fft.js (the FFT of the live engine)

## What and why

fft.js 4.0.4 is the Float64 radix-4 FFT of the TypeScript engine, the browser counterpart of `numpy.fft` in [L01](L01_numpy.md). It was chosen by measurement: 34.9 ms for a 1024 by 1024 complex 2D transform in Node 24, and in
Chromium 156 (Playwright, an Intel Core i9-14900HX workstation) 7.9 to 19.7 ms at 512 by 512 and 32.6 to 79.0 ms at 1024 by 1024, one weighted GS iteration at 512 by 512 in 27.9 to 58.8 ms (the factor of about 2 between the
two headless modes was measured and not explained). Alternatives not adopted: `kissfft-wasm` and `webfft`, because no measured gain was recorded and a WebAssembly build adds a binary to the site.

## Install (exact, verified)

Pinned exactly at 4.0.4 in the frontend package manifest (`npm ci` in `frontend/`), with its types declared in a local declaration file of the engine. The pin is the SDD technology table's, held to the manifest by
`scripts/check_tech_matrix.py`.

## Usage

The 2D transform is rows then columns on `Float64Array` scratch rows, with an explicit gather and scatter for the columns (their cost is included in the timings above). The engine applies the same centring and orthonormal scaling
as the Python engine, so that the focal field of the browser equals the focal field of the pipeline to the stated parity tolerance.

## Applying it here

The live methods (those whose `SPEC.lane` includes live, see [the method interface](../architecture/09_method-interface-and-registry.md)) and the device model call it for the forward and inverse transforms; the Web Worker runs it off the interface thread. The optional WebGPU backend is
a float32 Stockham radix-2 kernel measured at 2.3 ms for the 512 by 512 transform on an integrated GPU, with the CPU path as the fallback ([the live lane](../architecture/04_live-lane.md)).

## Caveats and licence

- Float64 on the CPU path against float32 on the WebGPU path: the two agree to a stated tolerance (1.7e-5 to 2.9e-5 of the maximum value was measured), and the GPU path is disabled when it disagrees.
- Timings are one machine and ranges, not a portable claim. The licence of fft.js is MIT (as recorded when it was chosen); see [ATTRIBUTION](../../ATTRIBUTION.md).
