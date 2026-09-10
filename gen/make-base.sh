#!/bin/bash
# The base synthetic sets everything started from:
#   synth-train / synth-exam  - base world, training of the fully connected network and boosting,
#                               exam on synthetic data with another seed;
#   rich-train / rich-exam    - rich world (8M events, attack stages);
#   nostage                   - the same world without attack stages;
#   sparse                    - sparse world (a tail of quiet machines).
# Each set: generation -> sort by time -> windows by the measurer.
# The generator is taken from PATH (npm i -g tdcv2) or from the TDC variable.
set -e
TDC="${TDC:-tdcv2}"
export NODE_OPTIONS="--max-old-space-size=8192"
mkdir -p data results
make_one() {  # config, seed, set name
  echo "== $3: $1, seed $2 (a big world takes a few minutes in silence, the file appears at the end)"
  $TDC "$1" --seed "$2" -o "data/$3-raw.csv"
  sort -t, -k1 -n "data/$3-raw.csv" > "data/$3.csv" && rm "data/$3-raw.csv"
  node gen/measure-synth.mjs "data/$3.csv" "results/$3-windows.csv"
}
make_one gen/world.tdc         world-train-1 synth-train
make_one gen/world.tdc         world-exam-1  synth-exam
make_one gen/world-rich.tdc    world-train-1 rich-train
make_one gen/world-rich.tdc    world-exam-1  rich-exam
make_one gen/world-nostage.tdc nostage-1     nostage
make_one gen/world-sparse.tdc  sparse-1      sparse
echo "BASE-DONE"
