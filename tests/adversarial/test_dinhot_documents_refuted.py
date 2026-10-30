"""Documents requirements DC-001 to DC-004 (docs/design/features/documents/): each web test copies the web code, plants the defect in the page source and runs the requirement's own vitest test, which passes untouched and must fail planted (local-only: needs node and the installed frontend)."""
from __future__ import annotations

import pytest
from planting import NODE, NODE_MODULES
from web_plant import web_refute

needs_web = pytest.mark.skipif(NODE is None or not (NODE_MODULES / "@fasl-work").is_dir(), reason="needs node and `npm ci` in frontend/")


@needs_web
def test_a_technical_view_without_an_area_fails_the_adr_0017_gate(tmp_path):
    """DC-001: the honesty area is renamed in the page source: the area is not found and the assertion fails (local-only: needs node and `npm ci` in frontend/, which the checks job does not install; the CI web job runs the same vitest suite)"""
    web_refute(tmp_path, 'frontend/src/content/introduction/technical.test.tsx', 'declares the five areas of ADR-0017 section 2.1, each with the content it requires', [
        ('src/content/introduction/technical.tsx', 'area="honesty"', 'area="honest"'),
    ])


@needs_web
def test_a_technical_view_with_an_em_dash_fails_the_typography_gate(tmp_path):
    """DC-002: a title of the honesty area is given an em-dash (written as an escape in the source): the rendered text holds it and the assertion fails (local-only: needs node and `npm ci` in frontend/, which the checks job does not install; the CI web job runs the same vitest suite)"""
    web_refute(tmp_path, 'frontend/src/content/introduction/technical.test.tsx', 'carries no em-dash, no arrow, and no DinHot measured number', [
        ('src/content/introduction/technical.tsx', "en: 'What is exact and what is not claimed'", "en: 'What is exact \u2014 and what is not claimed'"),
    ])


@needs_web
def test_a_range_scored_by_the_wrong_side_fails_the_experiments_gate(tmp_path):
    """DC-003: the range score counts the values outside the range instead of inside: the page disagrees with the bake and the assertion fails (local-only: needs node and `npm ci` in frontend/, which the checks job does not install; the CI web job runs the same vitest suite)"""
    web_refute(tmp_path, 'frontend/src/content/experiments/experiments.test.tsx', 'reads every checked range of every method as inside (the bake passed them)', [
        ('src/content/experiments/data.ts', 'if (inside(v[metric], r)) ok += 1;', 'if (!inside(v[metric], r)) ok += 1;'),
    ])


@needs_web
def test_a_contract_table_that_drifts_from_the_catalog_fails_the_implementation_gate(tmp_path):
    """DC-004: the version of the first row is changed in the page data: it no longer agrees with the catalog and the assertion fails (local-only: needs node and `npm ci` in frontend/, which the checks job does not install; the CI web job runs the same vitest suite)"""
    web_refute(tmp_path, 'frontend/src/content/implementation/contract.test.ts', 'lists the rows of the catalog, in order, with their version and producer', [
        ('src/content/implementation/contract-rows.ts', "id: 'params-record',\n    version: '1.0.0',", "id: 'params-record',\n    version: '9.9.9',"),
    ])
