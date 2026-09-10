// Comparison with reference methods on the same windows.
// 1. A counter - "many different accounts from a source", the way threshold rules do it.
// 2. A rule picked WHILE LOOKING AT THE ANSWERS (phase 1) - the ceiling of hindsight wisdom.
// 3. Our network - trained on synthetic data only, has never seen real data.
import { readFileSync } from "node:fs";
import { encode } from "../net/train_encode.mjs";
import { loadRows } from "../judge/rows.mjs";
const ROOT = new URL("..", import.meta.url).pathname;
const file = process.argv[2] ?? "results/day8-windows.csv";

const m = JSON.parse(readFileSync(`${ROOT}net/model.json`, "utf8"));
const [NIN, H1, H2] = m.arch; const relu = (x) => (x > 0 ? x : 0);
function predict(x) {
  const h1 = new Float64Array(H1);
  for (let j = 0; j < H1; j++) { let s = m.b1[j]; for (let i = 0; i < NIN; i++) s += x[i] * m.w1[i * H1 + j]; h1[j] = relu(s); }
  const h2 = new Float64Array(H2);
  for (let j = 0; j < H2; j++) { let s = m.b2[j]; for (let i = 0; i < H1; i++) s += h1[i] * m.w2[i * H2 + j]; h2[j] = relu(s); }
  let s = m.b3[0]; for (let i = 0; i < H2; i++) s += h2[i] * m.w3[i];
  return 1 / (1 + Math.exp(-s));
}

// loading through the shared loader: it checks that ALL features are present
const D = loadRows(`${ROOT}${file}`).map((r) => ({
  label: r.label, users: r.users, events: r.events, dsts: r.dsts,
  nur: r.newUserRatio, fr: r.failRatio, hist: r.historySize,
  p: predict(encode(r)),
}));

const P = D.filter((d) => d.label === 1).length;
console.log(`windows ${D.length}, labelled ${P}\n`);

// One pass by sorting instead of sweeping thresholds: sort by descending
// score and walk down, counting hits and false alarms. The previous variant was
// quadratic and on 3.6M unique values simply never finished.
function sweep(score) {
  const arr = D.map((d) => [score(d), d.label]).sort((a, b) => b[0] - a[0]);
  const costAt = new Map(); // how many false alarms on the way to the N-th hit
  let tp = 0, fp = 0;
  for (const [, lab] of arr) {
    if (lab === 1) { tp++; if (!costAt.has(tp)) costAt.set(tp, fp); }
    else fp++;
  }
  return { costAt, arr };
}

// AUC by ranks (Mann-Whitney formula): one pass instead of pairwise enumeration
function aucOf(score) {
  const arr = D.map((d) => [score(d), d.label]).sort((a, b) => a[0] - b[0]);
  let rank = 1, sumPosRanks = 0, nPos = 0, nNeg = 0, i = 0;
  while (i < arr.length) {
    let j = i;
    while (j < arr.length && arr[j][0] === arr[i][0]) j++;
    const avgRank = (rank + (rank + (j - i) - 1)) / 2;
    for (let k = i; k < j; k++) {
      if (arr[k][1] === 1) { sumPosRanks += avgRank; nPos++; } else nNeg++;
    }
    rank += j - i; i = j;
  }
  return (sumPosRanks - (nPos * (nPos + 1)) / 2) / (nPos * nNeg);
}

function report(name, score) {
  const { costAt } = sweep(score);
  const auc = aucOf(score);
  console.log(name);
  console.log(`  AUC ${auc.toFixed(5)}`);
  console.log(costAt.has(P)
    ? `  to catch all ${P}, the alarm has to be raised ${costAt.get(P)} more times`
    : `  catching all ${P} is not possible`);
}

report("COUNTER: number of different accounts from a source", (d) => d.users);
report("COUNTER: number of destinations from a source", (d) => d.dsts);
report("RULE PICKED BY THE ANSWERS (phase 1)",
  (d) => (d.nur >= 0.9 && d.users >= 5 && d.dsts >= 10 && d.fr >= 0.15 ? 1 : 0));
report("OUR NETWORK (trained on synthetic data only)", (d) => d.p);

console.log("\n=== price per recall level (how many false alarms) ===");
const L=[Math.ceil(P*0.25),Math.ceil(P*0.5),Math.ceil(P*0.75)];
console.log(`method                                   ${L[0]}/${P}   ${L[1]}/${P}   ${L[2]}/${P}`);
function costs(name, score) {
  const { costAt } = sweep(score);
  console.log(name.padEnd(40) + L.map((n) => String(costAt.has(n) ? costAt.get(n) : "-").padStart(8)).join(""));
}

costs("counter: accounts from a source", (d) => d.users);
costs("counter: destinations from a source", (d) => d.dsts);
costs("rule picked by the answers", (d) => (d.nur >= 0.9 && d.users >= 5 && d.dsts >= 10 && d.fr >= 0.15 ? 1 : 0));
costs("our network (synthetic data only)", (d) => d.p);
