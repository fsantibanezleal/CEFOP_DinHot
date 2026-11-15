# Native manuscripts and source-content admission

Use the separate [report and paper blueprints](../../templates/manuscripts/README.md), derived from the canonical LaTeX base. A real product always has a complete technical report. Each proposed method and other declared novel contribution has an appropriate separate paper, including negative results. Native sources and bibliography are mandatory; a PDF generated from another document format cannot satisfy the source requirement.

The existing metadata gate checks record identities and declared coverage. The source-content gate now complements it:

```sh
python scripts/check_manuscripts.py
python scripts/check_manuscript_depth.py --report
```

The second command reads the authored `manuscripts/<slug>/` trees, the authoritative SDD and contract catalog, and `product.json`. It enforces native-source presence, allowed classes, section-based papers, required structures, the current content floors, section/coverage depth, result-support labels and matched titles. It includes proposed methods and the SDD's other novel contributions. It performs no numerical execution, build, network read, DOI reservation or upload. A missing or malformed inventory is a failure; it cannot reduce the report's required coverage to zero. The guard uses the base's existing standard-library Markdown inventory parser; adopt the companion source guards together.

Keep `coverage.json` beside each manuscript. The report maps every method and contract ID to its substantial LaTeX section label. A paper maps the declared method or novel contribution IDs under `claims`; `title_support` names actual result figure/table labels. Internal IDs belong in this sidecar, not scientific prose. Complete sources and generated figures must support the title, uncertainty statements and conclusions. The title and record metadata change together when results or scope change.

The formatting blueprints and frozen historical source fixtures remain outside the authored inventory. Unfilled blueprints fail the real source check. The template sentinel exempts the teaching template from pretending it has a published scientific report; it does not exempt authored manuscripts from source validation. Frozen examples retain their original numerical values, native sources, attribution and negative outcomes and grant no current product-qualification waiver.

Before any new publication version, an independent reviewer reads the actual methods, derivations, experiment design, results, limitations and source provenance, and inspects every rendered PDF page. Neither source counts nor a successful LaTeX build replace that review. Only after acceptance does the normal publication workflow reserve identifiers, patch the four header macros, rebuild, verify the PDF, upload the required file set and verify the live record. Deployment separately verifies the accepted product build and scientific artifacts without retraining or rewriting evidence.
