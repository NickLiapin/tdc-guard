#!/bin/bash
# HELD-OUT SET: the whole span up to the end of day 29 (2 592 000 sec) - that is
# where the last ground-truth event lies. Only days 8 and 12 remain working days; all other
# labelled days (1,2,5,6,7,9,13,14,15,20,21,22,26,27,28,29 - 267 events)
# are neither measured nor looked at until the single final run.
set -o pipefail
curl -s --max-time 14400 https://lanl.ma.ic.ac.uk/data/cyber1/auth.txt.gz \
| gunzip \
| awk -F, '
    $1 > 2592000 { exit }
    $8 == "LogOn" { split($2, u, "@"); print $1 "," u[1] "," $4 "," $5 "," $9 }
  ' \
| gzip > data/auth_sealed_full.csv.gz
echo "EXIT=$?"; ls -lh data/auth_sealed_full.csv.gz
