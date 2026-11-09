# Datasets used in the paper

This page documents the frozen collections used in the
[Zindex paper](https://www.biorxiv.org/content/10.64898/2026.11.05.764633v1).
The accession lists and compressed manifests can be used independently of the
[benchmark suite](../README.md#benchmark-suite).

`data/accessions/refseq/N.txt` and `data/accessions/atb/N.txt` contain one
identifier per line in the exact benchmark order. No header, absolute filesystem
path or new random draw is required. All smaller collections are verified
prefixes of their collection's largest list.

| Collection | Included prefixes | Identifier |
|---|---|---|
| RefSeq | 64, doubling through 131,072 | Versioned assembly accession, `GCF_… .version` |
| ATB | 64, doubling through 65,536 | BioSample identifier used by ATB, such as `SAMN17531909` |

ATB object identifiers are **BioSamples**, not NCBI assembly accessions. The
portable manifests include the exact public object URLs. They must not be
reinterpreted as RefSeq accessions or silently replaced by a different assembly.

The RefSeq selection emphasizes species diversity, using the frozen catalogue
and taxonomy. The larger extension first adds species not already represented,
then additional assemblies to reach 131,072. It is not an assertion of a fixed
ANI separation or complete nonredundancy. ATB is a frozen random permutation
without taxonomic filtering, so related assemblies are retained. The selection
seeds and original manifest identities are in `data/provenance.json`.

`data/manifests/*.tsv.gz` hold accession, order, download URLs, expected base
count, taxonomy where recorded, and available sequence/compressed-file digests.
No original genome collection is bundled. The single fixed 4,999,712-base
calibration genome (`GCF_003003005.1`) is included in `data/reference/`. Genomes remain gzip-compressed during
download and benchmarking.

Some FTP assemblies disappeared after selection. Their frozen manifests retain
exact versioned ENA/paired-assembly or WGS-component recovery URLs, together
with the original accession label and archive provenance. Multiple component
URLs are concatenated as gzip members, preserving the whole assembly. The
downloader validates readable FASTA and expected total bases, and known static
FTP compressed checksums when available. It never picks an alternative species
or a newer assembly version if a URL is unavailable.

The **original compressed query files** are bundled once per distinct file in
`data/queries/`. The JSON index resolves collection sizes to exact workloads and
source-color metadata. RefSeq extensions above 16k reuse the frozen 16k workloads,
as the actual extension runs did. Query files contain approximately 16k positive
and 16k negative 1 kb records per experiment; the exact counts are in the metadata.
This costs about 168 MB and avoids silently regenerating different reads.

Upstream collections: [NCBI RefSeq](https://www.ncbi.nlm.nih.gov/refseq/) and
[AllTheBacteria](https://github.com/AllTheBacteria/AllTheBacteria). Frozen selection
identities, rather than their changing current catalogues, define these runs.

The 32 RefSeq genomes used in the seed experiment are also listed, in their
original paired order, in `data/accessions/seed-study-32.txt`, with portable
URLs/taxonomy in the matching manifest. `configs/seed-study.json` preserves its
error profiles and seed configurations. The bacterial scaling runner and the
seed error-sweep are different experiments; `plot --paper` reproduces both sets
of recorded figures without rerunning the original error-sweep kernels.
