// FINAL CHECK on the held-out set. Run ONCE.
//
// Days: 1,2,5,6,7,9,13,14,15,20,21,22,26,27,28,29 - everything except the working days 8 and 12.
// The weights are not touched (net/model-v7.json), the measurer is the same, the thresholds are the same.
//
// The baseline rule is the one verified on day 12 and chosen BEFORE looking at
// the result: the baseline is frozen on the first week and not updated afterwards;
// for the early days the baseline is everything that came before them. The rule is causal.
import { aggregate, toCsv } from "../judge/windows.mjs";
import { readFileSync, writeFileSync } from "node:fs";
const ROOT = new URL("..", import.meta.url).pathname;
const D = 86400, W = 3600;
const SEALED = [1, 2, 5, 6, 7, 9, 13, 14, 15, 20, 21, 22, 26, 27, 28, 29];
const FREEZE = 8; // baseline: days 0..7

const truth = readFileSync(`${ROOT}data/redteam.txt`, "utf8").trim().split("\n")
  .map((l) => l.split(",")).map(([t, , src]) => ({ t: +t, src }));

const batches = [];
for (const d of SEALED) {
  const hist = Math.min(d, FREEZE) * D;
  const key = String(hist);
  let b = batches.find((x) => x.hist === hist);
  if (!b) batches.push((b = { hist, days: [] }));
  b.days.push(d);
}

const all = [];
for (const b of batches) {
  // one batch = one streaming pass: one baseline, possibly many days
  for (const chunk of chunks(b.days, 4)) {
    const from = Math.min(...chunk) * D, to = (Math.max(...chunk) + 1) * D;
    const slots = new Set();
    for (const { t, src } of truth) {
      if (t >= from && t < to && chunk.includes(Math.floor(t / D))) slots.add(`${src}|${Math.floor(t / W)}`);
    }
    const { rows } = await aggregate({
      path: `${ROOT}data/auth_sealed_full.csv.gz`,
      historyUntil: b.hist, examStart: from, examEnd: to, window: W,
      truth: (p, key) => slots.has(key),
    });
    const keep = rows.filter((r) => chunk.includes(Math.floor((r.slot * W) / D)));
    for (const r of keep) r.day = Math.floor((r.slot * W) / D);
    for (const r of keep) all.push(r);
    console.error(`days ${chunk.join(",")}: windows ${keep.length}, labelled ${keep.filter((r) => r.label === 1).length}`);
  }
}
function* chunks(a, n) { for (let i = 0; i < a.length; i += n) yield a.slice(i, i + n); }

writeFileSync(`${ROOT}results/sealed-windows.csv`, toCsv(all));
console.error(`TOTAL windows ${all.length}, labelled ${all.filter((r) => r.label === 1).length}`);
