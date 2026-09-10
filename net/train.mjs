// A small fully connected network on window features. Hand-written in plain
// JS with no external libraries: exactly the same weights later go into the
// article page, and the reader checks the network in their own browser.
//
// Training is on synthetic data ONLY. The network never sees the real journal.
//
//   node net/train.mjs

import { readFileSync, writeFileSync } from "node:fs";
import { encode } from "./train_encode.mjs";

const ROOT = new URL("..", import.meta.url).pathname;

// --- reading the feature table ---
function load(path) {
  const [head, ...rows] = readFileSync(path, "utf8").trim().split("\n");
  const cols = head.split(",");
  const idx = Object.fromEntries(cols.map((c, i) => [c, i]));
  return rows.map((line) => {
    const p = line.split(",");
    const get = (c) => +p[idx[c]];
    return {
      src: p[idx.src],
      label: get("label"),
      f: encode({
        events: get("events"), users: get("users"), dsts: get("dsts"),
        newUsers: get("newUsers"), newDsts: get("newDsts"),
        newUserRatio: get("newUserRatio"), newDstRatio: get("newDstRatio"),
        newEdgeRatio: get("newEdgeRatio"), failRatio: get("failRatio"),
        rhythm: get("rhythm"), historySize: get("historySize"),
        knownUsers: get("knownUsers"),
        userSrcNewRatio: get("userSrcNewRatio"), tripleNewCount: get("tripleNewCount"),
        tripleNewRatio: get("tripleNewRatio"), minUserScope: get("minUserScope"),
        movedUserCount: get("movedUserCount"), freshUserCount: get("freshUserCount"),
      }),
    };
  });
}


const NIN = 18, H1 = 24, H2 = 12;

