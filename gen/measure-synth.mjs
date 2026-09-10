// Measures a synthetic journal with the same measurer as the real one.
// The truth is taken from the sixth field (the event label) and never enters the features.
import { aggregate, toCsv } from "../judge/windows.mjs";
import { writeFileSync } from "node:fs";

const path = process.argv[2];
const out = process.argv[3];
// the third argument is the baseline length; by default the whole first period.
// A short baseline reproduces the "early day" regime where the networks make mistakes.
const hist = process.argv[4] ? Number(process.argv[4]) : 28800;
const { rows, seen } = await aggregate({
  path,
  historyUntil: hist,
  examEnd: 28800 + 15 * 3600, // we observe 15 hours
  window: 3600,
  truth: (p) => p[5] === "1",
});
writeFileSync(out, toCsv(rows));
const pos = rows.filter((r) => r.label === 1).length;
console.error(`read ${seen}, windows ${rows.length}, labelled ${pos}`);
