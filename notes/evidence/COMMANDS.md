# Commands that produced the evidence (2026-10-31)

All run from the suite root unless noted. Checkouts live in a sibling
`scratch/` directory; `ironplc-src` is a symlink to `scratch/ironplc`.

```sh
# IronPLC 5ea0610
git clone --depth 1 https://github.com/ironplc/ironplc scratch/ironplc
(cd scratch/ironplc/compiler && cargo build --release -p ironplcc -p ironplcvm)
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

# RuSTy e911ee5 (LLVM 21 from apt.llvm.org)
curl -fsSL https://apt.llvm.org/llvm-snapshot.gpg.key | gpg --dearmor -o /etc/apt/trusted.gpg.d/llvm.gpg
echo "deb https://apt.llvm.org/noble/ llvm-toolchain-noble-21 main" > /etc/apt/sources.list.d/llvm.list
apt-get update && apt-get install -y llvm-21-dev libpolly-21-dev liblld-21-dev clang-21 lld-21 libzstd-dev
git clone --depth 1 https://github.com/PLC-lang/rusty scratch/rusty
export LLVM_SYS_211_PREFIX=/usr/lib/llvm-21 LLVM_CONFIG=/usr/lib/llvm-21/bin/llvm-config PATH=/usr/lib/llvm-21/bin:$PATH
(cd scratch/rusty && cargo build --release && cargo build --release -p iec61131std --features mock_time)
python3 -I harness/rusty/run.py --plc scratch/rusty/target/release/plc \
    --rusty-src scratch/rusty --record conformance > notes/evidence/rusty-run.txt

# Lean 4.35.0 (elan)
curl -sSfL https://github.com/leanprover/elan/releases/latest/download/elan-x86_64-unknown-linux-gnu.tar.gz | tar xz
./elan-init -y --default-toolchain stable
python3 -I formal/gen_traces.py
(cd formal && lake build)
```

Beremiz: cloned (`scratch/beremiz`) and inspected only; see notes/comparison.md.
