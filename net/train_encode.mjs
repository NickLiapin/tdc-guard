// Feature encoding - the ONLY definition, shared by training and all
// exams. Counters go under a logarithm: the absolute volumes of the synthetic
// world and the real network differ by orders of magnitude; the logarithm transfers, the raw count does not.
const L = (x) => Math.log1p(Math.max(0, x)) / 8;
export function encode(r) {
  return [
    L(r.events), L(r.users), L(r.dsts), L(r.newUsers), L(r.newDsts),
    r.newUserRatio, r.newDstRatio, r.newEdgeRatio, r.failRatio,
    Math.min(r.rhythm, 8) / 8,
    L(r.historySize), L(r.knownUsers),
    // event level: the share and the ABSOLUTE number of the most suspicious events,
    // so that a single foreign event in a large window does not drown in the average
    r.userSrcNewRatio, L(r.tripleNewCount), r.tripleNewRatio, L(r.minUserScope),
    L(r.movedUserCount), L(r.freshUserCount),
  ];
}
export const FEATURE_NAMES = [
  "events","users","dsts","newUsers","newDsts","newUserRatio","newDstRatio",
  "newEdgeRatio","failRatio","rhythm","historySize","knownUsers",
  "userSrcNewRatio","tripleNewCount","tripleNewRatio","minUserScope",
  "movedUserCount","freshUserCount",
];
