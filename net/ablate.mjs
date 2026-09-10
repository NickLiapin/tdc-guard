// Ablation: train the network on a subset of features and measure on day 8.
// The goal is to find which of the new features breaks the transfer.
import { readFileSync, writeFileSync } from "node:fs";
import { execSync } from "node:child_process";
import { FEATURE_NAMES } from "./train_encode.mjs";
import { loadRows } from "../judge/rows.mjs";
const ROOT = new URL("..", import.meta.url).pathname;

const drop = (process.argv[2] ?? "").split(",").filter(Boolean);
const keep = FEATURE_NAMES.map((n, i) => [n, i]).filter(([n]) => !drop.includes(n));
const L = (x) => Math.log1p(Math.max(0, x)) / 8;
const RAW = { events: L, users: L, dsts: L, newUsers: L, newDsts: L,
  newUserRatio: (v) => v, newDstRatio: (v) => v, newEdgeRatio: (v) => v, failRatio: (v) => v,
  rhythm: (v) => Math.min(v, 8) / 8, historySize: L, knownUsers: L,
  userSrcNewRatio: (v) => v, tripleNewCount: L, tripleNewRatio: (v) => v, minUserScope: L };
const enc = (r) => keep.map(([n]) => RAW[n](r[n]));

const NIN = keep.length, H1 = 24, H2 = 12;
const init = (n, m, sc) => { const w = new Float64Array(n * m); let s = 12345;
  const rnd = () => ((s = (s * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff) * 2 - 1;
  for (let i = 0; i < w.length; i++) w[i] = rnd() * sc; return w; };
const net = { w1: init(NIN, H1, Math.sqrt(2 / NIN)), b1: new Float64Array(H1),
  w2: init(H1, H2, Math.sqrt(2 / H1)), b2: new Float64Array(H2),
  w3: init(H2, 1, Math.sqrt(2 / H2)), b3: new Float64Array(1) };
const relu = (x) => (x > 0 ? x : 0);
function fwd(x) {
  const h1 = new Float64Array(H1);
  for (let j = 0; j < H1; j++) { let s = net.b1[j]; for (let i = 0; i < NIN; i++) s += x[i] * net.w1[i * H1 + j]; h1[j] = relu(s); }
  const h2 = new Float64Array(H2);
  for (let j = 0; j < H2; j++) { let s = net.b2[j]; for (let i = 0; i < H1; i++) s += h1[i] * net.w2[i * H2 + j]; h2[j] = relu(s); }
  let s = net.b3[0]; for (let i = 0; i < H2; i++) s += h2[i] * net.w3[i];
  return { h1, h2, p: 1 / (1 + Math.exp(-s)) };
}
function step(batch, lr) {
  const g1 = new Float64Array(net.w1.length), gb1 = new Float64Array(H1);
  const g2 = new Float64Array(net.w2.length), gb2 = new Float64Array(H2);
  const g3 = new Float64Array(net.w3.length); let gb3 = 0;
  for (const { f: x, label: y, weight: w } of batch) {
    const { h1, h2, p } = fwd(x); const dOut = (p - y) * w;
    const dh2 = new Float64Array(H2);
    for (let i = 0; i < H2; i++) { g3[i] += dOut * h2[i]; dh2[i] = h2[i] > 0 ? dOut * net.w3[i] : 0; }
    gb3 += dOut;
    const dh1 = new Float64Array(H1);
    for (let i = 0; i < H1; i++) { let a = 0;
      for (let j = 0; j < H2; j++) { g2[i * H2 + j] += dh2[j] * h1[i]; a += dh2[j] * net.w2[i * H2 + j]; }
      dh1[i] = h1[i] > 0 ? a : 0; }
    for (let j = 0; j < H2; j++) gb2[j] += dh2[j];
    for (let i = 0; i < NIN; i++) for (let j = 0; j < H1; j++) g1[i * H1 + j] += dh1[j] * x[i];
    for (let j = 0; j < H1; j++) gb1[j] += dh1[j];
  }
  const n = batch.length;
  for (let i = 0; i < net.w1.length; i++) net.w1[i] -= (lr * g1[i]) / n;
  for (let i = 0; i < H1; i++) net.b1[i] -= (lr * gb1[i]) / n;
  for (let i = 0; i < net.w2.length; i++) net.w2[i] -= (lr * g2[i]) / n;
  for (let i = 0; i < H2; i++) net.b2[i] -= (lr * gb2[i]) / n;
  for (let i = 0; i < net.w3.length; i++) net.w3[i] -= (lr * g3[i]) / n;
  net.b3[0] -= (lr * gb3) / n;
}
const train = loadRows(`${ROOT}results/synth-train-windows.csv`).map((r) => ({ f: enc(r), label: r.label }));
const P = train.filter((r) => r.label === 1).length;
const pw = (train.length - P) / P;
for (const r of train) r.weight = r.label === 1 ? pw : 1;
let sd = 7; const rnd = () => ((sd = (sd * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff);
for (let e = 0; e < 60; e++) { const sh = [...train].sort(() => rnd() - 0.5);
  for (let i = 0; i < sh.length; i += 128) step(sh.slice(i, i + 128), 0.35); }

const real = loadRows(`${ROOT}results/day8-shared.csv`).map((r) => ({ p: fwd(enc(r)).p, label: r.label }));
const pos = real.filter((d) => d.label === 1), neg = real.filter((d) => d.label === 0);
const sorted = [...real].sort((a, b) => b.p - a.p);
const worst = Math.max(...pos.map((d) => sorted.indexOf(d) + 1));
const fp99 = neg.filter((d) => d.p >= 0.99).length;
const tp99 = pos.filter((d) => d.p >= 0.99).length;
let auc = 0; for (const p of pos) for (const n of neg) auc += p.p > n.p ? 1 : p.p === n.p ? 0.5 : 0;
console.log(`without [${drop.join(",") || "nothing"}]  features ${NIN}  caught@0.99 ${tp99}/15  false alarms ${String(fp99).padStart(5)}  worst rank ${String(worst).padStart(6)}  AUC ${(auc / (pos.length * neg.length)).toFixed(5)}`);
