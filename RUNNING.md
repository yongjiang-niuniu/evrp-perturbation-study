# Running the recovered implementation

The implementation in `solver/` preserves the 12 March 2025 development snapshot. The 15 Python files are unchanged. Dependency setup and the checks described here were added during recovery in September 2026.

## Environment and quickstart

Verified environment: **Python 3.12.14**, macOS 26.5.1 arm64, NumPy 2.3.5, pandas 2.2.3, Matplotlib 3.10.7 and Loguru 0.7.3. `requirements.txt` pins those tested library versions. The original 2025 dependency lock was not recovered; other environments have not been verified.

Use the [README quickstart](README.md#run-a-small-example) from the repository root. Start with the one-run GreedySearch example before increasing the algorithm's budget. The command produces:

```text
runs/quickstart/
  .log
  greedy/E-n22-k4/
    run_0.txt
    run_0.png
```

Choose an unused run-directory name for each new experiment. The original logger deletes an existing `.log` in the working directory on import, and the CLI reuses result filenames. Keep new runs separate from the archived `solver/result/` directory. These original behaviours have been documented without rewriting the historical algorithm source.

The notebook requires Jupyter/IPython if used interactively; those optional tools are not needed for the CLI. Notebook source cells are preserved, while previously stored output and execution metadata have been removed.

## Recovery checks performed on 10 September 2026

All four cases ran in isolated working directories, with headless plotting, seed 12, one numerical-library thread and a 45-second timeout per subprocess. Every case completed before its timeout. GA/SA/ACO were called with reduced constructor parameters by a separate audit caller; these were not changes to the historical CLI defaults.

| Case | Budget | Observed outcome |
| --- | --- | --- |
| GreedySearch | Original CLI, E-n22-k4, one run | Exit 0; finite distance and route PNG written |
| GSGA | Population 10, two generations | Exit 0; finite result; original checker accepted; all 21 customers visited once; depot endpoints present |
| SA | Five iterations with original initialisation | Exit 0; finite result; original checker accepted; all 21 customers visited once; depot endpoints present |
| ACO | Three ants, two generations, intensive local search disabled | Exit 0; finite final result; original checker accepted; all 21 customers visited once; depot endpoints present |

The ACO log included invalid intermediate ant solutions. The final retained route passed the checks above; this does not mean every generated route was feasible. A portable summary of the observed checks and exact constructor parameters is in [verification/smoke-2026-09-10.json](verification/smoke-2026-09-10.json).

Source and benchmark hashes were checked before and after execution. No algorithm or benchmark input was changed, and the preserved historical outputs were not overwritten.

## What these checks establish

The checks establish that these four small workflows can execute in the recorded environment. They do not reproduce the report's final experiment matrix, establish comparative performance, or independently validate every battery/capacity constraint. PSO, VNS, BNB, MILP and the alternate `*_test.py` algorithm files were not executed in these checks.

The original CLI hardcodes much larger GA/SA/ACO budgets. It also seeds Python and NumPy at startup, but the ACO constructor can reseed them internally; the audit caller explicitly set its ACO seed to 12. Do not infer a complete experiment protocol from the CLI's `--seed` argument alone.

The final-report configuration, the separate C++ validator and complete multi-instance outputs remain unresolved. See [EVIDENCE_NOTES.md](EVIDENCE_NOTES.md) before interpreting archived results or making performance claims.
