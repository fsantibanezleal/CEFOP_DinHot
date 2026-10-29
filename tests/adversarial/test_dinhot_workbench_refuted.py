"""Workbench requirements WK-001 to WK-010 (docs/design/features/workbench/): each web test copies the web code, plants the defect in the TypeScript source and runs the requirement's own vitest test, which passes untouched and must fail planted (local-only: needs node and the installed frontend)."""
from __future__ import annotations

import pytest
from planting import NODE, NODE_MODULES
from web_plant import web_refute

needs_web = pytest.mark.skipif(NODE is None or not (NODE_MODULES / "@fasl-work").is_dir(), reason="needs node and `npm ci` in frontend/")


@needs_web
def test_an_editor_that_accepts_a_trap_at_the_field_edge_fails_the_field_gate(tmp_path):
    """WK-001: the comparison is relaxed from at-or-beyond to beyond: a trap on the bound is accepted and the assertion fails (local-only: needs node and `npm ci` in frontend/, which the checks job does not install; the CI web job runs the same vitest suite)"""
    web_refute(tmp_path, 'frontend/src/workbench/traps.test.ts', 'accepts a trap strictly inside and names the bound for one at or beyond it, in both languages', [
        ('src/workbench/traps.ts', 'Math.abs(t[axis]) >= halfFieldUm', 'Math.abs(t[axis]) > halfFieldUm'),
    ])


@needs_web
def test_an_editor_that_deletes_the_last_trap_fails_the_target_gate(tmp_path):
    """WK-002: the guard on the last trap is removed: the list is emptied and the assertion fails (local-only: needs node and `npm ci` in frontend/, which the checks job does not install; the CI web job runs the same vitest suite)"""
    web_refute(tmp_path, 'frontend/src/workbench/traps.test.ts', 'deletes a trap but never the last one (a target needs at least one trap)', [
        ('src/workbench/traps.ts', 'if (traps.length <= 1) {', 'if (traps.length <= 0) {'),
    ])


@needs_web
def test_an_editor_without_the_contract_limit_fails_the_size_gate(tmp_path):
    """WK-003: the limit is raised out of reach: a 4097th trap is accepted and the assertion fails (local-only: needs node and `npm ci` in frontend/, which the checks job does not install; the CI web job runs the same vitest suite)"""
    web_refute(tmp_path, 'frontend/src/workbench/traps.test.ts', 'refuses a list longer than the contract allows', [
        ('src/workbench/traps.ts', 'if (traps.length >= MAX_TRAPS) {', 'if (traps.length >= 1e9) {'),
    ])


@needs_web
def test_a_fill_factor_law_off_by_a_power_fails_the_device_view_gate(tmp_path):
    """WK-004: the fill-factor efficiency is changed from f squared to f: the closed-form assertions fail (local-only: needs node and `npm ci` in frontend/, which the checks job does not install; the CI web job runs the same vitest suite)"""
    web_refute(tmp_path, 'frontend/src/workbench/decode.test.ts', 'the closed forms match the sources: sinc^2(1/N) gives 0.405 for N = 2 and 0.684 for N = 3, f^2 for the fill factor', [
        ('src/workbench/decode.ts', '(fill: number): number => fill * fill;', '(fill: number): number => fill;'),
    ])


@needs_web
def test_a_quantizer_that_floors_fails_the_displayed_phase_gate(tmp_path):
    """WK-005: the level is taken by flooring instead of rounding to the nearest: the nearest-level assertion fails (local-only: needs node and `npm ci` in frontend/, which the checks job does not install; the CI web job runs the same vitest suite)"""
    web_refute(tmp_path, 'frontend/src/workbench/decode.test.ts', 'quantizes to the nearest of 2^b levels and reports the level', [
        ('src/workbench/decode.ts', '* levels + 0.5) % levels;', '* levels + 0.0) % levels;'),
    ])


@needs_web
def test_a_mask_that_does_not_cover_the_crop_fails_the_decode_gate(tmp_path):
    """WK-006: the coverage check is removed: a short mask is accepted and the refusal assertion fails (local-only: needs node and `npm ci` in frontend/, which the checks job does not install; the CI web job runs the same vitest suite)"""
    web_refute(tmp_path, 'frontend/src/workbench/decode.test.ts', 'expands a run-length mask, false first, and refuses a mask that does not cover the crop', [
        ('src/workbench/decode.ts', 'if (at !== total) throw new Error(', 'if (false) throw new Error('),
    ])


@needs_web
def test_a_lane_that_calls_a_baked_method_live_fails_the_lane_gate(tmp_path):
    """WK-007: the lane function answers live for every method: a baked method is labelled live and the assertion fails (local-only: needs node and `npm ci` in frontend/, which the checks job does not install; the CI web job runs the same vitest suite)"""
    web_refute(tmp_path, 'frontend/src/workbench/engine.test.ts', 'labels a result live only when the engine produced it, replay when the bake did', [
        ('src/workbench/engine.ts', "(liveMethods.includes(method) ? 'live' : 'replay')", "'live'"),
    ])


@needs_web
def test_a_replayed_map_labelled_computed_here_fails_the_provenance_gate(tmp_path):
    """WK-008: the replay label is reworded to a computed-here claim: the label assertion fails (local-only: needs node and `npm ci` in frontend/, which the checks job does not install; the CI web job runs the same vitest suite)"""
    web_refute(tmp_path, 'frontend/src/workbench/views.test.tsx', 'replayed maps are labelled replayed from the bake and name the reference method; they are never labelled live', [
        ('src/workbench/ui.tsx', '`Replayed from the bake: the maps are those of the reference method ${sel.maps.method}.`', '`Computed here: the maps are those of the reference method ${sel.maps.method}.`'),
    ])


@needs_web
def test_an_edit_applied_without_the_engine_fails_the_held_edits_gate(tmp_path):
    """WK-009: the card is reworded to say the edits are applied: the held-edits assertion fails (local-only: needs node and `npm ci` in frontend/, which the checks job does not install; the CI web job runs the same vitest suite)"""
    web_refute(tmp_path, 'frontend/src/workbench/views.test.tsx', 'trap edits without the live engine are held back and the result is said to be the baked case', [
        ('src/workbench/ui.tsx', "'Your trap edits are held: the live engine is not on this build", "'Your trap edits are applied: the live engine is not on this build"),
    ])


@needs_web
def test_a_refused_case_drawn_as_an_empty_chart_fails_the_reason_gate(tmp_path):
    """WK-010: the pending frame no longer shows the reason of an unavailable case: the views say loading and the assertion fails (local-only: needs node and `npm ci` in frontend/, which the checks job does not install; the CI web job runs the same vitest suite)"""
    web_refute(tmp_path, 'frontend/src/workbench/views.test.tsx', 'a refused case shows its reason in every view, never an empty chart', [
        ('src/workbench/ui.tsx', '  if (reason) {\n    return (', '  if (false as boolean) {\n    return ('),
    ])
