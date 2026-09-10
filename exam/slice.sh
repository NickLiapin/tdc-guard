#!/bin/bash
# One streaming pass over auth.txt.gz: take days 0..9 (0..864000 sec),
# keep only the fields needed for the login graph, and only LogOn events
# (LogOff/AuthMap are not needed for edge novelty - cuts the volume several times over).
# Output: time,srcuser,srccomp,dstcomp,success - a compact CSV.
set -o pipefail
curl -s --max-time 5400 https://lanl.ma.ic.ac.uk/data/cyber1/auth.txt.gz \
| gunzip \
| awk -F, '
    $1 > 864000 { exit }                      # reached the end of the window - stop the stream
    $8 == "LogOn" {
        split($2, u, "@");                    # srcuser without the domain
        print $1 "," u[1] "," $4 "," $5 "," $9
    }
  ' \
| gzip > data/auth_d0_d9.csv.gz
echo "EXIT=$?"
ls -lh data/auth_d0_d9.csv.gz
