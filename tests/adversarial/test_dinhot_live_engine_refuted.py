"""Live-engine requirements LE-001 to LE-011 (docs/design/features/live-engine/): each web test copies the web code, plants the defect in the TypeScript source and runs the requirement's own vitest test, which passes untouched and must fail planted (local-only: needs node and the installed frontend)."""
from __future__ import annotations

import pytest
from planting import NODE, NODE_MODULES
from web_plant import web_refute

needs_web = pytest.mark.skipif(NODE is None or not (NODE_MODULES / "@fasl-work").is_dir(), reason="needs node and `npm ci` in frontend/")


@needs_web
def test_a_stream_off_by_one_bit_fails_the_rng_parity_gate(tmp_path):
    """LE-001: the rotation of the output scrambler is 8 instead of 7: the stream no longer matches the committed reference (local-only: needs node and `npm ci` in frontend/, which the checks job does not install; the CI web job runs the same vitest suite)"""
    web_refute(tmp_path, 'frontend/src/engine/holo/core.parity.test.ts', 'reproduces the committed rng-reference.json stream', [
        ('src/engine/holo/rng.ts', 'const rot = ((x << 7) | (x >>> 25)) >>> 0;', 'const rot = ((x << 8) | (x >>> 24)) >>> 0;'),
    ])


@needs_web
def test_a_focal_field_that_loses_parseval_fails_the_forward_parity_gate(tmp_path):
    """LE-002: the orthonormal scale of the focal FFT is multiplied by 1.01: the parity and Parseval assertions fail (local-only: needs node and `npm ci` in frontend/, which the checks job does not install; the CI web job runs the same vitest suite)"""
    web_refute(tmp_path, 'frontend/src/engine/holo/core.parity.test.ts', 'fft_focal_field (orthonormal, Parseval, pad 2 and 3)', [
        ('src/engine/holo/forward.ts', 'const s = 1 / m; // orthonormal', 'const s = 1.01 / m; // orthonormal'),
    ])


@needs_web
def test_a_quantizer_that_floors_fails_the_device_parity_gate(tmp_path):
    """LE-003: the quantizer floors instead of rounding to the nearest level: the levels differ from the Python fixture (local-only: needs node and `npm ci` in frontend/, which the checks job does not install; the CI web job runs the same vitest suite)"""
    web_refute(tmp_path, 'frontend/src/engine/holo/device.parity.test.ts', 'quantize: levels exact, phase to 1e-12', [
        ('src/engine/holo/device.ts', '* levels + 0.5)', '* levels + 0.0)'),
    ])


@needs_web
def test_a_port_list_that_drops_a_live_method_fails_the_lane_gate(tmp_path):
    """LE-004: the first ported method is dropped from the list: the list no longer equals the live methods of the registry (local-only: needs node and `npm ci` in frontend/, which the checks job does not install; the CI web job runs the same vitest suite)"""
    web_refute(tmp_path, 'frontend/src/engine/holo/methods.parity.test.ts', 'lists exactly the methods whose Python lane is live or both', [
        ('src/engine/holo/methods/index.ts', 'ALL.map((m) => m.spec.id);\n\nexport const liveSpecs', 'ALL.slice(1).map((m) => m.spec.id);\n\nexport const liveSpecs'),
    ])


@needs_web
def test_a_silent_fallback_for_a_baked_method_fails_the_notlive_gate(tmp_path):
    """LE-005: `getMethod` is changed to answer M06 for an unknown id: the NotLive assertions fail (local-only: needs node and `npm ci` in frontend/, which the checks job does not install; the CI web job runs the same vitest suite)"""
    web_refute(tmp_path, 'frontend/src/engine/holo/methods.parity.test.ts', 'raises NotLive (never a silent fallback) for a baked-only or unknown method', [
        ('src/engine/holo/methods/index.ts', 'if (!m) throw new NotLive(id);', "if (!m) return BY_ID.get('M06')!;"),
    ])


@needs_web
def test_a_notlive_that_loses_its_type_at_the_worker_boundary_fails_the_client_gate(tmp_path):
    """LE-006: the client no longer maps the error name `NotLive` back: the caller receives a plain error and the instance assertion fails (local-only: needs node and `npm ci` in frontend/, which the checks job does not install; the CI web job runs the same vitest suite)"""
    web_refute(tmp_path, 'frontend/src/engine/holo/worker.test.ts', 'rejects a method that is not ported with NotLive, never a fallback', [
        ('src/engine/holo/client.ts', "if (name === 'NotLive') {", "if (name === 'NotLive_') {"),
    ])


@needs_web
def test_a_cancel_that_is_ignored_fails_the_cancellation_gate(tmp_path):
    """LE-007: the cancel handler no longer marks the run as cancelled: the run goes on to its last iteration and the assertion fails (local-only: needs node and `npm ci` in frontend/, which the checks job does not install; the CI web job runs the same vitest suite)"""
    web_refute(tmp_path, 'frontend/src/engine/holo/worker.test.ts', 'cancel stops the run within one iteration', [
        ('src/engine/holo/runner.ts', 'if (this.current) this.current.cancelled = true;', 'if (this.current) this.current.cancelled = false;'),
    ])


@needs_web
def test_a_loop_that_never_yields_fails_the_event_loop_gate(tmp_path):
    """LE-008: the yield after each iteration is removed: no message is seen between iterations and the assertion fails (local-only: needs node and `npm ci` in frontend/, which the checks job does not install; the CI web job runs the same vitest suite)"""
    web_refute(tmp_path, 'frontend/src/engine/holo/worker.test.ts', 'yields to the event loop after every iteration (so a message can be seen between iterations)', [
        ('src/engine/holo/runner.ts', 'await this.sched.yield(); // after every iteration', '// await this.sched.yield(); // after every iteration'),
    ])


@needs_web
def test_a_progress_stream_without_a_rate_limit_fails_the_progress_gate(tmp_path):
    """LE-009: the rate limit of the progress messages is removed: every iteration posts one and the count exceeds 30 per second and the assertion fails (local-only: needs node and `npm ci` in frontend/, which the checks job does not install; the CI web job runs the same vitest suite)"""
    web_refute(tmp_path, 'frontend/src/engine/holo/worker.test.ts', 'runs a case: progress at most 30 per second, a final result with the shapes of the contract', [
        ('src/engine/holo/runner.ts', 'if (!force && t - state.last < PROGRESS_MIN_GAP_MS) return;', 'if (false as boolean) return;'),
    ])


@needs_web
def test_a_silent_cpu_fallback_fails_the_reason_gate(tmp_path):
    """LE-010: the reason is dropped from the result: `fallbackReason` is null though the GPU was wanted and the assertion fails (local-only: needs node and `npm ci` in frontend/, which the checks job does not install; the CI web job runs the same vitest suite)"""
    web_refute(tmp_path, 'frontend/src/engine/holo/worker.test.ts', 'runs a case: progress at most 30 per second, a final result with the shapes of the contract', [
        ('src/engine/holo/runner.ts', "fallbackReason: want === 'cpu' ? null : reason,", 'fallbackReason: null,'),
    ])
