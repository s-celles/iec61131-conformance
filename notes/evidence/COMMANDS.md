# Commands that produced the evidence (updated 2026-11-07)

All run from the suite root unless noted. Checkouts live in a sibling
`scratch/` directory; `ironplc-src` is a symlink to `scratch/ironplc`.

```sh
# IronPLC 6e40df2 (0.252.0, 2026-11-06)
git clone --depth 1 https://github.com/ironplc/ironplc scratch/ironplc
(cd scratch/ironplc/compiler && cargo build --release --bin ironplcc)
ln -s $PWD/scratch/ironplc ironplc-src
(cd harness/ironplc && cargo build --release)
./harness/ironplc/target/release/iec61131-conformance-ironplc \
    --ironplcc ironplc-src/compiler/target/release/ironplcc --record conformance \
    > notes/evidence/ironplc-run.txt

# matiec 3a41303
apt-get install -y flex
git clone --depth 1 https://github.com/beremiz/matiec scratch/matiec
(cd scratch/matiec && autoreconf -i && ./configure && make -j4)
python3 -I harness/matiec/run.py --iec2c scratch/matiec/iec2c \
    --matiec-lib scratch/matiec/lib --record conformance > notes/evidence/matiec-run.txt

# OpenPLC_v3 b5d4135 (its bundled matiec fork, utils/matiec_src; 2026-11-01)
git clone --depth 1 https://github.com/thiagoralves/OpenPLC_v3 scratch/openplc
(cd scratch/openplc/utils/matiec_src && autoreconf -i && ./configure && make -j4)
python3 -I harness/matiec/run.py --iec2c scratch/openplc/utils/matiec_src/iec2c \
    --matiec-lib scratch/openplc/utils/matiec_src/lib --record conformance > notes/evidence/openplc-run.txt

# STruC++ 72dfcb8 (v0.7.0, built from source with Node 22; 2026-11-01)
git clone https://github.com/Autonomy-Logic/STruCpp scratch/strucpp
(cd scratch/strucpp && git checkout 72dfcb8 && npm ci --ignore-scripts && npx tsc && node scripts/rebuild-libs.mjs)
python3 -I harness/strucpp/run.py --strucpp "node scratch/strucpp/dist/node/cli.js" \
    --runtime-include scratch/strucpp/src/runtime/include --record conformance > notes/evidence/strucpp-run.txt

# RuSTy e911ee5 (LLVM 21 from apt.llvm.org)
curl -fsSL https://apt.llvm.org/llvm-snapshot.gpg.key | gpg --dearmor -o /etc/apt/trusted.gpg.d/llvm.gpg
echo "deb https://apt.llvm.org/noble/ llvm-toolchain-noble-21 main" > /etc/apt/sources.list.d/llvm.list
apt-get update && apt-get install -y llvm-21-dev libpolly-21-dev liblld-21-dev clang-21 lld-21 libzstd-dev
git clone --depth 1 https://github.com/PLC-lang/rusty scratch/rusty
export LLVM_SYS_211_PREFIX=/usr/lib/llvm-21 LLVM_CONFIG=/usr/lib/llvm-21/bin/llvm-config PATH=/usr/lib/llvm-21/bin:$PATH
(cd scratch/rusty && cargo build --release && cargo build --release -p iec61131std --features mock_time)
python3 -I harness/rusty/run.py --plc scratch/rusty/target/release/plc \
    --rusty-src scratch/rusty --record conformance > notes/evidence/rusty-run.txt

# 4diac IDE 3.3.0 + FORTE 3.3.0 (2026-11-01; CI: ubuntu-24.04, xvfb-run)
curl -fsSL -o 4diac-ide.tar.gz "https://download.eclipse.org/4diac/releases/3.3/4diac-ide/4diac-ide_3.3.0-linux.gtk.x86_64.tar.gz"
mkdir -p scratch/4diac-ide && tar -xzf 4diac-ide.tar.gz -C scratch/4diac-ide --strip-components=1
# (on macOS: the .dmg of the same directory, --ide pointing at 4diac-ide.app)
git clone -b 3.3.0 https://github.com/eclipse-4diac/4diac-forte scratch/4diac-forte
cmake -S scratch/4diac-forte -B scratch/4diac-forte/build -DFORTE_ARCHITECTURE=Posix \
    -DFORTE_BUILD_EXECUTABLE=OFF -DBUILD_SHARED_LIBS=ON -DCMAKE_BUILD_TYPE=Release \
    -DFORTE_MODULE_IEC61131=ON -DFORTE_MODULE_CONVERT=ON -DFORTE_MODULE_UTILS=ON \
    -DFORTE_COM_ETH=OFF -DFORTE_COM_FBDK=OFF -DFORTE_COM_LOCAL=ON && cmake --build scratch/4diac-forte/build -j8
xvfb-run -a python3 -I harness/4diac/run.py --ide scratch/4diac-ide --forte-src scratch/4diac-forte \
    --forte-build scratch/4diac-forte/build --record conformance > notes/evidence/4diac-run.txt

# rk 20761dd (adclz/rk, Rust 1.97.1 from its rust-toolchain.toml; 2026-11-02)
git clone https://github.com/adclz/rk scratch/rk
(cd scratch/rk && git checkout 20761dd5c3e559ef5962055490c42cf05dc3e43e && cargo build --release -p rk)
(cd harness/rk && cargo build --release)
./harness/rk/target/release/iec61131-conformance-rk --rk scratch/rk/target/release/rk --record conformance \
    > notes/evidence/rk-run.txt

# Lean 4.35.0 (elan)
curl -sSfL https://github.com/leanprover/elan/releases/latest/download/elan-x86_64-unknown-linux-gnu.tar.gz | tar xz
./elan-init -y --default-toolchain stable
python3 -I formal/gen_traces.py
(cd formal && lake build)
```

