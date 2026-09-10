// Independent transfer check: day 12 (209 ground-truth events).
// History - days 0..11, observation - day 12. The model is NOT retrained:
// the same weights, trained on synthetic data only, are taken.
import { aggregate, toCsv } from "../judge/windows.mjs";
import { readFileSync, writeFileSync } from "node:fs";

const ROOT = new URL("..", import.meta.url).pathname;
const HISTORY_UNTIL = 1036800; // end of day 11
const EXAM_END = 1123200;      // end of day 12
const WINDOW = 3600;

const truthWindows = new Set();
for (const line of readFileSync(`${ROOT}data/redteam.txt`, "utf8").trim().split("\n")) {
  const [t, , src] = line.split(",");
  const time = Number(t);
  if (time >= HISTORY_UNTIL && time < EXAM_END) truthWindows.add(`${src}|${Math.floor(time / WINDOW)}`);
}
console.error(`ground truth: ${truthWindows.size} labelled windows in day 12`);

const { rows, seen } = await aggregate({
  path: `${ROOT}data/auth_d0_d12.csv.gz`,
  historyUntil: HISTORY_UNTIL, examEnd: EXAM_END, window: WINDOW,
  truth: (p, key) => truthWindows.has(key),
});
writeFileSync(`${ROOT}results/day12-windows.csv`, toCsv(rows));
console.error(`read ${seen}, windows ${rows.length}, labelled ${rows.filter(r => r.label === 1).length}`);
