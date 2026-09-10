# Perturbation is All You Need

**Yongjiang Liu's Electric Vehicle Routing Problem (EVRP) research project.** The study investigates how route perturbation, local search and feasibility repair can improve delivery routes under vehicle-load and battery constraints. It compares a greedy baseline, a genetic algorithm, simulated annealing and ant colony optimisation.

**[Read the original 64-page report](reports/EVRP_Report.pdf)** · **[Explore the Python solver](solver/main.py)** · **[View the LaTeX source](report-source/main.tex)**

> **中文概述：** 这是刘勇江的电动车路径规划研究项目，研究载重、电量与充电约束下的路径优化，比较贪心构造、遗传算法、模拟退火和蚁群算法。仓库保留原始论文、LaTeX 图表，以及恢复的 Python 开发版本、17 个基准文件和历史结果。基础框架与 GSGA 保留其开源来源；找回的 2025 年 3 月开发版本尚未确认为最终论文全部实验所用版本。

## Project at a glance

| Item | Details |
| --- | --- |
| Project author | Yongjiang Liu |
| Institution | University of Manchester, School of Computer Science |
| Report | April 2025; supervisor Dr. Francisco Lobo |
| Main methods | Greedy construction, GA/GSGA, SA, ACO, local search and feasibility repair |
| Language and libraries | Python, NumPy, pandas, Matplotlib, Loguru |
| Preserved implementation | Latest recovered development snapshot: 12 March 2025 |
| Available evidence | 15 Python files, a cleaned notebook, 17 benchmark inputs, historical outputs, original PDF and 58 report-source files |

## Research and implementation

The project asks how perturbation can escape poor local solutions while keeping routes feasible. It builds on an existing Python EVRP and Greedy Search + Genetic Algorithm baseline; the inherited implementation is credited in [Third-party notices](THIRD_PARTY_NOTICES.md).

| Method | Focus in this project |
| --- | --- |
| Greedy / GSGA | Construction, evolutionary search and local route refinement; baseline adapted from the credited upstream project |
| Simulated annealing | Multiple neighbourhood operators, temperature-controlled acceptance, reheating and local improvement |
| Ant colony optimisation | Pheromone-guided construction, rank/Max-Min updates, perturbation and local repair |

Additional PSO, VNS and branch-and-bound experiments are retained in the recovered source. The file named `MILP.py` describes a custom heuristic; it is not an exact mathematical-programming solver. These exploratory methods are separate from the report's main comparison.

## Run a small example

Create an isolated environment at the repository root, then use a fresh directory for run outputs:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
mkdir -p runs/quickstart
cd runs/quickstart
MPLBACKEND=Agg python ../../solver/main.py \
  -p ../../solver/benchmark/E-n22-k4.evrp \
  -a GreedySearch -n 1 --seed 12 -o ./greedy
```

This writes a route-distance text file and route plot below `greedy/E-n22-k4/`. The original CLI accepts GreedySearch, GSGA, SA, ACO, PSO, VNS, BNB and MILP; the larger algorithms have hard-coded search budgets in solver/main.py. The preserved SA_test.py and ACO_test.py files are historical algorithm variants, not a pytest suite.

The original logger recreates .log in the working directory, and repeated commands reuse output filenames. Run in a new directory to preserve earlier results. The notebook's code cells are retained, while old output cells and machine metadata have been cleared. See [Running and verification](RUNNING.md) for the tested environment and the limits of the smoke checks.

## Repository guide

| Location | Contents |
| --- | --- |
| [solver/](solver/main.py) | Recovered Python implementation and notebook |
| [solver/benchmark/](solver/benchmark/) | 17 original EVRP benchmark inputs with their source comments |
| [solver/result/](solver/result/) | Unmodified historical outputs; these are not newly reproduced results |
| [reports/EVRP_Report.pdf](reports/EVRP_Report.pdf) | Original 64-page report |
| [report-source/](report-source/main.tex) | Original LaTeX, bibliography, diagrams and plots |
| [REPORT_SOURCE.md](REPORT_SOURCE.md) | Document entry point and preserved build details |
| [EVIDENCE_NOTES.md](EVIDENCE_NOTES.md) | Experimental discrepancies and validation limits |
| [solver-source-manifest.json](solver-source-manifest.json) | Recovered file hashes and publication transformations |
| [report-source-manifest.json](report-source-manifest.json) | Integrity records for the 58 report-source files |

## Results and reproducibility

The report discusses repeated-run route distances, parameter sensitivity and route visualisations using the IEEE WCCI 2020 EVRP benchmark family. Its benchmark overview lists 17 instances, while Table 4.3 presents 13. Some narrative labels and numerical claims disagree with that table; [the evidence notes](EVIDENCE_NOTES.md#result-statements-needing-reconciliation) identify them.

The recovered March snapshot contains related SA/ACO mechanisms and partial stored outputs, but its parameters and results do not match the final comparison table. The historical output folders also contain duplicate labels and failed values. This release preserves that evidence without presenting it as a full reproduction or asserting a universal winning algorithm.

The original Python checker does not explicitly verify complete customer coverage and depot endpoints. The separate C++ validator described in the report has not been recovered. Passing the existing checker or a small smoke run does not establish complete EVRP correctness or final-paper performance.

## Authorship and preservation

This is Yongjiang Liu's research project. The original report, source code and historical data are preserved with their actual recovery dates; no historical development commits have been invented. The published notebook excludes saved execution output and private machine metadata, and the source tree excludes bytecode, local logs and operating-system files.

The baseline includes code from **Hien Vu / NeiH4207's evrp-python**, with the original MIT notice retained in [LICENSES/evrp-python-MIT.txt](LICENSES/evrp-python-MIT.txt). See [Third-party notices](THIRD_PARTY_NOTICES.md) for file-level attribution. The original report-source GPLv3 text is retained separately in [report-source/LICENSE](report-source/LICENSE); it is not a new license grant for unrelated material.
