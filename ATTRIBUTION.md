# Attribution

DinHot is released under the Apache License 2.0 (`LICENSE`). This file credits what the product builds on, states the terms that require attribution, and says what was not confirmed.

## Provenance: DinHotSys

DinHot is the rebuild of **DinHotSys** ("Dynamic Holographic Optical Tweezers"), a C++ desktop tool (Windows Forms, OpenGL and OpenMP) of the **CEFOP**, **Universidad de Concepcion**, dated **2010**. The credits that the original files
state are the assembly company "UdeC", the product name "DinHotSys", "Copyright (c) UdeC 2010" and the version string 1.0.*; the tool's own window title reads "Gestor Sistema: Dinamic Hot System v 0.1.2". The original files name no author,
and this file therefore names none: the individual credit of the original developers is UNVERIFIED and is added here when it is stated by the repository owner.

The state of the repository before this rebuild, including the original sources, is kept in its history at commit f032a9b:
https://github.com/fsantibanezleal/CEFOP_DinHot/tree/f032a9b

What carries over is the name, the lineage and the idea of an interactive trap-array tool; the code does not. The original C++ is not part of the tree (it remains in the history above), and none of its code is used by this build. The
later Python and FastAPI port that preceded this rebuild was rewritten as well; nothing of its engine remains.

## Colormaps

The phase views use a perceptually uniform cyclic colormap of the **CET** family by Peter Kovesi, and the intensity views use inferno.

- **CET cyclic maps (colorcet).** Peter Kovesi, "Good Colour Maps: How to Design Them", https://arxiv.org/abs/1509.03700 ; the maps and their data: https://colorcet.com/gallery.html and https://colorcet.com/download/index.html .
  Licence: **Creative Commons Attribution 4.0 International (CC BY 4.0)**, https://creativecommons.org/licenses/by/4.0/ ; the licence asks to cite the site and the paper, which this entry does. The Python package `colorcet`
  3.2.1 declares the same licence (CC-BY-4.0): https://pypi.org/pypi/colorcet/json , source https://github.com/bokeh/colorcet . The map in use is CET-C1 (cyclic magenta, red, yellow, blue; `cyclic_mrybm_35_75_c68`) sampled to
  256 entries of 8-bit RGB and embedded as data in the workbench source, so that phase 0 and phase 2 pi are the same colour. The change from the published data is that sampling and 8-bit rounding. The workbench source that
  carries the data is not on this branch yet; the map name was read from its header and is to be confirmed when it lands (UNVERIFIED here).
- **inferno.** Nathaniel Smith and Stefan van der Walt, the matplotlib colormap, embedded in the same way as 256 entries of 8-bit RGB; the licence recorded in the workbench source header is CC0 (public domain dedication).
  Confirmed from that header only, not from the matplotlib distribution (UNVERIFIED here).

Matplotlib's `twilight` was considered for phase and not used: the repository that holds its data shows no licence statement (https://github.com/bastibe/twilight ).

## Published methods

The engine implements the methods of the ladder from their published descriptions; **no code of any existing holography software is copied, vendored or imported**. The sources are cited on each [framework card](docs/frameworks.md) with their DOIs or
URLs, and the main ones are listed here so that the intellectual credit is in one place:

- Di Leonardo, Ianni and Ruocco 2007 (superposition, random superposition, Gerchberg-Saxton, adaptive and weighted variants), https://doi.org/10.1364/OE.15.001913
- Polin, Hovhannisyan and Sorensen 2005 (direct search), https://doi.org/10.1364/OPEX.13.005831
- Kim, Kim, Lee and Ahn 2019 (phase-fixed weighted GS), https://doi.org/10.1364/OL.44.003178
- Pasienski and DeMarco 2008 (MRAF), https://doi.org/10.1364/OE.16.002176
- Harte, Bruce, Belmonte and Arnold 2014 (conjugate gradient), https://doi.org/10.1364/OE.22.026548
- Chakravarthula et al. 2019 (Wirtinger holography), https://doi.org/10.1145/3355089.3356539
- Nogrette et al. 2014 (camera feedback and aberration correction), https://arxiv.org/abs/1402.5329
- Schroff, La Rooij, Haller and Kuhr 2023 (pixel crosstalk model and sampling), https://doi.org/10.1038/s41598-023-30296-6
- Lee, Kim and Ahn 2017 (Hungarian rearrangement), https://doi.org/10.1103/PhysRevA.95.053424 ; linear phase interpolation, https://arxiv.org/abs/2501.01391
- Whyte and Courtial 2005 (volumetric 3D GS), https://doi.org/10.1088/1367-2630/7/1/117
- Montes-Usategui et al. 2006 (random mask), https://opg.optica.org/oe/fulltext.cfm?uri=oe-14-6-2101
- Swan et al. 2024 and Torchylo et al. 2025 (optimal-transport initialization), https://arxiv.org/abs/2408.17025 ; https://arxiv.org/abs/2512.19072
- Eybposh et al. 2020 (DeepCGH), https://doi.org/10.1364/OE.399624
- Grimm, Weidemuller and Ovchinnikov 2000 (dipole traps), https://arxiv.org/abs/physics/9902072
- Tolic-Norrelykke et al. 2006 (calibration spectrum), https://arxiv.org/abs/physics/0603037
- Noll 1976 (Zernike ordering), https://doi.org/10.1364/JOSA.66.000207 (not opened; UNVERIFIED)

Existing holography software was studied as a reference only and none of it is used: slmsuite (MIT), odak (MPL-2.0), hologradpy (LGPL-3.0), the OTSLM toolbox (GPLv3 per its paper, MATLAB), neural-holography (a custom academic,
non-commercial licence), DeepCGH and holotorch (licence not asserted on their repositories; a copyright file of DeepCGH was not read), as reported when they were surveyed; the licence of Red Tweezers could not be found (UNVERIFIED).

The portable random generator is **xoshiro128\*\*** (Blackman and Vigna, https://arxiv.org/abs/1805.01407 , reference at https://prng.di.unimi.it/xoshiro128starstar.c ) seeded by **SplitMix32**
(https://github.com/bryc/code/blob/master/jshash/PRNGs.md , described there as public domain). Both were re-implemented from their published update rules and cross-checked against an independent implementation; no source file was copied.
The licence terms of the xoshiro reference file were not confirmed (UNVERIFIED).

## Third-party code and data bundled with the site

| Item | Version | Role | Licence |
|---|---|---|---|
| fft.js | 4.0.4 | the FFT of the live engine, bundled in the site | MIT (as recorded when it was chosen) |
| onnxruntime-web | 1.31.1 | in-browser inference of the learned models; its WebAssembly file is hosted with the site | UNVERIFIED: not read for this file |
| CET-C1 and inferno colour data | see above | embedded colormap tables | CC BY 4.0 and CC0, see above |

The other dependencies (the shared app shell, React, the charting and 3D libraries, the build and test tools, numpy and the rest of the pipeline) are used as installed packages under their own licences, which the packages carry; they are
pinned with exact versions in `docs/design/SDD.md` (technology and versions), in the frontend lock file and in the requirements files. None of them is modified or redistributed outside the built site.

## Data

The product uses **no third-party dataset**. Its fourteen cases are synthetic, with stated parameters. Published numbers that appear in the documentation and in the pages are quoted as facts with their source, never as data files. The sourced
figures of the executive view of the Introduction carry their sources in `content/executive.json`.

## Trademarks and institutions

CEFOP and Universidad de Concepcion are named for the provenance of DinHotSys only; the names of the other software, journals and institutions above belong to their owners. Their mention is attribution, not endorsement.
