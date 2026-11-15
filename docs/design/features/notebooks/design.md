# Notebook design

The two mirrored language trees are the product's worked teaching interface.
`product.json` supplies real method entry points and package names; the SDD supplies
the ladder and verified research basis. Each lesson imports actual implementations
and reads or constructs data through the product's contracts. It does not reproduce
the engine in notebook cells or substitute precomputed values for method calls.

`check_notebooks.py` owns layout, anatomy, metadata, sources/pins, method-call
analysis, cleanliness, image interpretation and the historical measured bar.
`check_notebook_depth.py` adds the current content obligations and whole-tool
coverage described in [`content-depth.md`](content-depth.md), using the same
structural prose and figure reader. These are static guards on committed files.
They never execute notebook or engine code and do not contact a registry in CI.

`run_notebooks.py` owns actual execution, fresh kernels, copied-tree admission,
source/pin identity and preservation of canonical artifacts. Execution scratch and
temporary training/model examples belong under the configured external task root.
The example curriculum must not write into released `models/` or `data/` trees.

`notebooks/coverage.json` is a bilingual teaching index. Required IDs come from
the actual ladder, catalog, stage files or explicitly declared existing stage
sources and package declarations. A mapping proves existence and level, not
substantive teaching. An independent reader checks every method, boundary,
figure, equation, own-data example and source after fresh execution.

Old source/tag acceptance stays historical. Changed lessons require current
depth and independent review. A failed new gate blocks promotion; it is never
silenced with a lower threshold or a language-specific exception.
