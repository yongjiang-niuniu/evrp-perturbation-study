# Third-party sources and notices

Project author: **Yongjiang Liu**. This research project builds on existing EVRP implementations and benchmark data, whose notices are retained below.

## Python EVRP and GSGA baseline

- Upstream: [NeiH4207/evrp-python](https://github.com/NeiH4207/evrp-python).
- Compared revision: [16d3499799ab7aa7bc3f11a5eaf8604947389462](https://github.com/NeiH4207/evrp-python/tree/16d3499799ab7aa7bc3f11a5eaf8604947389462), predating the recovered snapshot.
- Copyright: **2023 Hien Vu**.
- Original notice: [MIT license](LICENSES/evrp-python-MIT.txt), retained verbatim.

| Recovered path | Upstream relationship |
| --- | --- |
| `solver/node.py` | Byte-identical to `objects/node.py` |
| `solver/logger.py` | Byte-identical to `src/utils.py` |
| `solver/GA.py` | GSGA implementation with flattened imports; all 17 function syntax trees match `algorithms/GSGA.py` |
| `solver/solution.py` | Core methods match the upstream apart from documentation and order |
| `solver/greedy.py`, `solver/problem.py` | Adapted baseline modules with small differences |
| `solver/main.py` | Adapted CLI structure with additional algorithm branches and changed defaults |

The upstream copyright and permission notice applies to its copied or adapted portions. The inherited GA is not presented as an independently invented algorithm. No blanket license is newly assigned to project additions by this preservation step.

## Benchmark data and research references

The 17 files in `solver/benchmark/` match the upstream `benchmarks/evrp-2019/` inputs. Their original comments, including benchmark provenance, are retained. The report refers to the [IEEE WCCI 2020 EVRP competition](https://mavrovouniotis.github.io/EVRPcompetition2020/); source documentation and data notices govern reuse of the benchmark material.

The report's bibliography and citations are preserved in `report-source/bibliography.bib`. The report-source package includes its original GPLv3 license text, kept at `report-source/LICENSE`; it is not used to relicense the separate Python baseline, university branding or cited figures.
