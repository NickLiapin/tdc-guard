// The main phase 1 measurement: a run of the judge over the real LANL journal.
// History - days 0..7, the exam window - day 8 (the densest in red-team
// labels: 273 events out of 749).
//
// One stream, aggregation on the fly: 72M events do not fit in memory,
// so the window features accumulate incrementally.
//
//   node --max-old-space-size=8192 exam/day8.mjs

import { createReadStream } from "node:fs";
import { createInterface } from "node:readline";
import { createGunzip } from "node:zlib";
import { readFileSync, writeFileSync } from "node:fs";

const SLICE = new URL("../data/auth_d0_d9.csv.gz", import.meta.url).pathname;
const TRUTH = new URL("../data/redteam.txt", import.meta.url).pathname;
const HISTORY_UNTIL = 691200; // end of day 7
const EXAM_END = 777600;      // end of day 8
const WINDOW = 3600;          // one-hour window

// --- ground truth: which (source, window) pairs contain red-team activity ---
const truthWindows = new Set();
const truthSrc = new Set();
for (const line of readFileSync(TRUTH, "utf8").trim().split("\n")) {
  const [t, , src] = line.split(",");
  const time = Number(t);
  truthSrc.add(src);
  if (time >= HISTORY_UNTIL && time < EXAM_END) {
    truthWindows.add(`${src}|${Math.floor(time / WINDOW)}`);
  }
}
console.error(`ground truth: ${truthWindows.size} labelled windows in day 8, sources in total ${truthSrc.size}`);

// --- history as sets of edges of the login graph ---
const srcUsers = new Map();
const srcDsts = new Map();
const userDsts = new Map();
const srcEvents = new Map();

function addTo(map, key, value) {
  let set = map.get(key);
  if (!set) map.set(key, (set = new Set()));
  set.add(value);
}

// --- window accumulators (source|slot) ---
const win = new Map();

function bucket(key, src, slot) {
  let b = win.get(key);
  if (!b) {
    win.set(key, (b = {
      src, slot, events: 0, fails: 0,
      users: new Set(), dsts: new Set(),
      newUsers: new Set(), newDsts: new Set(),
      newEdges: 0, lastTime: null, gapN: 0, gapSum: 0, gapSq: 0,
    }));
  }
  return b;
}

const lines = createInterface({
  input: createReadStream(SLICE).pipe(createGunzip()),
  crlfDelay: Infinity,
});

let seen = 0;
for await (const line of lines) {
  const p = line.split(",");
  if (p.length < 5) continue;
  const time = +p[0];
  if (time >= EXAM_END) break;
  const user = p[1], src = p[2], dst = p[3], ok = p[4] === "Success";

  if (++seen % 10_000_000 === 0) console.error(`  read ${seen / 1e6} million, t=${time}`);

  if (time < HISTORY_UNTIL) {
    addTo(srcUsers, src, user);
    addTo(srcDsts, src, dst);
    addTo(userDsts, user, dst);
    srcEvents.set(src, (srcEvents.get(src) ?? 0) + 1);
    continue;
  }

  const slot = Math.floor(time / WINDOW);
  const b = bucket(`${src}|${slot}`, src, slot);
  b.events++;
  if (!ok) b.fails++;
  b.users.add(user);
  b.dsts.add(dst);
  if (!(srcUsers.get(src)?.has(user))) b.newUsers.add(user);
  if (!(srcDsts.get(src)?.has(dst))) b.newDsts.add(dst);
  if (!(userDsts.get(user)?.has(dst))) b.newEdges++;
  if (b.lastTime !== null) {
    const g = time - b.lastTime;
    b.gapN++; b.gapSum += g; b.gapSq += g * g;
  }
  b.lastTime = time;
}
console.error(`read ${seen} events in total, windows collected ${win.size}`);

// --- writing out the features ---
const out = ["src,slot,label,events,users,dsts,newUsers,newDsts,newUserRatio,newDstRatio,newEdgeRatio,failRatio,rhythm,historySize,knownUsers"];
for (const [key, b] of win) {
  const label = truthWindows.has(key) ? 1 : 0;
  let rhythm = 0;
  if (b.gapN > 1) {
    const mean = b.gapSum / b.gapN;
    if (mean > 0) {
      const varr = Math.max(0, b.gapSq / b.gapN - mean * mean);
      rhythm = Math.sqrt(varr) / mean;
    }
  }
  out.push([
    b.src, b.slot, label, b.events, b.users.size, b.dsts.size,
    b.newUsers.size, b.newDsts.size,
    (b.users.size ? b.newUsers.size / b.users.size : 0).toFixed(4),
    (b.dsts.size ? b.newDsts.size / b.dsts.size : 0).toFixed(4),
    (b.events ? b.newEdges / b.events : 0).toFixed(4),
    (b.events ? b.fails / b.events : 0).toFixed(4),
    rhythm.toFixed(4),
    srcEvents.get(b.src) ?? 0,
    srcUsers.get(b.src)?.size ?? 0,
  ].join(","));
}
writeFileSync(new URL("../results/day8-windows.csv", import.meta.url).pathname, out.join("\n") + "\n");
console.error(`wrote ${out.length - 1} rows to results/day8-windows.csv`);
