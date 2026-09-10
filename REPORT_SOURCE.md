# Original report source

The `report-source/` directory preserves all **58 original files** from the author's Overleaf `EVRP_Report` source export. No chapter, figure, bibliography entry or license file was edited during extraction. The original 64-page PDF in `reports/` remains unchanged.

## Entry point and file map

| Path | Role |
| --- | --- |
| `report-source/main.tex` | Main LaTeX document |
| `report-source/chapters/` | Introduction, background, methodology, evaluation and conclusion |
| `report-source/other/` | Title page, abstract, acknowledgements and abbreviations |
| `report-source/bibliography.bib` | Original references, using `biblatex` |
| `report-source/image/` | Original diagrams, plots and parameter figures |
| `report-source/crest.jpg` | Original title-page university crest |
| `report-source/LICENSE` | GPL version 3 license text present in the original export |

The entry point is `main.tex` with paths relative to `report-source/`. For example, import the contents of that directory into a LaTeX project and select `main.tex` as the main document. The source uses the `report` class, `graphicx`, `biblatex` and mathematical/algorithm packages; bibliography processing requires a compatible LaTeX/Biber environment. The original Overleaf compiler/version configuration was not encoded in this source ZIP. This recovery step did not compile or modify the document, so it does not claim identical output from a newly selected environment.

Two source details are retained unchanged: `main.tex` has an unused `April 2023` date declaration, while the included custom title page explicitly prints **April 2025**; `chapters/appendix_evaluation.tex` is empty and is not included by the main document. The source also retains its original package declarations and bibliography entries rather than silently cleaning them during preservation.

## Integrity and license

The source archive is **10,092,470 bytes**, SHA-256 `73991b112b3412e51750b05b31b56f37a9154a3b2184652d1c33585df5914891`. [The file manifest](report-source-manifest.json) records every extracted path, byte count and SHA-256. Extraction rejected absolute/traversing paths, symbolic links and duplicate names; the accepted files match the original ZIP exactly.

The original GPLv3 `LICENSE` is preserved at its original source-root location. This is a record of the license file supplied with the export, not a new license grant for the report, third-party illustrations or separately recovered solver code. The report's author, supervisor, citations and university identifiers are retained.

## Relationship to the solver

These are the document's editable sources, not a solver implementation. A shared Python snapshot was recovered separately and is currently retained locally while its contributor history, upstream code and correspondence to the final report are reviewed. Its benchmark inputs and outputs are not a substitute for confirming the exact final experiments. See [Evidence and recovery notes](EVIDENCE_NOTES.md) for the current status.
