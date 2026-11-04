# Zindex paper benchmarks

Install the eight tools, download the exact bacterial collections, and run the
index-size, construction and query benchmarks from one command-line interface.
The repository includes **every accession list**, the **original compressed
positive/negative queries**, fixed 4-, 8- and 16-bit parameter profiles, and the
paper measurements and plotting code. The fixed5Mb calibration reference is
also included.

Tools: **Zindex, COBS, Raptor, kmindex, Kaminari, Fulgor, MetaGraph and Themisto**.

## Quick start

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

## Choose a collection and precision

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
verified prefixes. RefSeq lists cover **64–131,072** assemblies; ATB lists cover
**64–65,536** samples. See [the lists](data/accessions/) and
[dataset provenance](docs/datasets.md). Large lists do not imply every tool or
precision was completed at that size in the paper.

The default run is 64 genomes at target FPR `2^-8`, dense and minimizer modes.
Settings come from the standalone 5 Mb calibration and remain fixed during
collection growth. Exact tools have no fingerprint tuning. No findere is used.
[The protocol](docs/protocol.md) explains native/external minimizer handling,
query semantics, accuracy, resource accounting and known differences between
historical paper timings and fresh runs.

## Put downloads and indexes on a large disk

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

## Results and plots

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-plot.txt
./bench plot --output plots/my-run

# Regenerate the paper figures immediately, without installing indexing tools:
./bench plot --paper --output plots/paper
./bench results --paper
```

Fresh results are in `work/reports/results.csv` and `results.json`. Each case
also keeps its exact commands, binary/input identities, native output archives,
wall/CPU time, peak construction/query RSS, sampled temporary-disk use, final
index bytes, positive/negative throughput and source-recovery checks.

EPS, PDF and PNG plots use the existing paper filenames. Supplementary panels
are index size, construction wall time, construction RAM, query RAM, positive
query wall time and negative query wall time. The bundled plotter also retains
the paper's seed and parameter-sensitivity data.

## Verify and resume

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
