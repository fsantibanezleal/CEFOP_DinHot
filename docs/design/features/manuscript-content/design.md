# Design: portable manuscript content enforcement

The authoritative rule is CAOS_MANAGE `conventions/manuscript-content-bar.md`, together with the header, scientific-voice, method-tier and publication file-set standards. The current product gate only checks `product.json` manuscript metadata. This unit adds the actual source-content gate to the reusable base, retains that existing metadata gate and supplies native source blueprints with explicit draft status.

The initial guard and adversarial unit suite are exported from the management repository's existing standard-library implementation with raw hashes recorded in `upstream.json`. Any subsequent adaptations and reviewer-found defects are separate source changes; export identity must never be used to claim that modified code is byte-identical. Default operation reads source/metadata only, performs no build, numerical computation, installation, DOI reservation, upload or publication, and returns a nonzero exit code with precise findings.

## Authoritative inputs and coverage

The product root contains `product.json`, `docs/design/SDD.md`, `docs/contracts/catalog.md` and `manuscripts/<slug>/`. A manuscript has one native main file, included LaTeX sources, a bibliography and `coverage.json`. Each actual product needs a technical report; proposed contributions need separate appropriate manuscripts. The template sentinel exempts the teaching template from pretending that it already has a published scientific report. Formatting blueprints and source fixtures live outside the authored `manuscripts/` inventory and remain explicitly identified as such.

The report and paper have different required structures and floors. A technical report needs12000 prose words,25 display equations,10 figures,8 tables,30 references and3 algorithms. A paper needs7000 words,12 equations,6 figures,4 tables,25 references and1 algorithm. Ordinary top-level sections need350 prose words, designated short sections150, subsections150 and captions15. Each method coverage region needs600 words/two equations, each proposed-claim region1500/six equations, and each contract120 words. These values are copied from the current rule, not made configurable as a per-product waiver.

The current multipage-table rule also counts captioned longtable environments, with the same caption, label and prose-reference requirements. The guard shares the existing reviewed standard-library Markdown inventory parser with the companion source guards, refuses missing/malformed/hidden-only inventories, and includes both declared proposed methods and other novel contributions. Literal quoted LaTeX does not become active includes, structure or content counts.

Inventory membership comes from that same validated table result, including inline-code IDs and valid row indentation. A second approximate ID reader cannot silently reduce required coverage. Distinct methods and proposals need disjoint substantial source regions; different labels in the same section, or a parent and its child, cannot double-count one region. Active core TeX conditionals in the body are refused as statically unmeasurable rather than credited as rendered prose. The checker is not a TeX interpreter. Title matching retains numbers, signs, units, case and unknown commands instead of reducing a title to alphabetic words. Nested inputs use the main compilation working directory, including a main in the allowed tex subfolder.

## Native source and historical examples

Default blueprints use the authoritative11pt article base,1.1in margins, navy links, theorem family, ORCID/header identity and running headers. The technical report and research paper remain separate source trees; the paper uses sections. Unpublished blueprint metadata must not invent a DOI, author approval, scientific result or completed content review. The content gate refuses incomplete authored copies.

Frozen source examples are copied only from immutable SoftQP v0.01.002 source, with exact hashes and attribution. They retain both negative studies and their historical report/paper versions. They are validation/style examples, not new scientific products or results of the epidemic teaching example. No renderer recreates those numerical results and no ReportLab or alternative PDF generator substitutes for native LaTeX.

## Acceptance sequence

Implement the portable guard, meaningful positive/negative tests, exact-source examples and native blueprints. Run the actual source gate and examples, inspect the generated native formatting proof where relevant, and obtain independent source/content/visual review. Then integrate with current upstream/base changes and hosted CI. Release/versioning and product adoption are root-owned later steps; no local count or compiler exit grants permission to skip those gates.
