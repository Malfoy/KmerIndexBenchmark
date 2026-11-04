# Third-party software and data

The harness code is MIT licensed. External tools retain their upstream licenses:

- Zindex: https://github.com/Malfoy/Zindex (MIT; frozen paper source in vendor/)
- COBS: https://github.com/iqbal-lab-org/cobs
- Raptor: https://github.com/seqan/raptor
- kmindex / kmtricks: https://github.com/tlemane/kmindex and https://github.com/tlemane/kmtricks
- Kaminari: https://github.com/yhhshb/kaminari
- Fulgor: https://github.com/jermp/fulgor
- MetaGraph: https://github.com/ratschlab/metagraph
- Themisto: https://github.com/algbio/themisto
- SIMD minimizer extraction: https://github.com/ragnargrootkoerkamp/simd-minimizers

The installer retains source/distribution license files in its installation
prefix. Source revisions, release checksums and the Kaminari compatibility patch
are pinned. The Raptor SeqAn3 inline-variable and COBS integer-header compatibility
changes are explicit in the installer and do not change membership algorithms.

Public genome data are obtained from NCBI RefSeq/GenBank, ENA and AllTheBacteria.
The repository includes identifiers and derived query fragments, not the genome
collections. Consult the source repositories' and archives' usage/citation terms.
The paper measurements and figures are supplied as research reproduction data.
