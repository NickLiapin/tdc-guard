#!/bin/bash
# One world with 3% new hosts (the final config): generation, windows, shape, evaluation
# on the working days, top forty false alarms. Writes results/newhost-windows.csv.
set -e
TDC="${TDC:-tdcv2}"
export NODE_OPTIONS="--max-old-space-size=8192"
$TDC gen/world-newhost.tdc --seed "newhost-world-0" -o data/newhost-raw.csv
sort -t, -k1 -n data/newhost-raw.csv > data/newhost.csv
node --max-old-space-size=8192 gen/measure-synth.mjs data/newhost.csv results/newhost-windows.csv
echo "NEWHOST-WORLD-MEASURED"
python3 - <<'PY'
import sys; sys.path.insert(0, "net_py")
import numpy as np, data
c = {n: i for i, n in enumerate(data.FEATURES)}
raw, y, _ = data.read_csv("results/newhost-windows.csv")
n = raw[y == 0]; ev = n[:, c["events"]]
storm = (ev >= 100) & (n[:, c["failRatio"]] >= 0.9)
full = (raw[:, c["newUserRatio"]] >= 0.9) & (raw[:, c["failRatio"]] >= 0.15); coin = (y == 0) & full
q = np.percentile(ev, [1, 50, 90])
print(f"windows {len(y)}, labelled {int(y.sum())}, normal {len(n)}; storms {int(storm.sum())} (median events in a storm {np.median(ev[storm]) if storm.sum() else 0:.0f}); "
      f"events 1/50/90% = {q[0]:.0f}/{q[1]:.0f}/{q[2]:.0f}; windows <=2: {100*(ev<=2).mean():.1f}%; coincidences {int(coin.sum())}")
PY
python3 -u net_py/eval_world.py results/newhost-windows.csv "new hosts 3%"
echo "NEWHOST-EVAL-DONE"
python3 -u net_py/top_false.py results/newhost-windows.csv
