#!/bin/bash
# Six worlds WITH STORMS: sparse shape + the "storm" role as the norm.
# The hypothesis was born from the breakdown of the top of the held-out set - tuning.
set -e
if [ ! -f results/sealed-windows.csv ] && [ -z "$FORCE" ]; then
  echo "results/sealed-windows.csv is missing - the six worlds are only useful against the held-out set."
  echo "Build it first (README, steps 0 and 1), or run with FORCE=1 to generate the worlds anyway."
  exit 1
fi
TDC="${TDC:-tdcv2}"
export NODE_OPTIONS="--max-old-space-size=8192"
PCTS=(0.5 1.0 1.5 2.5 3.5 5.0)
for i in "${!PCTS[@]}"; do
  pct="${PCTS[$i]}"; rest=$(python3 -c "print(round(100-$pct,1))")
  sed "s|<sequence name=\"isCoin\"><gen type=\"text\" value=\"1,0\" percent=\"1.5,98.5\"/></sequence>|<sequence name=\"isCoin\"><gen type=\"text\" value=\"1,0\" percent=\"$pct,$rest\"/></sequence>|" \
      gen/world-storm.tdc > /tmp/st$i.tdc
  [ "$(grep -c "isCoin\".*percent=\"$pct,$rest\"" /tmp/st$i.tdc)" = 1 ] || { echo "coincidence share substitution did not find the isCoin line in the config"; exit 1; }
  $TDC /tmp/st$i.tdc \
       --seed "storm-world-$i" -o data/st-$i-raw.csv
  sort -t, -k1 -n data/st-$i-raw.csv > data/st-$i.csv
  node --max-old-space-size=8192 gen/measure-synth.mjs data/st-$i.csv results/st-$i-windows.csv
  echo "storm world $i done"
done
echo "STORM-WORLDS-DONE"
