# Evidence and recovery notes

These notes preserve the original report and identify the evidence needed for a reproducible project release.

## Verified during local recovery

- The original PDF has 64 pages. Its cover names Yongjiang Liu and dates the report April 2025.
- The file was copied without modification; `source_manifest.json` records its SHA-256 hash.
- Local filename and source-project searches found no corresponding implementation or raw experimental outputs in Desktop, Documents or Downloads. A separate copy under the HPC dissertation reference folder is not a recovered EVRP software implementation.
- Report text scanning found no email addresses, student-number labels or password/secret/token mentions. This is a limited text check, not a blanket redistribution clearance.

## Result statements needing reconciliation

The following refer to the original report's printed page numbers (PDF page numbers are shown in parentheses). They are not edits to the preserved PDF.

1. The benchmark overview lists 17 instances on printed pages 31-32 (PDF pages 40-41). Table 4.3 on printed page 34 (PDF page 43) presents 13 instances. Recover the result logs before describing all 17 as experimentally evaluated in that comparison.
2. The prose claims GA has the lowest mean on every instance. Table 4.3 instead gives ACO a lower mean on `E-n23-k3` (578.00 versus GA 579.10) and `E-n76-k7` (708.50 versus GA 709.00).
3. Some prose examples on printed pages 34-35 (PDF pages 43-44) swap ACO and SA values relative to Table 4.3. For example, `E-n51-k5` lists ACO 543.00 and SA 601.00 in the table, but assigns them oppositely in the prose.
4. The volatility sentence for `X-n685-k75` compares 222.30 as greater than 229.62 and also swaps the ACO/SA standard deviations. Check the underlying runs before repeating that stability claim.
5. The Figure 4.1 caption and its prose disagree about whether the fourth plot represents SA or ACO. Confirm against the plot source.

## Recovery priorities

- Recover the original solver and C++ validator source, preserving existing Git history if available.
- Recover the exact experiment configuration, seed list, benchmark provenance and raw route/result outputs.
- Recalculate summary tables from those outputs and reconcile the narrative using a separate documented revision.
- Add setup and reproduction instructions based on the recovered files and an actual verification run.

No tests or experiments were run on reconstructed or invented implementations. No historical commits were fabricated.
