// Shared window measurer - the ONLY place where features are computed.
// It measures both the synthetic data and the real LANL journal. If the measurer
// is wrong, it is wrong for both sides the same way, and the comparison stays fair.
// (Lesson from tdc-ecg: both first "generator defects" turned out to be judge defects.)
//
// Journal line format: time,account,source,destination,outcome[,truth]
// The sixth field is the truth label in the synthetic data; it does NOT enter the features.

import { createReadStream } from "node:fs";
import { createInterface } from "node:readline";
import { createGunzip } from "node:zlib";

export function lines(path) {
  const raw = createReadStream(path);
  const stream = path.endsWith(".gz") ? raw.pipe(createGunzip()) : raw;
  return createInterface({ input: stream, crlfDelay: Infinity });
}

export const FEATURES = [
  "events", "users", "dsts", "newUsers", "newDsts",
  "newUserRatio", "newDstRatio", "newEdgeRatio", "failRatio", "rhythm",
  "historySize", "knownUsers",
  // EVENT-level features. Ratios are averages, and an average drowns a single
  // event: a real window can hold 1 foreign event among 37 ordinary ones. So
  // next to the ratio goes the ABSOLUTE number of the most suspicious events.
  "userSrcNewRatio",  // share of events where the account is on this machine for the first time
  "tripleNewCount",   // HOW MANY events have all three edges new at once
  "tripleNewRatio",   // and what share that is
  "minUserScope",     // the 'narrowest' account of the window: how many machines it knew
  "movedUserCount",   // account KNOWN to the network, but first time on this machine
  "freshUserCount",   // account never seen in the network at all (new employee, service account)
];

// One streaming pass: up to historyUntil the login graph history is built,
// after it the window features accumulate. Events are not stored in memory.
// examStart: if given, events between historyUntil and examStart are ignored
// entirely - this is how the baseline is "frozen" on an early clean period.
export async function aggregate({ path, historyUntil, examStart, examEnd, window, truth }) {
  const srcUsers = new Map(), srcDsts = new Map(), userDsts = new Map(), srcEvents = new Map();
  const userSrcs = new Map(); // account -> machines it logged in from
  const add = (map, k, v) => {
    let s = map.get(k);
    if (!s) map.set(k, (s = new Set()));
    s.add(v);
  };

  const win = new Map();
  let seen = 0;

  for await (const line of lines(path)) {
    const p = line.split(",");
    if (p.length < 5) continue;
    const time = +p[0];
    if (!Number.isFinite(time)) continue;
    if (time >= examEnd) break;
    const user = p[1], src = p[2], dst = p[3], ok = p[4] === "Success";
    seen++;

    if (time < historyUntil) {
      add(srcUsers, src, user);
      add(srcDsts, src, dst);
      add(userDsts, user, dst);
      add(userSrcs, user, src);
      srcEvents.set(src, (srcEvents.get(src) ?? 0) + 1);
      continue;
    }

    if (examStart !== undefined && time < examStart) continue;

    const slot = Math.floor(time / window);
    const key = `${src}|${slot}`;
    let b = win.get(key);
    if (!b) {
      win.set(key, (b = {
        src, slot, events: 0, fails: 0, truth: 0,
        users: new Set(), dsts: new Set(), newUsers: new Set(), newDsts: new Set(),
        newEdges: 0, lastTime: null, gapN: 0, gapSum: 0, gapSq: 0,
        userSrcNew: 0, tripleNew: 0, minScope: Infinity, moved: 0, fresh: 0,
      }));
    }
    b.events++;
    if (!ok) b.fails++;
    b.users.add(user);
    b.dsts.add(dst);
    if (!srcUsers.get(src)?.has(user)) b.newUsers.add(user);
    if (!srcDsts.get(src)?.has(dst)) b.newDsts.add(dst);
    const udNew = !userDsts.get(user)?.has(dst);
    if (udNew) b.newEdges++;
    // three axes of novelty of one event
    const usNew = !userSrcs.get(user)?.has(src);
    const sdNew = !srcDsts.get(src)?.has(dst);
    if (usNew) b.userSrcNew++;
    if (usNew && sdNew && udNew) b.tripleNew++;
    // how "attached" the account is: an account that knew one machine and surfaced
    // on another is more suspicious than a roaming administrator
    const scope = userSrcs.get(user)?.size ?? 0;
    if (scope < b.minScope) b.minScope = scope;
    // separate the two reasons an account is new on a machine
    if (usNew) { if (scope > 0) b.moved++; else b.fresh++; }
    if (b.lastTime !== null) {
      const g = time - b.lastTime;
      b.gapN++; b.gapSum += g; b.gapSq += g * g;
    }
    b.lastTime = time;
    if (truth && truth(p, key)) b.truth = 1;
  }

  const rows = [];
  for (const b of win.values()) {
    let rhythm = 0;
    if (b.gapN > 1) {
      const mean = b.gapSum / b.gapN;
      if (mean > 0) {
        const varr = Math.max(0, b.gapSq / b.gapN - mean * mean);
        rhythm = Math.sqrt(varr) / mean;
      }
    }
    rows.push({
      src: b.src, slot: b.slot, label: b.truth,
      events: b.events, users: b.users.size, dsts: b.dsts.size,
      newUsers: b.newUsers.size, newDsts: b.newDsts.size,
      newUserRatio: b.users.size ? b.newUsers.size / b.users.size : 0,
      newDstRatio: b.dsts.size ? b.newDsts.size / b.dsts.size : 0,
      newEdgeRatio: b.events ? b.newEdges / b.events : 0,
      failRatio: b.events ? b.fails / b.events : 0,
      rhythm,
      historySize: srcEvents.get(b.src) ?? 0,
      knownUsers: srcUsers.get(b.src)?.size ?? 0,
      userSrcNewRatio: b.events ? b.userSrcNew / b.events : 0,
      tripleNewCount: b.tripleNew,
      tripleNewRatio: b.events ? b.tripleNew / b.events : 0,
      minUserScope: Number.isFinite(b.minScope) ? b.minScope : 0,
      movedUserCount: b.moved,
      freshUserCount: b.fresh,
    });
  }
  return { rows, seen };
}

export function toCsv(rows) {
  const head = ["src", "slot", "label", ...FEATURES].join(",");
  const body = rows.map((r) =>
    [r.src, r.slot, r.label, ...FEATURES.map((f) => {
      const v = r[f];
      return Number.isInteger(v) ? v : v.toFixed(4);
    })].join(",")
  );
  return head + "\n" + body.join("\n") + "\n";
}
