# Evidence and recovery notes

These notes preserve the original report and identify the evidence needed for a reproducible project release.

## Initial report recovery, 9 September 2026

- The original PDF has 64 pages. Its cover names Yongjiang Liu and dates the report April 2025.
- The file was copied without modification; `source_manifest.json` records its SHA-256 hash.
- Local filename and source-project searches found no corresponding implementation or raw experimental outputs in Desktop, Documents or Downloads. A separate copy under the HPC dissertation reference folder is not a recovered EVRP software implementation.
- Report text scanning found no email addresses, student-number labels or password/secret/token mentions. This is a limited text check, not a blanket redistribution clearance.

## Additional recovery, 10 September 2026

- The author's Overleaf project yielded 58 original files, now preserved in [report-source/](report-source/main.tex). Each extracted file matches its ZIP member byte for byte; [report-source-manifest.json](report-source-manifest.json) records hashes and archive provenance. The original PDF remains unchanged.
- The package contains the main LaTeX document, five chapters, front matter, bibliography, figures and its original GPLv3 `LICENSE`. The license file is retained as supplied; no new license scope is asserted for separate materials.
- A shared Python EVRP snapshot with 17 benchmark files and stored outputs was separately recovered locally. It is not included in this public repository while upstream attribution, individual contributions and its relationship to the final report are being checked. A received shared snapshot is not itself proof of sole authorship or final-submission identity.
- The earlier absence of code in the checked GitHub repository and its backup remains a historical fact: its first commit contained only the report and manifest, followed by documentation changes. Finding a later local recovery source does not indicate that code was deleted from that GitHub history.
- The restored report source was checked for unsafe archive paths, private contact details and credential-like text. The review found author/supervisor names, university information and scholarly references; no private email address or credential pattern was found in its text. This is a scoped static check, not a claim to have revalidated every cited asset.

## Result statements needing reconciliation

The following refer to the original report's printed page numbers (PDF page numbers are shown in parentheses). They are not edits to the preserved PDF.

1. The benchmark overview lists 17 instances on printed pages 31-32 (PDF pages 40-41). Table 4.3 on printed page 34 (PDF page 43) presents 13 instances. Recover the result logs before describing all 17 as experimentally evaluated in that comparison.
2. The prose claims GA has the lowest mean on every instance. Table 4.3 instead gives ACO a lower mean on `E-n23-k3` (578.00 versus GA 579.10) and `E-n76-k7` (708.50 versus GA 709.00).
3. Some prose examples on printed pages 34-35 (PDF pages 43-44) swap ACO and SA values relative to Table 4.3. For example, `E-n51-k5` lists ACO 543.00 and SA 601.00 in the table, but assigns them oppositely in the prose.
4. The volatility sentence for `X-n685-k75` compares 222.30 as greater than 229.62 and also swaps the ACO/SA standard deviations. Check the underlying runs before repeating that stability claim.
5. The Figure 4.1 caption and its prose disagree about whether the fourth plot represents SA or ACO. Confirm against the plot source.

## Recovery priorities

- Establish which recovered Python files and results correspond to the final report, preserving the received snapshot and upstream attribution. Continue looking for the described C++ validator or a later final solver version.
- Confirm individual contributions, exact experiment configuration, seed list and benchmark/result provenance before publishing the shared implementation.
- Recalculate summary tables from those outputs and reconcile the narrative using a separate documented revision.
- Add setup and reproduction instructions based on the recovered files and an actual verification run.

No tests or experiments were run on reconstructed or invented implementations. No historical commits were fabricated.
