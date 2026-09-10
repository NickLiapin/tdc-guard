// Reading the window table. The only place where fields are fetched by name -
// so adding a feature cannot get "lost" in one of the exams
// (that is exactly how the NaN failure arose: an exam passed 12 fields out of 16).
import { readFileSync } from "node:fs";
import { FEATURE_NAMES } from "../net/train_encode.mjs";

export function loadRows(path) {
  const [head, ...lines] = readFileSync(path, "utf8").trim().split("\n");
  const idx = Object.fromEntries(head.split(",").map((c, i) => [c, i]));
  for (const f of FEATURE_NAMES) {
    if (!(f in idx)) throw new Error(`file ${path} has no feature "${f}" - the table is stale, recompute it with the measurer`);
  }
  return lines.map((line) => {
    const p = line.split(",");
    const r = { src: p[idx.src], slot: +p[idx.slot], label: +p[idx.label] };
    for (const f of FEATURE_NAMES) r[f] = +p[idx[f]];
    return r;
  });
}
