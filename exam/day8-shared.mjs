// Recomputing day 8 with the SHARED module - a check that the measurer is one and the same.
import { aggregate, toCsv } from "../judge/windows.mjs";
import { readFileSync, writeFileSync } from "node:fs";
const ROOT = new URL("..", import.meta.url).pathname;
const H = 691200, E = 777600, W = 3600;
const truth = new Set();
for (const line of readFileSync(`${ROOT}data/redteam.txt`, "utf8").trim().split("\n")) {
  const [t, , src] = line.split(",");
  const time = Number(t);
  if (time >= H && time < E) truth.add(`${src}|${Math.floor(time / W)}`);
}
const { rows, seen } = await aggregate({
  path: `${ROOT}data/auth_d0_d9.csv.gz`, historyUntil: H, examEnd: E, window: W,
  truth: (p, key) => truth.has(key),
});
writeFileSync(`${ROOT}results/day8-shared.csv`, toCsv(rows));
console.error(`read ${seen}, windows ${rows.length}, labelled ${rows.filter(r => r.label === 1).length}`);
