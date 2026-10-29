# U3b fragment, what is left for the main session (the SDD changes are merged)

## Catalog (docs/contracts)

- After the canonical bake: set `status` to `real` for params-record, case-index, case-manifest, trace and benchmark-results, and recompute
  `data/derived/readiness.json`.
- `readiness.schema.json` keeps the const `example.readiness/v1` (U3a open question 1); `core/readiness.py` writes that value.
