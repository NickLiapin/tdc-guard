// Scoring the network on a ready window table. The weights are not touched - only applied.
import { readFileSync } from "node:fs";
import { encode } from "../net/train_encode.mjs";
import { loadRows } from "../judge/rows.mjs";

const ROOT = new URL("..", import.meta.url).pathname;
const file = process.argv[2];
const m = JSON.parse(readFileSync(`${ROOT}net/model.json`, "utf8"));
const [NIN, H1, H2] = m.arch;
const relu = (x) => (x > 0 ? x : 0);
function predict(x) {
  const h1 = new Float64Array(H1);
  for (let j = 0; j < H1; j++) { let s = m.b1[j]; for (let i = 0; i < NIN; i++) s += x[i] * m.w1[i * H1 + j]; h1[j] = relu(s); }
  const h2 = new Float64Array(H2);
  for (let j = 0; j < H2; j++) { let s = m.b2[j]; for (let i = 0; i < H1; i++) s += h1[i] * m.w2[i * H2 + j]; h2[j] = relu(s); }
  let s = m.b3[0]; for (let i = 0; i < H2; i++) s += h2[i] * m.w3[i];
  return 1 / (1 + Math.exp(-s));
}

const data = loadRows(`${ROOT}${file}`).map((r) => ({ ...r, hist: r.historySize,
  ev: r.events, users: r.users, dsts: r.dsts, nur: r.newUserRatio, fr: r.failRatio,
  p: predict(encode(r)) }));

const pos = data.filter((d) => d.label === 1), neg = data.filter((d) => d.label === 0);
console.log(`windows ${data.length}, labelled ${pos.length}`);
console.log("\nthreshold | caught | false alarms | precision");
for (const thr of [0.5, 0.9, 0.99, 0.999]) {
  const tp = pos.filter((d) => d.p >= thr).length, fp = neg.filter((d) => d.p >= thr).length;
  console.log(`${String(thr).padEnd(6)}| ${tp}/${pos.length}`.padEnd(22) + `| ${String(fp).padEnd(7)}| ${(tp / (tp + fp) || 0).toFixed(4)}`);
}
const sorted = [...data].sort((a, b) => b.p - a.p);
const ranks = pos.map((d) => sorted.indexOf(d) + 1).sort((a, b) => a - b);
console.log(`\nworst rank of a labelled window: ${ranks[ranks.length - 1]} of ${data.length}`);
console.log(`first ranks: ${ranks.slice(0, 12).join(", ")}${ranks.length > 12 ? " ..." : ""}`);
let auc = 0;
for (const p of pos) for (const n of neg) auc += p.p > n.p ? 1 : p.p === n.p ? 0.5 : 0;
console.log(`AUC = ${(auc / (pos.length * neg.length)).toFixed(5)}`);
const fpHigh = neg.filter((d) => d.p >= 0.99);
console.log(`\nfalse alarms at 0.99: ${fpHigh.length}, of them new hosts (history=0): ${fpHigh.filter((d) => d.hist === 0).length}`);
const bySrc = {};
for (const d of fpHigh) bySrc[d.src] = (bySrc[d.src] || 0) + 1;
console.log("by machine:", Object.entries(bySrc).sort((a, b) => b[1] - a[1]).slice(0, 12).map(([k, v]) => `${k}:${v}`).join("  "));
