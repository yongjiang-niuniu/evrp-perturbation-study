# Perturbation is All You Need

A research study of the **Electric Vehicle Routing Problem (EVRP)**: how to improve delivery routes while respecting vehicle load and battery constraints. Yongjiang Liu's report compares a greedy construction baseline with three separately evaluated search methods, examining route quality, variability and feasibility.

**[Read the original 64-page report](reports/EVRP_Report.pdf)** or explore its **[restored LaTeX source](report-source/main.tex)**. Its cover is dated April 2025 and names the University of Manchester School of Computer Science and supervisor Dr. Francisco Lobo.

> **中文概述：** 本研究关注电动车路径规划中的载重与电量约束，比较贪心构造、遗传算法、模拟退火和蚁群算法，并讨论扰动、局部搜索与可行性修复。原始 PDF 与 Overleaf 论文源码均已恢复；另已在本地找回协作 Python 求解器快照，正在核对上游来源、个人贡献及其与最终论文的对应关系，暂未纳入公开仓库。

## Project at a glance

| Item | Details |
| --- | --- |
| Project type | Individual research report |
| Institution and date | University of Manchester, School of Computer Science; April 2025 |
| Author and supervisor | Yongjiang Liu; Dr. Francisco Lobo |
| Methods | Greedy construction, Genetic Algorithm, Simulated Annealing, Ant Colony Optimization, local search and feasibility checks |
| Implementation described | Search methods and a C++ solution validator described in the report; a separately recovered Python snapshot requires version and attribution checks |
| Available artifacts | Original PDF, 58 original LaTeX/source-asset files, recovery notes and integrity manifests |
| Status | Report and editable source restored; shared solver snapshot recovered locally, with final-report correspondence and contributor attribution pending |

## Research questions

The study asks how to construct feasible EVRP routes, how perturbation and local search can improve them, and how alternative search strategies compare across benchmark instances. It considers both route distance and the variability of repeated runs, while retaining the problem's capacity and battery constraints.

## Design and method

The report describes a multi-stage greedy route constructor as the baseline. It then evaluates three search approaches independently:

| Method | Main search mechanism |
| --- | --- |
| Genetic Algorithm (GA) | Evolutionary search and route refinement |
| Simulated Annealing (SA) | Neighbourhood perturbations with temperature-controlled acceptance |
| Ant Colony Optimization (ACO) | Pheromone-guided construction and local search |

The described C++ validator checks depot boundaries, customer visits, vehicle capacity, battery feasibility and total route distance. Evaluation uses the IEEE WCCI 2020 EVRP benchmark family, with repeated runs, parameter settings and route visualizations discussed in the report.

These are methods documented in the report. This repository supplies the written study and its editable source. The recovered shared Python snapshot is being assessed separately; its existence does not establish that every algorithm was authored independently by the report's author or that it generated the final tables.

## Reading the report

Start with the problem and constraints, then read the construction and search methods before interpreting the evaluation. For the numerical comparison:

1. Read the benchmark overview on **printed pages 31–32 (PDF pages 40–41)**.
2. Inspect **Table 4.3 on printed page 34 (PDF page 43)**, paying attention to the algorithm labels and the instances actually tabulated.
3. Read [Evidence and recovery notes](EVIDENCE_NOTES.md) alongside the result discussion and Figure 4.1.

For the document entry point, file layout and preserved build limitations, see [Report source and recovery](REPORT_SOURCE.md). No solver installation command is published while the recovered implementation's version, dependencies and provenance remain under review.

## Results and verification

The report's comparison table presents lower route distances for the search methods than for the greedy baseline. Those values remain historical reported results and have not been independently reproduced from original code or logs.

Some conclusions need reconciliation with the table. The benchmark overview lists 17 instances, while Table 4.3 covers 13. Although the prose claims that GA has the lowest mean on every instance, the table lists lower ACO means for `E-n23-k3` and `E-n76-k7`. Other passages interchange ACO/SA values or labels. The [evidence notes](EVIDENCE_NOTES.md#result-statements-needing-reconciliation) identify the exact examples; the available evidence does not establish a universal winning algorithm.

Archive checks verified that the preserved PDF has 64 pages and matches the original file byte for byte. The restored source contains 58 files copied byte for byte from the author's Overleaf export, including figures, bibliography and the license text supplied with that export. These checks do not rerun the experiments or resolve the discrepancies in the original results; recompilation from the restored source has not been verified in this recovery step.

## Repository guide

| File | Purpose |
| --- | --- |
| [Original report](reports/EVRP_Report.pdf) | Read the complete research study, figures and references |
| [Original LaTeX source](report-source/main.tex) | Explore the main document, chapters, bibliography and figure assets |
| [Report source guide](REPORT_SOURCE.md) | Read source-entry, license and recovery-scope notes |
| [Report-source manifest](report-source-manifest.json) | Verify every restored file against the original Overleaf ZIP |
| [Evidence and recovery notes](EVIDENCE_NOTES.md) | Review result discrepancies, verification scope and missing artifacts |
| [Source manifest](source_manifest.json) | Check the original filename, size, SHA-256 and report date |

## Limitations and next recovery steps

The editable report source is restored. A shared Python code snapshot with benchmark files and stored outputs has also been recovered locally. Its correspondence to the final April 2025 report, the authorship of its additions and the completeness of final experiment configurations remain unverified. The report's described C++ validator has not been identified in that Python snapshot. Independent reproduction requires these questions to be settled before its outputs can be used to recalculate the final tables or resolve contradictory labels.

## Attribution and provenance

The original report credits **Yongjiang Liu** and names **Dr. Francisco Lobo** as supervisor. Its citations and original content remain unchanged. The [source manifest](source_manifest.json) records the preserved PDF; documentation commits describe later preservation and explanation rather than historical implementation milestones.

The Overleaf export's original [GPLv3 license text](report-source/LICENSE) is retained in its source directory. This preservation step makes no new license grant or authorship claim for the report, cited assets, university branding or the separate solver snapshot. Retained references distinguish the study's methods and observations from the work it builds on.
