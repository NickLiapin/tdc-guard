#!/bin/bash
# CONTROL: the same six worlds, the same seeds, but coincidence share = 0.
# Needed to separate the effect of "many different worlds" from the effect of "there are coincidences".
set -e
TDC="${TDC:-tdcv2}"
export NODE_OPTIONS="--max-old-space-size=8192"
for i in 0 1 2 3 4 5; do
  sed 's|<gen type="text" value="1,0" percent="1.5,98.5"/></sequence>$|<gen type="text" value="1,0" percent="0,100"/></sequence>|' \
      gen/world-coin.tdc > /tmp/c$i.tdc
  [ "$(grep -c 'isCoin".*percent="0,100"' /tmp/c$i.tdc)" = 1 ] || { echo "substitution did not find the isCoin line"; exit 1; }
  $TDC /tmp/c$i.tdc \
       --seed "coin-world-$i" -o data/ctrl-$i-raw.csv
  sort -t, -k1 -n data/ctrl-$i-raw.csv > data/ctrl-$i.csv
  node --max-old-space-size=8192 gen/measure-synth.mjs data/ctrl-$i.csv results/ctrl-$i-windows.csv
  echo "control $i done"
done
