// Experiment: the baseline is FROZEN on days 0..7, the exam is day 12.
// Days 8..11 enter neither the history nor the windows: we check whether an
// early clean baseline saves it from its own poisoning.
// This is a working operator strategy ("take the reference in a known quiet period"),
// not peeking at the answers: which days exactly are poisoned, we do not use.
import { aggregate, toCsv } from "../judge/windows.mjs";
import { readFileSync, writeFileSync } from "node:fs";
const ROOT = new URL("..", import.meta.url).pathname;
const H = 691200, S = 1036800, E = 1123200, W = 3600;
const truth = new Set();
for (const line of readFileSync(`${ROOT}data/redteam.txt`, "utf8").trim().split("\n")) {
  const [t, , src] = line.split(",");
  const time = Number(t);
  if (time >= S && time < E) truth.add(`${src}|${Math.floor(time / W)}`);
}
const { rows, seen } = await aggregate({
  path: `${ROOT}data/auth_d0_d12.csv.gz`,
  historyUntil: H, examStart: S, examEnd: E, window: W,
  truth: (p, key) => truth.has(key),
});
writeFileSync(`${ROOT}results/day12-frozen-windows.csv`, toCsv(rows));
console.error(`read ${seen}, windows ${rows.length}, labelled ${rows.filter(r => r.label === 1).length}`);