function init(n, m, scale) {
  const w = new Float64Array(n * m);
  let s = 12345;
  const rnd = () => ((s = (s * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff) * 2 - 1;
  for (let i = 0; i < w.length; i++) w[i] = rnd() * scale;
  return w;
}

const net = {
  w1: init(NIN, H1, Math.sqrt(2 / NIN)), b1: new Float64Array(H1),
  w2: init(H1, H2, Math.sqrt(2 / H1)), b2: new Float64Array(H2),
  w3: init(H2, 1, Math.sqrt(2 / H2)), b3: new Float64Array(1),
};
const nParams = net.w1.length + net.b1.length + net.w2.length + net.b2.length + net.w3.length + 1;

const relu = (x) => (x > 0 ? x : 0);
const sigmoid = (x) => 1 / (1 + Math.exp(-x));

function forward(x) {
  const h1 = new Float64Array(H1);
  for (let j = 0; j < H1; j++) {
    let s = net.b1[j];
    for (let i = 0; i < NIN; i++) s += x[i] * net.w1[i * H1 + j];
    h1[j] = relu(s);
  }
  const h2 = new Float64Array(H2);
  for (let j = 0; j < H2; j++) {
    let s = net.b2[j];
    for (let i = 0; i < H1; i++) s += h1[i] * net.w2[i * H2 + j];
    h2[j] = relu(s);
  }
  let s = net.b3[0];
  for (let i = 0; i < H2; i++) s += h2[i] * net.w3[i];
  return { h1, h2, p: sigmoid(s) };
}

function trainStep(batch, lr) {
  const g1 = new Float64Array(net.w1.length), gb1 = new Float64Array(H1);
  const g2 = new Float64Array(net.w2.length), gb2 = new Float64Array(H2);
  const g3 = new Float64Array(net.w3.length); let gb3 = 0;
  let loss = 0;

  for (const { f: x, label: y, weight } of batch) {
    const { h1, h2, p } = forward(x);
    const w = weight ?? 1;
    loss += -w * (y * Math.log(p + 1e-9) + (1 - y) * Math.log(1 - p + 1e-9));
    const dOut = (p - y) * w;

    const dh2 = new Float64Array(H2);
    for (let i = 0; i < H2; i++) {
      g3[i] += dOut * h2[i];
      dh2[i] = h2[i] > 0 ? dOut * net.w3[i] : 0;
    }
    gb3 += dOut;

    const dh1 = new Float64Array(H1);
    for (let i = 0; i < H1; i++) {
      let acc = 0;
      for (let j = 0; j < H2; j++) {
        g2[i * H2 + j] += dh2[j] * h1[i];
        acc += dh2[j] * net.w2[i * H2 + j];
      }
      dh1[i] = h1[i] > 0 ? acc : 0;
    }
    for (let j = 0; j < H2; j++) gb2[j] += dh2[j];

    for (let i = 0; i < NIN; i++)
      for (let j = 0; j < H1; j++) g1[i * H1 + j] += dh1[j] * x[i];
    for (let j = 0; j < H1; j++) gb1[j] += dh1[j];
  }

  const n = batch.length;
  for (let i = 0; i < net.w1.length; i++) net.w1[i] -= (lr * g1[i]) / n;
  for (let i = 0; i < H1; i++) net.b1[i] -= (lr * gb1[i]) / n;
  for (let i = 0; i < net.w2.length; i++) net.w2[i] -= (lr * g2[i]) / n;
  for (let i = 0; i < H2; i++) net.b2[i] -= (lr * gb2[i]) / n;
  for (let i = 0; i < net.w3.length; i++) net.w3[i] -= (lr * g3[i]) / n;
  net.b3[0] -= (lr * gb3) / n;
  return loss / n;
}

function evaluate(rows, thr = 0.5) {
  let tp = 0, fp = 0, fn = 0, tn = 0;
  for (const r of rows) {
    const p = forward(r.f).p;
    const hit = p >= thr;
    if (r.label === 1) hit ? tp++ : fn++;
    else hit ? fp++ : tn++;
  }
  const prec = tp + fp ? tp / (tp + fp) : 0;
  const rec = tp + fn ? tp / (tp + fn) : 0;
  return { tp, fp, fn, tn, prec, rec, f1: prec + rec ? (2 * prec * rec) / (prec + rec) : 0 };
}

// --- training ---
const train = load(`${ROOT}results/synth-train-windows.csv`);
const pos = train.filter((r) => r.label === 1).length;
console.log(`training windows ${train.length}, labelled ${pos}`);
console.log(`weights in the network: ${nParams}`);

// the rare class weighs more - otherwise the network simply learns to stay silent
const posWeight = (train.length - pos) / pos;
for (const r of train) r.weight = r.label === 1 ? posWeight : 1;

let seed = 7;
const rnd = () => ((seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff);
const BATCH = 128;
for (let epoch = 1; epoch <= 60; epoch++) {
  const shuffled = [...train].sort(() => rnd() - 0.5);
  let loss = 0, steps = 0;
  for (let i = 0; i < shuffled.length; i += BATCH) {
    loss += trainStep(shuffled.slice(i, i + BATCH), 0.35);
    steps++;
  }
  if (epoch % 15 === 0) {
    const e = evaluate(train);
    console.log(`epoch ${epoch}: loss ${(loss / steps).toFixed(4)}, F1 on training ${e.f1.toFixed(4)}`);
  }
}

// --- internal exam: synthetic data with another seed ---
const synthExam = load(`${ROOT}results/synth-exam-windows.csv`);
const se = evaluate(synthExam);
console.log(`\ninternal exam (synthetic data, another seed): precision ${se.prec.toFixed(4)}, recall ${se.rec.toFixed(4)}, F1 ${se.f1.toFixed(4)}`);
console.log(`  correct ${se.tp}, missed ${se.fn}, false alarms ${se.fp} out of ${se.tn + se.fp} normal`);

writeFileSync(`${ROOT}net/model.json`, JSON.stringify({
  arch: [NIN, H1, H2, 1], params: nParams,
  w1: [...net.w1], b1: [...net.b1], w2: [...net.w2], b2: [...net.b2],
  w3: [...net.w3], b3: [...net.b3],
}));
console.log("weights saved to net/model.json");
