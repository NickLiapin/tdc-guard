#!/bin/bash
# One world with relocation (on top of storms): generation, windows, shape, evaluation
# on the working days, top forty false alarms. Writes results/move-windows.csv.
set -e
TDC="${TDC:-tdcv2}"
export NODE_OPTIONS="--max-old-space-size=8192"
$TDC gen/world-move.tdc --seed "move-world-2" -o data/move-raw.csv
sort -t, -k1 -n data/move-raw.csv > data/move.csv
node --max-old-space-size=8192 gen/measure-synth.mjs data/move.csv results/move-windows.csv
echo "MOVE-WORLD-MEASURED"
python3 - <<'PY'
import sys; sys.path.insert(0, "net_py")
import numpy as np, data
c = {n: i for i, n in enumerate(data.FEATURES)}
raw, y, _ = data.read_csv("results/move-windows.csv")
n = raw[y == 0]; ev = n[:, c["events"]]
storm = (ev >= 100) & (n[:, c["failRatio"]] >= 0.9)
full = (raw[:, c["newUserRatio"]] >= 0.9) & (raw[:, c["failRatio"]] >= 0.15); coin = (y == 0) & full
q = np.percentile(ev, [1, 50, 90])
print(f"windows {len(y)}, labelled {int(y.sum())}, normal {len(n)}; storms {int(storm.sum())} (median events in a storm {np.median(ev[storm]) if storm.sum() else 0:.0f}); "
      f"events 1/50/90% = {q[0]:.0f}/{q[1]:.0f}/{q[2]:.0f}; windows <=2: {100*(ev<=2).mean():.1f}%; coincidences {int(coin.sum())}")
PY
python3 -u net_py/eval_world.py results/move-windows.csv "relocation"
echo "MOVE-EVAL-DONE"
python3 -u net_py/top_false.py results/move-windows.csv
