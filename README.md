# Perturbation is All You Need

A research study of the **Electric Vehicle Routing Problem (EVRP)**: how to improve delivery routes while respecting vehicle load and battery constraints. Yongjiang Liu's report compares a greedy construction baseline with three independently applied search methods, examining route quality, variability and feasibility.

**[Read the original 64-page report](reports/EVRP_Report.pdf).** Its cover is dated April 2025 and names the University of Manchester School of Computer Science and supervisor Dr. Francisco Lobo.

> **中文概述：** 本研究关注电动车路径规划中的载重与电量约束，比较贪心构造、遗传算法、模拟退火和蚁群算法，并讨论扰动、局部搜索与可行性修复。当前保留的是原始研究报告，尚无可运行的原始求解器或实验数据；结果说明保留了论文中表格与叙述需要进一步核对的地方。

## Project at a glance

| Item | Details |
| --- | --- |
| Project type | Individual research report |
| Institution and date | University of Manchester, School of Computer Science; April 2025 |
| Author and supervisor | Yongjiang Liu; Dr. Francisco Lobo |
| Methods | Greedy construction, Genetic Algorithm, Simulated Annealing, Ant Colony Optimization, local search and feasibility checks |
| Implementation described | A C++ solution validator; its source has not been recovered |
| Available artifacts | Original report, evidence notes and a file-integrity manifest |
| Status | Report preserved; original solver, experiment logs and benchmark files unavailable |

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

These are methods documented in the report. The repository currently supplies the written study rather than executable implementations of those methods.

## Reading the report

Start with the problem and constraints, then read the construction and search methods before interpreting the evaluation. For the numerical comparison:

1. Read the benchmark overview on **printed pages 31–32 (PDF pages 40–41)**.
2. Inspect **Table 4.3 on printed page 34 (PDF page 43)**, paying attention to the algorithm labels and the instances actually tabulated.
3. Read [Evidence and recovery notes](EVIDENCE_NOTES.md) alongside the result discussion and Figure 4.1.

No build or installation command is available because the original implementation and runtime environment have not been recovered.

## Results and verification

The report's comparison table presents lower route distances for the search methods than for the greedy baseline. Those values remain historical reported results and have not been independently reproduced from original code or logs.

Some conclusions need reconciliation with the table. The benchmark overview lists 17 instances, while Table 4.3 covers 13. Although the prose claims that GA has the lowest mean on every instance, the table lists lower ACO means for `E-n23-k3` and `E-n76-k7`. Other passages interchange ACO/SA values or labels. The [evidence notes](EVIDENCE_NOTES.md#result-statements-needing-reconciliation) identify the exact examples; the available evidence does not establish a universal winning algorithm.

Archive checks verified that the preserved PDF has 64 pages and matches the original file byte for byte. This documentation refresh checks links and file integrity. Neither step reruns the experiments or resolves the discrepancies in the original results.

## Repository guide

| File | Purpose |
| --- | --- |
| [Original report](reports/EVRP_Report.pdf) | Read the complete research study, figures and references |
| [Evidence and recovery notes](EVIDENCE_NOTES.md) | Review result discrepancies, verification scope and missing artifacts |
| [Source manifest](source_manifest.json) | Check the original filename, size, SHA-256 and report date |

## Limitations and next recovery steps

The solver, C++ validator, benchmark files, exact run configurations, seed list, raw outputs and editable report source have not been recovered. Independent reproduction requires those artifacts before the comparison tables can be recalculated or contradictory labels resolved. A source-code reconstruction would be a new implementation, not the recovered original project.

## Attribution and provenance

The original report credits **Yongjiang Liu** and names **Dr. Francisco Lobo** as supervisor. Its citations and original content remain unchanged. The [source manifest](source_manifest.json) records the preserved PDF; documentation commits describe later preservation and explanation rather than historical implementation milestones.

No new license is assigned to the report, cited material, university branding or third-party figures. Retained references distinguish the study's methods and observations from the work it builds on.
