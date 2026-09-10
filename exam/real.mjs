// THE MAIN EXAM: a network trained on synthetic data only, against the real
// LANL journal and the red-team labels. Real data was not used in training
// in any form.
import { readFileSync } from "node:fs";
import { encode } from "../net/train_encode.mjs";

const ROOT = new URL("..", import.meta.url).pathname;
const m = JSON.parse(readFileSync(`${ROOT}net/model.json`, "utf8"));
const [NIN, H1, H2] = m.arch;
const relu = (x) => (x > 0 ? x : 0);

function predict(x) {
  const h1 = new Float64Array(H1);
  for (let j = 0; j < H1; j++) { let s = m.b1[j]; for (let i = 0; i < NIN; i++) s += x[i] * m.w1[i * H1 + j]; h1[j] = relu(s); }
  const h2 = new Float64Array(H2);
  for (let j = 0; j < H2; j++) { let s = m.b2[j]; for (let i = 0; i < H1; i++) s += h1[i] * m.w2[i * H2 + j]; h2[j] = relu(s); }
  let s = m.b3[0];
  for (let i = 0; i < H2; i++) s += h2[i] * m.w3[i];
  return 1 / (1 + Math.exp(-s));
}

const [head, ...rows] = readFileSync(`${ROOT}results/day8-windows.csv`, "utf8").trim().split("\n");
const cols = head.split(",");
const idx = Object.fromEntries(cols.map((c, i) => [c, i]));
const data = rows.map((line) => {
  const p = line.split(",");
  const g = (c) => +p[idx[c]];
  return { src: p[idx.src], slot: g("slot"), label: g("label"),
    f: encode({ events: g("events"), users: g("users"), dsts: g("dsts"),
      newUsers: g("newUsers"), newDsts: g("newDsts"), newUserRatio: g("newUserRatio"),
      newDstRatio: g("newDstRatio"), newEdgeRatio: g("newEdgeRatio"), failRatio: g("failRatio"),
      rhythm: g("rhythm"), historySize: g("historySize"), knownUsers: g("knownUsers") }) };
});

for (const d of data) d.p = predict(d.f);
const pos = data.filter((d) => d.label === 1);
const neg = data.filter((d) => d.label === 0);
console.log(`windows ${data.length}, labelled ${pos.length}`);

console.log("\nthreshold | caught | false alarms | precision");
for (const thr of [0.5, 0.9, 0.99, 0.999]) {
  const tp = pos.filter((d) => d.p >= thr).length;
  const fp = neg.filter((d) => d.p >= thr).length;
  console.log(`${thr.toString().padEnd(6)}| ${tp}/${pos.length}     | ${fp}      | ${(tp / (tp + fp) || 0).toFixed(4)}`);
}

// rank measure: where the labelled windows stand in the overall list by confidence
const sorted = [...data].sort((a, b) => b.p - a.p);
const ranks = pos.map((d) => sorted.indexOf(d) + 1).sort((a, b) => a - b);
console.log(`\nranks of the labelled windows in the list by confidence: ${ranks.join(", ")}`);
console.log(`worst rank: ${ranks[ranks.length - 1]} of ${data.length}`);

// AUC
let auc = 0;
for (const p of pos) for (const n of neg) auc += p.p > n.p ? 1 : p.p === n.p ? 0.5 : 0;
console.log(`AUC = ${(auc / (pos.length * neg.length)).toFixed(5)}`);

console.log("\n=== top of the list by confidence (first 30) ===");
console.log("label src        events accounts newAcc newRatio failRatio history");
for (const d of sorted.slice(0, 30)) {
  const p = d.f;
  console.log(
    `${d.label ? "ATTACK" : "  -   "} ${d.src.padEnd(10)} ` +
    `p=${d.p.toFixed(4)}`
  );
}