Beremiz: cloned (`scratch/beremiz`) and inspected only; see notes/comparison.md.

## Refresh of 2026-11-07

The six locally available runtimes above were run over all 99 tests with
their pinned revisions unchanged. Checkouts were in sibling `../scratch/`,
so compiler/library options used absolute paths from `realpath ../scratch`.
RuSTy was not installed locally; its evidence file was left unchanged.

C/C++ build-error cases were rerun after fixing diagnostic normalisation:
the matiec and STruC++ harnesses now replace the library root with
`<matiec-lib>` / `<strucpp-runtime>` before truncating stderr. The other
normalisations remain those in `.github/scripts/check-evidence.sh` (suite
root, temporary paths, ANSI colours, object offsets, Eclipse timestamps).
All 94 pre-existing verdicts were checked against the captured full run
for each available runtime; only new tests and build-error excerpts changed.
The new results have hand derivations in their `.trace` headers.

See `notes/fuzz-2026-11-07.md` for the fuzz commands and their results.

## Refresh of 2026-11-15

The 2026-11-07 refresh had added `strings/compare_le_ge` and
`strings/len_int` only, and its build-error excerpts predated the
`<matiec-lib>` / `<strucpp-runtime>` masking. The same six runtimes, at the
same pinned revisions, were rerun over all 99 tests with absolute
`../scratch` paths, and the outputs normalised as `check-evidence.sh` does
(with `RUNNER_TEMP` set to the scratch directory). For IronPLC, matiec,
the OpenPLC fork, STruC++ and rk, every pre-existing verdict is unchanged;
the files differ only by the five new tests and by the masked, re-cut
build diagnostics.

For 4diac, only the blocks of the five new tests were inserted into the
existing file. Locally, the IDE fails `data/enum` on `COLOR.dtp` ("Unknown
source type EnumeratedType") instead of the CI's undefined-variable
messages: the verdict (FAIL) is the same, but the local diagnostic was not
recorded in place of the CI one.

Later the same day `pou/inout_array_element` and `pou/output_array_element`
were added (101 tests). The five runtimes were rerun over the whole suite
in the same way: only those two blocks and the summary lines changed. For
4diac, the two blocks of a run on those two tests were inserted, and its
summary line counted them (one PASS, one ERROR).

## Refresh of 2026-11-16

Four structure tests were added (105 tests): `data/struct_init`,
`data/struct_element_copy`, `pou/inout_struct_field` and
`pou/output_struct_field`. IronPLC, matiec, the OpenPLC fork, STruC++ and rk
were rerun over the whole suite as on 2026-11-15. Only the four new blocks
and the summary lines changed. For 4diac, the blocks of a run on the four
tests were inserted, and the summary counts them (three PASS, one ERROR).
RuSTy's file is updated separately, on its own branch, because CI runs that
job only on pull requests and on the weekly schedule.
