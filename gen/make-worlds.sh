#!/bin/bash
# Six worlds instead of one: different seeds AND different coincidence shares.
# The network will see not one reality but a spread of realities, and will not be
# able to memorise the proportions of a particular world.
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
  pct="${PCTS[$i]}"
  rest=$(python3 -c "print(round(100-$pct,1))")
  sed "s|<gen type=\"text\" value=\"1,0\" percent=\"1.5,98.5\"/></sequence>\$|<gen type=\"text\" value=\"1,0\" percent=\"$pct,$rest\"/></sequence>|" \
      gen/world-coin.tdc > /tmp/w$i.tdc
  [ "$(grep -c "isCoin\".*percent=\"$pct,$rest\"" /tmp/w$i.tdc)" = 1 ] || { echo "coincidence share substitution did not find the isCoin line in the config"; exit 1; }
  $TDC /tmp/w$i.tdc \
       --seed "coin-world-$i" -o data/coin-$i-raw.csv
  sort -t, -k1 -n data/coin-$i-raw.csv > data/coin-$i.csv
  node --max-old-space-size=8192 gen/measure-synth.mjs data/coin-$i.csv results/coin-$i-windows.csv
  echo "world $i (coincidences $pct%) done"
done
