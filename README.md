# Perturbation is All You Need: Electric Vehicle Routing

A research report by **Yongjiang Liu** on the Electric Vehicle Routing Problem (EVRP). The report studies how perturbation, local search and feasibility repair can improve routes under vehicle load and battery constraints.

[Read the original report](reports/EVRP_Report.pdf). The cover is dated April 2025 and names the University of Manchester School of Computer Science and supervisor Dr. Francisco Lobo.

## Project approach

The report describes a multi-stage greedy route constructor, followed by three independently applied search methods:

- A Genetic Algorithm with evolutionary search and route refinement.
- Simulated Annealing with neighborhood perturbations and temperature-controlled acceptance.
- Ant Colony Optimization with pheromone-guided construction and local search.

A C++ solution validator is described for checking depot boundaries, customer visits, vehicle capacity, battery feasibility and total distance. The evaluation uses the IEEE WCCI 2020 EVRP benchmark family and discusses repeated runs, parameter settings and route visualizations.

## What is preserved

| File | Purpose |
|---|---|
| `reports/EVRP_Report.pdf` | Unmodified 64-page report. |
| `EVIDENCE_NOTES.md` | Scope of the recovered evidence and issues to check against the original experiments. |
| `source_manifest.json` | Original filename, file size and SHA-256 checksum. |

This recovery contains the report. The implementation, original experiment logs, benchmark files and editable report source have not yet been recovered, so the experiments cannot currently be reproduced from this archive. A working software package should be documented when those original files are found.

## Reading the results

The report presents lower route distances for the search methods than the greedy baseline in its comparison table. Its numerical results remain historical reported results; they have not been independently rerun during archiving. Some prose and table labels require reconciliation, recorded in [the evidence notes](EVIDENCE_NOTES.md). This README therefore does not claim a universal winning algorithm or independently verified performance gains.

## 中文说明

这是 Yongjiang Liu 的电动车路径规划研究报告存档，主题是通过扰动、局部搜索和可行性修复，比较遗传算法、模拟退火和蚁群算法。当前保留的是原始报告；源代码、原始实验记录和可编辑论文源文件尚未恢复，不能仅凭这个仓库复现实验。说明文件区分了论文中的历史报告结果与本次整理实际核验的内容。

## Preservation and reuse

The report is preserved byte-for-byte. Archival documentation was prepared on 9 September 2026; this does not represent a new implementation milestone. No new license is assigned to the original report, cited material, university branding or third-party figures.
