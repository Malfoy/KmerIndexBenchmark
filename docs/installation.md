# Installation details

`./bench install` installs the eight indexing tools and kmtricks (a kmindex
dependency) under the work directory. Building Zindex also installs the pinned
Rust SIMD minimizer FASTA utility. Rust1.89 or newer is needed. Compilation uses
all affinity CPUs and Release configuration.

| Tool | Pin | Installation |
|---|---|---|
| Zindex | Paper source SHA in tools.lock.json | Bundled source archive, Cargo release |
| COBS |0.3.1| Checksummed upstream source archive, CMake |
| Raptor |3.0.1, commit01b8afc…| Source and pinned submodules, CMake |
| kmindex |0.6.1| Checksummed Linux x86-64 release |
| kmtricks |1.6.0| Checksummed Linux x86-64 release |
| Kaminari |305f2c5…| Source, pinned argparse and merge compatibility patch |
| Fulgor |ef654195…| Source and pinned submodules, CMake |
| MetaGraph |0.5.2| Checksummed Linux DNA release binary |
| Themisto |3.2.2| Checksummed Linux distribution, retaining companion executables |

The complete revisions and checksums, not the shortened labels above, define
installation identity. A successful installation records the actual binary SHA
and its source pin. Rerunning installation checks the existing binary rather
than rebuilding it. Incomplete archive extraction is staged separately, so it
cannot look like a completed source tree after interruption.

Pinned releases require Linux x86-64; this is not a portable ARM installer.
Zindex's native SIMD flags and the comparator binaries may require a recent CPU.
The local patch for Kaminari's single-file merge, the COBS integer-header include,
and SeqAn3 inline-variable compiler compatibility changes are explicit. Source
and distribution licenses remain in the prefix; installed binaries are retained.

`doctor` checks prerequisites without installing anything. The optional GitHub
Actions **native installation check** is manual, one selected tool at a time;
the default CI uses lightweight command/output fixtures and verifies dataset
integrity without compiling every indexer or launching bacterial benchmarks.
