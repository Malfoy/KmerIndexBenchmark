# KmerIndexBenchmark

This repository provides a reproducible benchmark suite for comparing the
scalability of genomic sequence indexes. Its goal is to measure the trade-offs
between index size, construction resources and query performance as genome
collections grow, comparing full k-mer indexing with minimizer indexing under
fixed false-positive-rate settings.

The **[benchmark suite](#benchmark-suite)** provides installation, execution and
measurement commands. The **[paper datasets and results](#paper-datasets-and-results)**
are provided separately as frozen accession lists, queries and recorded
measurements accompanying the [Zindex paper](https://www.biorxiv.org/content/10.64898/2026.11.05.764633v1).
You can use the accession lists without installing or running the benchmark suite.

## Benchmark suite

### Supported tools

| Tool | GitHub repository |
|---|---|
| Zindex | [Malfoy/Zindex](https://github.com/Malfoy/Zindex) |
| COBS | [iqbal-lab-org/cobs](https://github.com/iqbal-lab-org/cobs) |
| Raptor | [seqan/raptor](https://github.com/seqan/raptor) |
| kmindex | [tlemane/kmindex](https://github.com/tlemane/kmindex) |
| Kaminari | [yhhshb/kaminari](https://github.com/yhhshb/kaminari) |
| Fulgor | [jermp/fulgor](https://github.com/jermp/fulgor) |
| MetaGraph | [ratschlab/metagraph](https://github.com/ratschlab/metagraph) |
| Themisto | [algbio/themisto](https://github.com/algbio/themisto) |

The suite also uses [kmtricks](https://github.com/tlemane/kmtricks) for kmindex
construction and [SimdMinimizers](https://github.com/ragnargrootkoerkamp/simd-minimizers)
for external minimizer extraction. Exact versions and checksums are recorded in
[configs/tools.lock.json](configs/tools.lock.json).

### Quick start

```bash
git clone https://github.com/Malfoy/KmerIndexBenchmark.git
cd KmerIndexBenchmark
```

Use Linux x86-64, Python 3.11.8 or newer, a C++ compiler, CMake, GNU Make, Git,
GNU time, pigz, and Rust 1.89 or newer. On Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install -y build-essential cmake git pkg-config time pigz curl \
  zlib1g-dev libbz2-dev liblzma-dev libzstd-dev libjemalloc-dev python3-venv
# Install Rust if needed: https://rustup.rs/
./bench doctor
./bench install
./bench download refseq --size 64
./bench run refseq --sizes 64 --bits 8
./bench results
```

`install` builds/downloads pinned versions into `work/tools/`. It does not modify
system tool installations. To start with just two tools, use
`./bench install zindex cobs` and add `--tools zindex cobs` to `run`.

All commands use the CPUs available to the process. Tools run **one at a time**;
all selected tools and modes finish at one collection size before the next size.
Indexes are deleted after testing, while inputs, commands, logs and measurements
are retained. Running the same command again skips successful measurements.

### Choose a collection and precision

```bash
./bench datasets
./bench download atb --size 128
./bench run atb --sizes 64 128 --bits 8 --mode minimizers

# Both dense and minimizer modes, at each of three precision settings:
./bench run refseq --sizes 64 128 --bits 8 16 4 --mode both

# Inspect a queue without downloading or running anything:
./bench run refseq --sizes 64 128 256 512 --dry-run
```

Download the largest requested collection once: smaller collections are its
verified prefixes. The commands above use the frozen collections described in
[Paper datasets and results](#paper-datasets-and-results).

The default run is 64 genomes at target FPR `2^-8`, dense and minimizer modes.
Settings come from the standalone 5 Mb calibration and remain fixed during
collection growth. Exact tools have no fingerprint tuning. No findere is used.
[The protocol](docs/protocol.md) explains native/external minimizer handling,
query semantics, accuracy, resource accounting and known differences between
historical paper timings and fresh runs.

### Put downloads and indexes on a large disk

```bash
export BENCH_WORKDIR=/scratch/zindex-benchmarks
./bench install
./bench download refseq --size 1024
./bench run refseq --sizes 64 128 256 512 1024 --bits 8
```

Alternatively, prefix a command with `./bench --workdir /scratch/benchmark`.
The native RAM budget defaults to **48 decimal GB** and the disk reserve to
**2 GB**. Explicitly change them with `run --max-ram-gb` and
`--disk-reserve-gb`; these choices are recorded. No virtual-address-space cap is
used. kmindex receives a pre-build disk estimate for its uncompressed matrix.
`--keep-indexes` and `--keep-prepared` opt out of the corresponding cleanup.

For a long run, redirect its log and leave it in the background:

```bash
nohup ./bench run refseq --sizes 64 128 256 512 1024 --bits 8 > run.log 2>&1 &
```

`work/status.json` records the current case. There is no high-frequency progress
printing and no automatic parameter search.

### Results from a new run

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-plot.txt
./bench plot --output plots/my-run
```

Fresh results are in `work/reports/results.csv` and `results.json`. Each case
also keeps its exact commands, binary/input identities, native output archives,
wall/CPU time, peak construction/query RSS, sampled temporary-disk use, final
index bytes, positive/negative throughput and source-recovery checks.

Plots are exported as EPS, PDF and PNG. The six-panel layout shows index size,
construction wall time, construction RAM, query RAM, positive query wall time
and negative query wall time.

### Verify and resume

```bash
./bench verify                 # accessions, nesting, source pins and settings
./bench verify --queries       # also verify every original compressed query
python3 -m unittest discover -s tests -v
```

Download retries affect missing transfers only. Completed benchmarks are not
rerun. Failed/interrupted native stages retain their evidence and are not
retried automatically. See [troubleshooting](docs/troubleshooting.md).

[Installation details and versions](docs/installation.md) describe each build.
Native installation pins are in [configs/tools.lock.json](configs/tools.lock.json).
The small [frozen Zindex source archive](vendor/) includes the paper's query
optimizations and construction planners; it avoids depending on an unpublished
working directory. Tool licenses remain their authors'. The harness is MIT
licensed; see [third-party notices](THIRD_PARTY.md).

## Paper datasets and results

The frozen data in this section accompany the
[Zindex paper on bioRxiv](https://www.biorxiv.org/content/10.64898/2026.11.05.764633v1).
They can be browsed or downloaded directly from this repository, independently
of the benchmark suite.

### Accession lists used in the paper

| Collection | Nested collection sizes | Accession lists | Compressed download manifests |
|---|---|---|---|
| RefSeq | 64, doubling through 131,072 assemblies | [RefSeq lists](data/accessions/refseq/) | [refseq.tsv.gz](data/manifests/refseq.tsv.gz) |
| AllTheBacteria (ATB) | 64, doubling through 65,536 samples | [ATB lists](data/accessions/atb/) | [atb.tsv.gz](data/manifests/atb.tsv.gz) |
| Seed experiment | 32 RefSeq genomes | [Seed-study list](data/accessions/seed-study-32.txt) | [seed-study-32.tsv.gz](data/manifests/seed-study-32.tsv.gz) |

Each accession list contains one identifier per line in the original experiment
order. Smaller scaling collections are exact prefixes of the larger lists.
ATB identifiers are BioSample IDs, rather than NCBI assembly accessions.
The manifests supply the corresponding download URLs and recorded metadata.
The original genome collections are downloaded separately and are not bundled.

See [dataset selection and provenance](docs/datasets.md) for the distinction
between the diversity-oriented RefSeq selection and the random ATB selection.
Available lists do not imply that every tool and precision completed every size.

### Queries, settings and recorded results

- [Original compressed queries](data/queries/) and their workload metadata.
- [Fixed 5 Mb calibration reference](data/reference/), assembly `GCF_003003005.1`.
- [Frozen 4-, 8- and 16-bit settings](configs/) and the [measurement protocol](docs/protocol.md).
- [Recorded paper measurements](paper/measurements.csv), [EPS figures](paper/figures/)
  and the [self-contained plotting script](paper/plot.py), including seed and
  parameter-sensitivity experiments.

To inspect the recorded results or regenerate the figures without installing
indexing tools or downloading the genome collections:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-plot.txt
./bench results --paper
./bench plot --paper --output plots/paper
```
