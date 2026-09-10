// Window measurer ("the judge before the network") - computes from the login
// journal the features the network later learns on. The same code is applied
// to the synthetic data and to the real slice: if the measurer lies, both
// sides lie the same way, and the comparison stays fair.
//
// Unit of measurement: a SOURCE WINDOW - one computer over one time span.
// The key idea found in phase 0: raw counters are fooled by servers
// (a domain controller legitimately sees thousands of accounts), so we measure
// the NOVELTY OF EDGES of the login graph relative to the node's own history.
//
// Usage:
//   node judge/measure.mjs <file.csv[.gz]> --history-until=<sec> --window=<sec>
// Input format: time,user,source,destination,success

import { createReadStream } from "node:fs";
import { createInterface } from "node:readline";
import { createGunzip } from "node:zlib";

export function openLines(path) {
  const raw = createReadStream(path);
  const stream = path.endsWith(".gz") ? raw.pipe(createGunzip()) : raw;
  return createInterface({ input: stream, crlfDelay: Infinity });
}

// History is kept as sets of edges: which pairs were already seen before the window.
export function emptyHistory() {
  return {
    srcUsers: new Map(),   // source  -> Set(accounts that logged in from it)
    srcDsts: new Map(),    // source  -> Set(destinations)
    userDsts: new Map(),   // account -> Set(destinations)
    srcEvents: new Map(),  // source  -> how many events were seen
  };
}

function addTo(map, key, value) {
  let set = map.get(key);
  if (!set) map.set(key, (set = new Set()));
  set.add(value);
}

export function learn(history, ev) {
  addTo(history.srcUsers, ev.src, ev.user);
  addTo(history.srcDsts, ev.src, ev.dst);
  addTo(history.userDsts, ev.user, ev.dst);
  history.srcEvents.set(ev.src, (history.srcEvents.get(ev.src) ?? 0) + 1);
}

export function parseLine(line) {
  const p = line.split(",");
  if (p.length < 5) return null;
  const time = Number(p[0]);
  if (!Number.isFinite(time)) return null;
  return { time, user: p[1], src: p[2], dst: p[3], ok: p[4] === "Success" };
}

// Features of one window of one source. We keep them few and
// explainable - the article must be able to show each one.
export function featurize(events, history) {
  const src = events[0].src;
  const knownUsers = history.srcUsers.get(src) ?? new Set();
  const knownDsts = history.srcDsts.get(src) ?? new Set();
  const seenBefore = history.srcEvents.get(src) ?? 0;

  const users = new Set();
  const dsts = new Set();
  const newUsers = new Set();
  const newDsts = new Set();
  let newUserDstEdges = 0;
  let fails = 0;
  const times = [];

  for (const ev of events) {
    users.add(ev.user);
    dsts.add(ev.dst);
    if (!knownUsers.has(ev.user)) newUsers.add(ev.user);
    if (!knownDsts.has(ev.dst)) newDsts.add(ev.dst);
    const userSeen = history.userDsts.get(ev.user);
    if (!userSeen || !userSeen.has(ev.dst)) newUserDstEdges++;
    if (!ev.ok) fails++;
    times.push(ev.time);
  }

  // Rhythm: machine work is steadier than human work. Measured as the spread
  // of inter-event gaps (coefficient of variation), 0 - perfectly even.
  times.sort((a, b) => a - b);
  let rhythm = 0;
  if (times.length > 2) {
    const gaps = [];
    for (let i = 1; i < times.length; i++) gaps.push(times[i] - times[i - 1]);
    const mean = gaps.reduce((a, b) => a + b, 0) / gaps.length;
    if (mean > 0) {
      const varr = gaps.reduce((a, g) => a + (g - mean) ** 2, 0) / gaps.length;
      rhythm = Math.sqrt(varr) / mean;
    }
  }

  const n = events.length;
  return {
    src,
    events: n,
    users: users.size,
    dsts: dsts.size,
    newUsers: newUsers.size,
    newDsts: newDsts.size,
    // Novelty ratios - the very thing raw counters do not see.
    newUserRatio: users.size ? newUsers.size / users.size : 0,
    newDstRatio: dsts.size ? newDsts.size / dsts.size : 0,
    newEdgeRatio: n ? newUserDstEdges / n : 0,
    failRatio: n ? fails / n : 0,
    rhythm,
    // Node role context: a server has a huge history, a workstation a small one.
    historySize: seenBefore,
    knownUsers: knownUsers.size,
  };
}

// Run: build the history up to historyUntil, then cut the rest into windows.
export async function run(path, { historyUntil, window }) {
  const history = emptyHistory();
  const buckets = new Map(); // "source|window number" -> events

  const lines = openLines(path);
  for await (const line of lines) {
    const ev = parseLine(line);
    if (!ev) continue;
    if (ev.time < historyUntil) {
      learn(history, ev);
      continue;
    }
    const slot = Math.floor(ev.time / window);
    const key = `${ev.src}|${slot}`;
    let bucket = buckets.get(key);
    if (!bucket) buckets.set(key, (bucket = []));
    bucket.push(ev);
  }

  const rows = [];
  for (const [key, events] of buckets) {
    const slot = Number(key.split("|")[1]);
    const f = featurize(events, history);
    rows.push({ ...f, slot, windowStart: slot * window });
  }
  return rows;
}

const isMain = process.argv[1] && import.meta.url.endsWith(process.argv[1].split("/").pop());
if (isMain) {
  const [path] = process.argv.slice(2).filter((a) => !a.startsWith("--"));
  const arg = (name, dflt) => {
    const hit = process.argv.find((a) => a.startsWith(`--${name}=`));
    return hit ? Number(hit.split("=")[1]) : dflt;
  };
  const historyUntil = arg("history-until", 604800); // days 0..6 - history
  const window = arg("window", 3600);                // one-hour window

  const rows = await run(path, { historyUntil, window });
  process.stdout.write(
    "src,windowStart,events,users,dsts,newUsers,newDsts,newUserRatio,newDstRatio,newEdgeRatio,failRatio,rhythm,historySize,knownUsers\n"
  );
  for (const r of rows) {
    process.stdout.write(
      [r.src, r.windowStart, r.events, r.users, r.dsts, r.newUsers, r.newDsts,
       r.newUserRatio.toFixed(4), r.newDstRatio.toFixed(4), r.newEdgeRatio.toFixed(4),
       r.failRatio.toFixed(4), r.rhythm.toFixed(4), r.historySize, r.knownUsers].join(",") + "\n"
    );
  }
}
