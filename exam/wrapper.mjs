// A temporal wrapper around the network: the windows of one machine stop being judged separately.
// All rules are CAUSAL - they look only into the past, the way it would work in
// real life. The network is not retrained: its output is taken and processed on top.
import { loadRows } from "../judge/rows.mjs";
import { encode } from "../net/train_encode.mjs";
import { readFileSync } from "node:fs";
const ROOT = new URL("..", import.meta.url).pathname;
const m = JSON.parse(readFileSync(`${ROOT}net/model.json`, "utf8"));
const [NIN, H1, H2] = m.arch, relu = (x) => (x > 0 ? x : 0);
function predict(x) {
  const h1 = new Float64Array(H1);
  for (let j = 0; j < H1; j++) { let s = m.b1[j]; for (let i = 0; i < NIN; i++) s += x[i] * m.w1[i * H1 + j]; h1[j] = relu(s); }
  const h2 = new Float64Array(H2);
  for (let j = 0; j < H2; j++) { let s = m.b2[j]; for (let i = 0; i < H1; i++) s += h1[i] * m.w2[i * H2 + j]; h2[j] = relu(s); }
  let s = m.b3[0]; for (let i = 0; i < H2; i++) s += h2[i] * m.w3[i];
  return 1 / (1 + Math.exp(-s));
}

export function scoreFile(file) {
  const rows = loadRows(`${ROOT}${file}`);
  for (const r of rows) r.p = predict(encode(r));

  // group by machine and order by time
  const byHost = new Map();
  for (const r of rows) {
    let a = byHost.get(r.src);
    if (!a) byHost.set(r.src, (a = []));
    a.push(r);
  }
  for (const arr of byHost.values()) {
    arr.sort((a, b) => a.slot - b.slot);
    const seen = [];
    for (const r of arr) {
      // 1. accumulation: suspicion with decay
      const prevAcc = seen.length ? seen[seen.length - 1].acc : 0;
      r.acc = Math.max(r.p, 0.75 * prevAcc);
      // 2. deviation from this machine's OWN past for today
      if (seen.length >= 2) {
        const past = seen.map((x) => x.p).sort((a, b) => a - b);
        const med = past[Math.floor(past.length / 2)];
        r.dev = Math.max(0, r.p - med);
      } else {
        r.dev = 0; // no baseline, no judgement - the machine has only just appeared
      }
      // 3. combination: suspicion confirmed by deviation
      r.mix = r.p * (0.35 + 0.65 * Math.min(1, r.dev * 3));
      seen.push(r);
    }
  }
  return rows;
}

function report(rows, key, name) {
  const pos = rows.filter((r) => r.label === 1), neg = rows.filter((r) => r.label === 0);
  const sorted = [...rows].sort((a, b) => b[key] - a[key]);
  const ranks = pos.map((r) => sorted.indexOf(r) + 1).sort((a, b) => a - b);
  // price of full recall: how many false alarms on the way to the N-th hit
  const cost = (n) => (ranks.length >= n ? ranks[n - 1] - n : "-");
  let auc = 0;
  for (const p of pos) for (const q of neg) auc += p[key] > q[key] ? 1 : p[key] === q[key] ? 0.5 : 0;
  console.log(
    `${name.padEnd(28)} false alarms before ${Math.ceil(pos.length * 0.5)}/${pos.length}: ${String(cost(Math.ceil(pos.length * 0.5))).padStart(6)}` +
    `  before ${pos.length - 2}: ${String(cost(pos.length - 2)).padStart(7)}` +
    `  worst rank ${String(ranks[ranks.length - 1]).padStart(6)}  AUC ${(auc / (pos.length * neg.length)).toFixed(5)}`
  );
}

for (const [file, label] of [["results/day8-shared.csv", "DAY 8"], ["results/day12-frozen-windows.csv", "DAY 12"]]) {
  console.log(`\n=== ${label} ===`);
  const rows = scoreFile(file);
  report(rows, "p", "network as is");
  report(rows, "acc", "accumulation with decay");
  report(rows, "dev", "deviation from own past");
  report(rows, "mix", "suspicion x deviation");
}
