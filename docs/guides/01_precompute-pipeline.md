# Guide, run the precompute pipeline

```bash
./scripts/setup.sh            # or scripts/setup.ps1, builds .venv-pipeline + .venv, installs, editable pkg
./scripts/precompute.sh       # all cases   (or:  ./scripts/precompute.sh EX02_epidemic --seed 7)
.venv-pipeline/bin/python -m pytest        # (Scripts/python.exe on Windows)
./scripts/smoke.sh            # CONTRACT 2 check: index <-> manifests <-> artifacts consistent
```

Outputs land in `data/derived/<case>/trace.json` + `data/derived/manifests/<case>.json` + `index.json`. The run is
deterministic in `(params, seed)`, same seed ⇒ byte-identical artifact. Stages + their roles:
[../architecture/05_precompute-pipeline.md](../architecture/05_precompute-pipeline.md).
