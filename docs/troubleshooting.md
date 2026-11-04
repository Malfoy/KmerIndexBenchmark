# Troubleshooting

- **`doctor` reports a missing program:** install the prerequisite in the README.
  Rust is needed for Zindex and the external SIMD minimizer FASTA utility.
- **A tool installation fails:** read `work/logs/install/TOOL.log`. Installation
  does not replace system binaries. Pinned source IDs and compatibility changes
  are visible in `configs/tools.lock.json` and `benchkit/install.py`.
- **An accession URL returns404:** the accession is retained and the download
  report lists the failing version. Rerun `download` for missing files only.
  Do not replace it by a newer release and still call it the same dataset.
- **Not enough disk:** inspect the preflight `admission.json`, remove only derived
  inputs/indexes you no longer need, or use a larger `--workdir`. A pre-native
  resource deferral can be reconsidered; no failed native command is retried.
- **A tool exceeds RAM or its query fails:** its `FAILED.json`, stage metrics and
  stderr remain. Successful construction has a separate `construction-result`.
  This is not a completed construction-and-query case. Use a different output
  work directory for a deliberate new experiment, preserving the failed attempt.
- **An interrupted case exists:** inspect it before proceeding. Completed cases
  are skipped, but an unfinished native stage is never silently repeated.
- **Minimizer preparation was interrupted:** only the derived directory named
  in the error may be removed and regenerated. Original compressed genomes and
  bundled query files must remain intact.
- **Plotting is unavailable:** activate the plotting venv and install
  `requirements-plot.txt`. Core running and CSV export use only the standard
  library. Plotting is a separate command and never reruns native measurements.

The bundled paper data retain historical construction/query resource boundaries.
In particular, COBS64k minimizer construction succeeded but its positive query
was OOM-killed; the construction-only point has no invented query measurement.
RefSeq16bit dense32k was deferred before launch because of disk, not a native
execution failure. ATB4 contains Zindex results only. See `paper/results.json`
for actual tool/mode/size coverage, not merely the largest accession list.
