#!/bin/bash
# Second streaming pass: days 0..12 inclusive (up to 1123200 sec).
# Needed for the independent transfer check on day 12 (209 ground-truth events).
set -o pipefail
curl -s --max-time 9000 https://lanl.ma.ic.ac.uk/data/cyber1/auth.txt.gz \
| gunzip \
| awk -F, '
    $1 > 1123200 { exit }
    $8 == "LogOn" { split($2, u, "@"); print $1 "," u[1] "," $4 "," $5 "," $9 }
  ' \
| gzip > data/auth_d0_d12.csv.gz
echo "EXIT=$?"; ls -lh data/auth_d0_d12.csv.gz
