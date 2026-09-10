Russian version: [DIARY.ru.md](DIARY.ru.md)

The project's lab journal: measurements and decisions in the order they were
made, including the moves that failed. The numbers here are raw; the summary
with honesty notes lives in FACTS.md.

# tdc-guard project diary

This is the record of WHY each decision was made and what was measured; the
summary with the numbers is in FACTS.md. Kept as a running narrative, while
everything is fresh; every number is real and reproducible.

---

## 2026-08-30 - Phase 0: the exam is opened, the problem statement is settled

**What was done.** Downloaded the labelled LANL "ground truth" and a streamed
slice of the authentication log; measured both before a single line of config
was written (the order borrowed from tdc-ecg: exam first, generator second).

**Data source.** LANL's own site (`csr.lanl.gov`) only serves the files through
a form. The academic mirror at Imperial College London
(`lanl.ma.ic.ac.uk/data/cyber1/`) serves them directly and supports range
requests. `redteam.txt.gz` is 4.8 KB and was taken whole. `auth.txt.gz` is
7.2 GB; a streamed slice of the first 1.5 million lines was taken (the first
~4 hours of observation).

**Log format (auth.txt), 9 fields:**
`time, srcuser@domain, dstuser@domain, srccomp, dstcomp, type, logontype,
orientation, Success/Fail`.

**Ground-truth format (redteam.txt), 4 fields:**
`time, user@domain, srccomp, dstcomp` - 749 labelled events.

### What is labelled as red-team activity

- 749 events, **104** unique accounts, **301** unique destinations.
- Only **4** sources, and 701 of 749 (94%) come from a single foothold,
  **C17693** (the rest: C22409, C19932, C18025).
- Time range: 150 885 ... 2 557 047 s (roughly day 1.7 to day 29.6 of 58).

**Conclusion about the nature of the phenomenon.** This is NOT password
guessing. This is lateral movement on other people's accounts: from a handful
of footholds, they go to many places under many valid accounts. The risk
written into the plan beforehand is borne out by the facts.

### Three measurements that settled the problem statement

1. **The account on its own gives nothing away.** The top red-team "victim",
   U66 (118 labelled events), appears **30 497** times in the clean four-hour
   slice - it is the most active regular account there is. So the signal is
   not in WHOSE account it is but in WHERE it came from.
2. **A naive counter is fooled by servers.** Take "number of distinct accounts
   from a source": C586/C529/C467 have 2500-3000 (domain controllers - they
   legitimately see everyone), then a drop to the workstations (hundreds down
   to single digits). A foothold with 104 accounts would land in the middle of
   the range and be mistaken for a small server. The same thing fools "number
   of destinations from a source" (servers 130-2079, workstations single
   digits).
3. **The real discriminator is relational.** Lateral movement creates **new
   edges** in the login graph: a "(source -> account)" or "(account ->
   destination)" pair that was never in the history. Not a raw count, but the
   novelty of an edge relative to the node's own history.

### Other facts from the slice (for the generator)

- Share of Fail in the clean slice: U-accounts 1.54%, overall 0.68% - normal
  traffic is almost entirely successful.
- Many machine accounts (`C123$`), `ANONYMOUS LOGON`, `SYSTEM@`; types NTLM/
  Kerberos/Negotiate/`?`; orientation LogOn/LogOff/TGS/TGT/AuthMap.
- The authtype field is "dirty": truncated values
  (`MICROSOFT_AUTHENTICATION_PACKAGE` in seven different lengths). The ECG
  lesson "dirt is part of the living thing" applies here too: the generator
  has to be able to reproduce it, not scrub it away.

### Decision on the open question of scope (option 3 was: decide after Phase 0)

The LANL exam honestly supports exactly **two** labels: ordinary behaviour
versus red-team-style behaviour (someone else's account out of place). The
"guessing one/many accounts" classes are NOT represented in the LANL ground
truth - they would have to stay synthetic, with no real exam behind them.
Therefore:

- **The v1 problem statement is binary**, scoring edge novelty within a window:
  "does this (source, account) / (account, destination) pair behave like its
  own history, or like a stranger".
- The password-guessing classes go into an optional synthetic demo (sliders for
  the reader), NOT into the main exam - anything else would be dishonest.

### What is left for the next step

- The main exam (Phase 4) needs an auth slice covering the red-team window
  (150k...2.56M s) - far beyond the 1.5 million lines taken so far. Pulling the
  whole file (7.2 GB gz / ~70 GB unpacked) is unnecessary: the right move is a
  single streaming pass that filters down to a compact form (only the
  fields/nodes that are needed). To be designed in Phase 1.
- Phase 1: the window measurer (edge-novelty features + source role) - "the
  judge before the network".

---

## 2026-08-30 - Phase 1: the judge is written, separability is measured, the "hindsight" risk is exposed

**What was done.** Took the target slice of the log (days 0..9, one streaming
pass through the mirror, LogOn events only, compact form: time, account,
source, destination, outcome) - **72 139 560** lines, 372 MB compressed. Wrote
the window measurer `judge/measure.mjs` (9 explainable features) and the run
script `exam/day8.mjs` with incremental aggregation: 72 million events do not
fit in memory, so the features accumulate on the fly.

**Labels by day.** Red-team activity is concentrated: day 8 has 273 events,
day 12 has 209 (64% of the entire ground truth in two days). **Day 8** is
chosen as the exam window, days 0..7 as the history.

**Measurement.** Read 64 418 655 events and built **231 787** source windows
(a window is one hour), **15** of which are labelled by the ground truth.

### Normal and red team: the numbers

Share of new edges (newEdgeRatio) in normal traffic: median **0.0000**, 90th
percentile **0.0000**. People stick to well-trodden routes - the background is
almost perfectly clean.

All 15 labelled windows: `newUserRatio` = 1.0 in fourteen of the fifteen (every
account on the source is being seen for the first time), `newDstRatio`
0.90...1.00, failure share 0.17...0.61 against a normal background of 0.68%.

### What separates the nodes - and what misleads

The combined rule `newUserRatio>=0.9 & users>=5 & dsts>=10 & failRatio>=0.15`
gives **13 of 15** with **zero** false alarms on 231 772 normal windows.

The error analysis turned out to matter more than the number itself:

- **Seven normal windows that look like the red team on three features are
  new hosts** (C21949...C22183, `historySize=0`, `knownUsers=0`). On a machine
  that has just appeared in the network, EVERYTHING is new by definition. What
  sets them apart from the foothold: their failure share is ~0 (everything
  works), the rhythm is ragged (3.0...6.8), and the history is empty. Windows
  with an empty history in total: 1245.
- **The foothold C17693 HAS a history** (`historySize=336`, `knownUsers=15`):
  it is an ordinary workstation on which every account suddenly became
  foreign. The rule "has a history, but all accounts are new" catches **15 of
  15** (at the cost of 248 false alarms); adding volume thresholds brings the
  false alarms down to 7 at 13 of 15.
- **The two missed windows are quiet reconnaissance**: 3 and 6 events. That
  little volume gives no statistics; only the rule without volume thresholds
  picks them up.

### The main risk exposed by this measurement

The thresholds above were picked **while looking at the answers**. That is not
a detector, that is hindsight: on a labelled day it is easy to fit a rule, and
zero false alarms here proves nothing. So what has to be checked is not the
rule but the **transfer**: a network trained ONLY on synthetic data, one that
has never seen LANL, has to produce a comparable result on the same 231 787
windows. That is exactly where the value of the article lies - and exactly why
the thresholds picked now must NOT be carried over into the generator
(otherwise the truth about the exam leaks into the training world - the same
mechanism tdc-ecg called the poisoned reference book).

**Decision on the unit of measurement (the question had been left to my
judgement):** the source window. The measurement confirmed that window features
separate the classes, and the ground truth's event-level labels map onto
windows without loss.

### What is left

- Phase 2: TDC configs - a world of workstations, servers, NEW hosts (they are
  mandatory: without them the network will never learn to stay silent on
  legitimate novelty) and a node with foreign accounts. No LANL thresholds go
  into the generator.

---

## 2026-08-30 - Phase 2/3/4: the generator builds the world, the network is trained, THE MAIN EXAM IS PASSED

### Phase 2 - the generator (`gen/world.tdc`)

The project's first config. The world has two pools of machines, because load
in a network is spread extremely unevenly - a handful of servers legitimately
see hundreds of accounts, while workstations are many and each one is quiet.
Roles of the working machines: a workstation with its own 1..4 accounts, a
NEW host (no history, everything on it is legitimately new) and a workstation
whose accounts become foreign in the second period. The two periods are
history and observation.

Engine mechanisms used: two `<pool>`s (machines as entities that persist across
rows), `<gen type="formula">` with `hash(N, salt)` for deterministic draws,
exact role proportions via `percent`, `if=` on text generators.
400 000 events in 9 seconds.

Pitfalls along the way: `number` only takes integer ranges (shares had to be
kept in thousandths); `formula` does not accept `if=` - you need ternaries;
TDC is not XML, so `&lt;`/`&amp;&amp;` in expressions have to be written as
the literal characters (the engine said as much with a clear TDC294 error).

### Checking the world against reality BEFORE training

The first version of the world failed the check at the most important point:
in normal traffic, the 90th percentile of the share of new accounts came out
at **1.000** against **0.000** in the real network. The reason: new hosts made
up 16% instead of the real ~0.5%, and the stream was spread too thin. A world
like that must never be shown to the network: it would learn that novelty is
normal, and the main signal would be destroyed.

After the rebuild (two pools, new hosts at 2%, a third of the stream going to
servers):

| feature | LANL reality | TDC synthetic |
| --- | --- | --- |
| normal: share of new accounts, median / 90% | 0.000 / 0.000 | 0.000 / 0.000 |
| normal: events per window, median | 22 | 23 |
| normal: accounts per window, median / 90% | 2 / 4 | 2 / 4 |
| labelled: share of new accounts, median | 1.000 | 1.000 |
| labelled: failure share, median | 0.342 | 0.375 |
| labelled: accounts per window, median | 8 | 14 (range 2..49) |

The account count in labelled windows was not fitted: instead of matching the
number, the axis is spread wide (each machine has its own circle of foreign
accounts, 2..60 of them), so the real 8 falls inside the covered range.
Matching the number would have been copying the answer; covering the axis is a
legitimate spread (domain randomization).

**What was calibrated against reality and has to be spelled out in the
article:** the COARSE composition of the world - the share of servers, the
rarity of new hosts, the density of the stream. The features of the phenomenon
itself and the decision rule were not calibrated against anything.

### Phase 3 - the network (`net/train.mjs`)

A fully connected network, 12->24->12->1, **625 weights**, hand-written in
plain JS with no external libraries (the same weights will go straight into
the article's page). Counts are encoded as logarithms: the absolute volumes of
the synthetic world and of the real network differ by orders of magnitude, but
the logarithm transfers; shares go in as they are.

Training: 60 epochs, a matter of seconds. The internal exam on synthetic data
with a DIFFERENT seed (`world-exam-1`): precision 1.0000, recall 1.0000, false
alarms 0 of 3058.

The honest caveat, written down BEFORE the main exam (as in tdc-ecg): 100% on
synthetic data means "the network has learned our generator thoroughly", and
nothing more.

### Phase 4 - THE MAIN EXAM: real LANL

231 787 windows of the real network, 15 of them labelled. No real data was used
in training in any form.

| threshold | caught | false alarms | precision |
| --- | --- | --- | --- |
| 0.5 | 15/15 | 498 | 0.029 |
| 0.9 | 15/15 | 331 | 0.043 |
| 0.99 | **15/15** | **27** | 0.357 |
| 0.999 | 14/15 | 10 | 0.583 |

**AUC = 0.99999.** Ranks of the labelled windows in the overall list sorted by
confidence: 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 25 - **all fifteen
in the top twenty-five of 231 787**.

Unlike tdc-ecg (100% on synthetic data -> 25% on live patients), the transfer
worked the first time. The likely reason is the project's own thesis: the
authentication log is produced by a machine, the phenomenon has a computable
definition, and the "axes of nature" missing from our model are nearly
nonexistent here.

### Error analysis

- **First place in the list went to the foothold C17693 itself, in an hour the
  ground truth did NOT label.** The LANL red-team labels are not an exhaustive
  per-window truth; this is a limitation of the ground truth and it has to be
  stated in the article. Formally a false alarm, in substance the same
  machine.
- **Not a single false alarm landed on a new host** (`historySize=0` - zero
  cases out of 27). The "new host" class in the synthetic world worked exactly
  as intended: the network learned to stay silent on legitimate novelty. This
  vindicated the decision made after the Phase 1 measurement.
- The remaining false alarms are windows of one or two events with a
  one-hundred-percent failure rate, plus the machine C21868, where every single
  login fails. Genuinely odd windows, not noise.

### Limits of the result (to be stated in the article outright)

- Only 15 labelled windows - the AUC is computed over fifteen positives.
- So far the exam covers day 8 only. Day 12 (209 ground-truth events) has not
  been checked: it needs another streaming pass over days 0..12.
- The composition of the world is calibrated against the coarse statistics of
  the real network (see above).

### What is left

- Check the transfer on day 12 - an independent confirmation.
- Phase 5: the browser demo, plots, the fact package.

---

## 2026-08-30 - the methods digest is started

The project's techniques are moved out into a separate file, `METHODS.md`:
twelve items, each with its gist, why it is used and where it came from. The
diary stays a chronicle by date; the digest is a reference of techniques for
the article. Among the items: "exam first, generator second", "one measurer
for both sides", "the judge before the network", "cover the axis, do not match
the number", "calibrate the composition of the world, but not the features of
the phenomenon", "the caveat is written down BEFORE the exam".

---

## 2026-08-30 - checking the pipeline and comparing against the reference methods

### There really is only one measurer

Day 8 was originally computed by its own code (`exam/day8.mjs`), the synthetic
data by the shared module (`judge/windows.mjs`). If the two diverged, the whole
comparison of synthetic data against reality would be invalid, so day 8 was
recomputed with the shared module and compared line by line.

Result: **231 787 lines matched exactly by value** (largest discrepancy 0).
Only the formatting of zeros differs (`0` versus `0.0000`) - an artefact of
the output format. Method no. 2 from METHODS.md is confirmed by measurement,
not by promise.

### Comparison against the reference methods (day 8, the same windows)

The price of recall - how many false alarms you have to put up with to catch
this many of the fifteen labelled windows:

| method | 12/15 | 14/15 | 15/15 | AUC |
| --- | --- | --- | --- | --- |
| counter: number of accounts from the source | 1 940 | 83 084 | 175 904 | 0.94130 |
| counter: number of destinations from the source | 1 361 | 161 437 | 206 651 | 0.90266 |
| rule fitted TO THE ANSWERS (Phase 1) | 0 | unreachable | unreachable | 0.93333 |
| **network trained only on synthetic data** | **2** | **2** | **10** | **0.99999** |

Read it like this: to catch all fifteen windows, a threshold counter would have
to raise the alarm 175 904 times; the network, ten. And the counter works
directly on the real data, while the network has never seen it.

A separate, honest word about the Phase 1 rule: at 12 of 15 it is flawless
(zero false alarms), but it NEVER gets any higher - the two quiet windows (3
and 6 events) fail its volume thresholds. Fitting to the answers gives a
pretty number and then hits a ceiling; the network, which has never seen the
answers, goes further. A direct illustration of method no. 7.

---

## 2026-08-30 - DAY 12: THE TRANSFER SAGGED, AND THE CAUSE TURNED OUT TO BE WORTH MORE THAN A SECOND SUCCESS

### Measurement

Second streaming pass: days 0..12, **92 646 816** events, 223 987 windows,
12 of them labelled by the ground truth. The network was NOT retrained - the
same 625 weights, the same measurer, not one threshold touched.

| threshold | caught | false alarms |
| --- | --- | --- |
| 0.5 | 8/12 | 392 |
| 0.9 | 7/12 | 231 |
| 0.99 | 5/12 | 30 |

**AUC = 0.92006** against 0.99999 on day 8. Ranks of the labelled windows:
2, 15, 17, 18, 30, 226, 234, 255, 450, 823, 5614 and **207 258** of 223 987.

### Diagnosis - by measurement, not by guesswork

Features of the labelled windows on the two days, compared:

| feature | day 8 | day 12 |
| --- | --- | --- |
| share of new accounts (median) | 1.0000 | 0.5714 |
| share of new edges (median) | 0.7692 | 0.5455 |
| size of the source's history | 336 | 863 |
| **accounts known to the source** | **15** | **84** |

A direct check of the mechanism: by the start of day 12 the machine C17693
"knows" 84 accounts, and **49 of them are precisely the accounts that were
used through it earlier** (that is ALL 49 ground-truth accounts used before
day 12). **58.3% of the machine's "normal history" is the observed activity
itself.**

### The lesson, in one line

**THE BASELINE POISONS ITSELF.** The feature is built as "novelty relative to
the node's own history", and the history accumulates as events happen.
Anything that goes on long enough BECOMES the norm for that node - and stops
being new. The longer the activity lasts, the more normal it looks.

This is not a defect of the network, nor of the generator: the network worked
on exactly the signal it was given, and that signal weakened by half. The
defect is in how the baseline is constructed.

The kinship with the tdc-ecg lesson "the poisoned reference book" is direct,
but the mechanism is mirrored: there, false data leaked into the reference of
shapes; here, the thing being observed leaks into its own norm.

### Worst case: where the network is blind in principle

The window at rank 207 258 is C19932, 37 events, share of new accounts **0**,
share of new edges **0**, failure share **0**. The account on this machine is
not new, the route is not new, everything succeeds. In the "edge novelty"
feature set such a window is IN PRINCIPLE indistinguishable from ordinary work
- not because the model is weak, but because the features carry no
discriminating information. A measured limit of applicability.

### What this gives the article

A second successful confirmation would have been weaker than this finding.
What we have instead: a failed transfer, an exposed mechanism, a number that
proves the mechanism (58.3%), and a remedy that follows from the mechanism -
freeze the baseline on an early period. Checking the remedy is the next step.

---

## 2026-08-30 - FROZEN BASELINE: the signal restored, two limits measured

### Experiment

The baseline is frozen on days 0..7, the exam is day 12, and days 8..11 go
neither into the history nor into the windows (an `examStart` parameter was
added to the module). This is the operator's strategy of "snapshot the
baseline during a quiet period"; knowledge of which days are poisoned was not
used. The network was not retrained.

### Result

| | drifting baseline | frozen |
| --- | --- | --- |
| caught at threshold 0.99 | 5/12 | **10/12** |
| false alarms at 0.99 | 30 | 83 |
| accounts known to C17693 | 84 | **15** |
| share of new accounts (median) | 0.57 | **~0.95** |
| AUC | 0.92006 | 0.92373 |

Ranks of the labelled C17693 windows: were 2, 15, 17, 18, 30, 226, 234, 255,
450, 823 - now **1, 3, 4, 5, 8, 9, 20, 25, 26, 27**. All ten moved up into the
top twenty-seven of 223 987.

**The price of the remedy, stated:** 83 false alarms against 30. A short
baseline knows less, so more legitimate novelty falls under suspicion. The
trade-off is measured, not swept under the rug.

### Two unbeaten limits

**C22409 (rank 3896).** Novelty 1.00, everything as it should be - but
`knownUsers = 0`: the machine is NEW. The network stays silent precisely
because we taught it to. The "new host" class, which gave zero false alarms on
day 8, works against us here. **Immunity to legitimate novelty cuts both
ways:** a machine that is new and compromised at the same time is
indistinguishable by construction.

**C19932 (rank 201 049).** Account novelty 0, route novelty 0, failures 0.
There is no discriminating information in the features at all. A limit of the
problem statement, not of the model: to see something like this you need a
different feature (for example, how unusual the route itself is for this
ACCOUNT rather than for the machine).

### Methodological note

The AUC barely moved (0.920 -> 0.924), even though recall doubled. With twelve
positives, the AUC is dominated by the two invisible windows and hides
everything else. **A table of ranks is more honest than a single summary
number** - the table goes into the article, the AUC is given with a caveat.

### State of the programme

The article's storyline is now complete and rests on measurements:
1. Day 8 - transfer without a single adjustment: 15/15, all in the top 25 of
   231 787.
2. A counter on the same data: 175 904 false alarms against 10 for the network.
3. Day 12 - the transfer sagged by half; the mechanism exposed and proved
   (58.3% of the machine's history is the observed activity itself).
4. Freezing the baseline - the signal restored (10/12, ranks 1..27), the price
   stated.
5. Two measured limits of applicability: a new-and-compromised machine, and a
   window with zero novelty.

---

## 2026-08-30 - autopsy of two failures and the SEALED SET (protocol fixed BEFORE any improvements)

### Why two windows turned out to be invisible

Direct inspection of the ground truth: in the C19932 window **1 event of 37**
is labelled, in the C22409 window **2 of 65**. The targets are C586, C457,
C467 - domain controllers, the busiest machines in the network. A single
foreign event dissolves among fifty ordinary ones, and all the window features
are shares, i.e. averages. The average drowns out the single event.

This is exactly the trouble tdc-ecg had with the missed beat: a head with pure
averaging lost one event per ten seconds. The cure there was the avg+max head
("the average is about the overall rhythm, the maximum is about the loudest
local event"), and it gave +20 points. The same trick is needed here, in a
different form.

### Is there a signal in the events themselves (checked against the frozen baseline)

| event | account has been on the machine | account has gone there | machine has gone there | machines the account knew |
| --- | --- | --- | --- | --- |
| U737 @ C19932 -> C586 | YES | YES | YES | 18 |
| U3486 @ C22409 -> C457 | **NO** | YES | **NO** | **1** |
| U3486 @ C22409 -> C467 | **NO** | YES | **NO** | **1** |

**C22409 is recoverable:** an account that historically knew ONE machine turns
up on another and leads it to new places. A strong signature, lost only to
averaging.

**C19932 is not recoverable with novelty features:** there is no novelty on
any of the three axes. The account used is legitimately native to this
machine. This is a limit of the problem statement itself, not of the model.

### The sealed set - declared BEFORE improvements

The inspection of days 8 and 12 was used to understand the PHENOMENON (what
movement on foreign accounts looks like), not to pick thresholds. But
inspecting failures and then improving on them is still development steered
by the exam.

Therefore **days 13, 14, 15 are declared sealed** (142 ground-truth events: 81,
35 and 26). They are NOT inspected and NOT used for building features, tuning
the generator, or choosing thresholds. Their only use is the final check of
the improved version, run once, with the result published whatever it turns
out to be.

Days 8 and 12 are from now on considered "working": looking at them and
diagnosing on them is allowed. Days 13..15 are the honest measure of the
transfer.

**ADDED the same day, on reflection.** Three consecutive days is too narrow a
surprise: the check should draw on different periods of the network's life.

The option of splitting the events within each day in half was considered and
REJECTED. The reason: the unit of measurement is the "machine x hour" window,
and the halves of ONE window would land on both sides (tuning on one half of
the hour, checking on the other half of the same hour on the same machine).
Besides, a split history would make the novelty features wrong for both sides
at once.

Decided differently, in whole windows: **EVERYTHING except the two working
days is held out.**

| set | days | ground-truth events |
| --- | --- | --- |
| working | 8, 12 | 482 |
| held-out | 1,2,5,6,7,9,13,14,15,20,21,22,26,27,28,29 | **267** |

Sixteen days spread across the whole observation period - the beginning, the
middle and the tail. No knob was turned on any of them. The slice is
downloaded in advance (`exam/slice-sealed.sh`, up to the end of day 29) but is
not measured until the final check.

### Improvement plan (motivated by the phenomenon, not by thresholds)

1. **Generator - MIXED WINDOWS.** Right now, on a machine with foreign
   accounts, ALL events of the observation period are foreign (share 100%). In
   reality it is 1 of 37 and 2 of 65. The network has never seen a diluted
   case - so it does not recognise one. A "share of foreign events" knob is
   introduced, spread from 2% to 100%.
2. **Measurer - event-level features plus a maximum over the window.** Added
   to the shares: the share of events where the account is on this machine for
   the first time; the NUMBER of events whose three edges are all new at once
   (an absolute count, not a share - otherwise a single event drowns again);
   the "narrowest" account in the window (how many machines it knew).

---


## 2026-08-30 - IMPROVEMENT CAMPAIGN: six changes to the world, one of them reverted

The task for the day is to raise the quality of the data and of the approach.
Below are all the experiments in order, including the reverted ones: here the
negative results are worth more than the positive ones.

### Experiment 1 - diluted windows (REVERTED)

**Idea.** A real window may contain 1 intruder event in 37, while in the
synthetic data every event of the period was the intruder's. Introduced a
"share of intruder events" knob, 2%..100%.

**Result.** Day 8: **1428** false alarms instead of 27, worst rank 1275 instead
of 25. An ablation showed the new features are not to blame: even on the
previous twelve features, the new world gave 2169 false alarms. A direct check
with the knob switched off - 7 false alarms. Dilution is the cause.

**The mechanism, worked out arithmetically.** Dilution teaches the network that
ANY event with triple novelty means an intruder. In the real network, 1330
normal windows contain such events - hence the ~1428 false alarms. The knob is
reverted.

**Lesson.** Training on diluted examples buys sensitivity at the cost of a
collapse in precision, and the price turned out to be out of all proportion.

### Experiment 2 - service and machine accounts

The world consisted only of accounts "tied to a workplace": an account's scope
never exceeded 3 machines, against the real 9812. Service accounts were added.
The first attempt (a random pick from a common pool) raised the novelty of the
normal class to 0.11 against the real 0.00 - a wrong model. Fixed: a service
account is **tied to a machine** (the same machine always has the same
accounts), but each one serves several machines. The novelty of the normal
class went back to 0.00.

### Experiment 3 - rarity of new hosts

Windows without history made up 2.8% against the real 0.54%, and ALL the normal
windows with a high triple-novelty count came from precisely those. The share
was brought down to 0.6%.

### Experiment 4 - organic churn (legitimate novelty in the normal class)

**Idea.** The synthetic normal class NEVER had any novelty, so the network
concluded that any new event means an intruder. A live network changes: a new
employee, a new server, a machine moved somewhere else.

A churn knob was added. The first value gave 17.77% of windows with novelty
against the real 0.57% - an overshoot by an order of magnitude; after two
refinements, ~2%. False alarms: 1428 -> 201 -> and further down.

### Experiment 5 - two kinds of legitimate novelty

An intrusion event and churn looked identical: an account on a machine for the
first time. They were split into a **new employee** (the account did not exist
in the network at all) and **a relocation of an existing person** to another
machine.

### Experiment 6 - THE MAIN FIX: the stolen account must exist

Cross-checking the new features against reality exposed an error that had been
in the world from the very start:

| feature of labelled windows | reality | synthetic before the fix |
| --- | --- | --- |
| account known to the network, but first time on the machine | **26** | 2 |
| account did not exist in the network at all | **0** | 11 |

In reality the intrusion goes through EXISTING accounts - they work in the
network, just not on this machine. In the synthetic data the "stolen" account
was rolled as a number from a range, and most of the time no such account
existed anywhere. Those are not stolen credentials, they are credentials made
up out of thin air.

**Fix.** Accounts became addressable: machine `hid` owns accounts
`hid*30 .. hid*30+span`. A stolen account is now an account that BELONGS to
another machine in the world and lives there. After the fix: moved 2 -> 13
(reality 26), fresh 11 -> 1 (reality 0).

### New measurer features (12 -> 18)

`userSrcNewRatio`, `tripleNewCount` (an absolute count - a ratio drowns a
single event), `tripleNewRatio`, `minUserScope`, `movedUserCount` (account known
to the network but on this machine for the first time - the signature of stolen
credentials), `freshUserCount` (account did not exist anywhere - the signature
of a new employee).

### Campaign result

| | version 1 | version 6 |
| --- | --- | --- |
| **day 8**: caught at 0.99 | 15/15 | 15/15 |
| **day 8**: false alarms | 27 | **6** |
| **day 8**: worst rank | 25 | **21** |
| **day 8**: precision at 0.99 | 0.357 | **0.714** |
| **day 12**: caught at 0.5 | 10/12 | 10/12 |
| **day 12**: ranks of the ten windows | 1..27 | 1..29 |

False alarms on day 8 fell fourfold (27 -> 6) at the same recall; precision doubled (0.357 -> 0.714). Day 12 did not change.

**What remains unbeaten (and probably unbeatable in this formulation):**
C22409 (rank 3775) - a machine that is new and running under stolen accounts at
the same time; C19932 (rank 210 243) - zero novelty on every axis.

### Methodological note

During the campaign I broke my own rule, "the judge before the network": the
network was retrained without cross-checking the new features against reality,
and the result got twice as bad. Once I went back to the rule, every subsequent
change was verified by the cross-check BEFORE training, and it was the
cross-check that exposed the main error in the model (experiment 6). The rule
earned its keep.

Separately, an engineering defect came to light: the exam passed 12 fields out
of 16 into the encoding, the missing ones arrived empty, and the network output
a constant (AUC exactly 0.50000). A common loader, `judge/rows.mjs`, was
introduced; it checks that ALL features are present and fails with a clear
error. Field names are no longer retyped by hand anywhere.

---

## 2026-08-30 - experiment 7: a machine that is new and running under stolen accounts at the same time

**Idea.** The network missed window C22409 (rank 3775) by construction: it was
taught to stay silent on the legitimate novelty of new hosts, and this machine
was new AND running under stolen accounts. That combination did not exist in
the synthetic world at all - new hosts there are always honest. Yet a
distinguishing feature does exist: an honest new host has FRESH accounts (never
seen in the network before), a new compromised one has MOVED accounts, i.e.
ones the network has long known.

**What was done.** Role 4 was introduced: a machine with no history, running
under stolen accounts. Its share was chosen by a sweep (2% -> 1% -> 0.6%).

**Share sweep (both working days):**

| role 4 share | day 8: false alarms at 0.99 | day 12: caught / false alarms at 0.99 | C22409 |
| --- | --- | --- | --- |
| none (version 6) | 6 | 9/12 * 16 | 3775 |
| 2% | 139 | 10/12 * 185 | 571 |
| 1% | - | 9/12 * 14 | - |
| **0.6%** | **11** | **10/12 * 8** | **594** |

Checking the assumption did not confirm it: at a 2% share, only 7 of the 139
false alarms were new hosts, and 132 were machines with history. So a large
share of role 4 shifts the decision boundary in general rather than breaking
the immunity to novelty. At 0.6% the shift disappears and the benefit remains.

**Result (version 7 against version 6):**

| | version 6 | version 7 |
| --- | --- | --- |
| day 8: ranks of labelled windows | 2..21 | 1..32 |
| day 8: false alarms at 0.99 | 6 | 11 |
| day 12: caught at 0.99 | 9/12 | **10/12** |
| day 12: false alarms at 0.99 | 16 | **8** |
| day 12: C22409 | 3775 | **594** |
| day 12: C19932 | 210 243 | **83 808** |

Ten of the twelve windows on day 12 landed in the top fifteen out of 223 987.
Day 8 sagged slightly, day 12 improved noticeably - the trade is accepted,
because day 12 was the weak side.

C19932 rose from 210 243 to 83 808 - which is to say, it stayed invisible. That
is expected: it has zero novelty on every axis, and no novelty feature will
ever reach it. The boundary of the formulation is confirmed once more.

**Weights saved as `net/model-v7.json` - a candidate for the final version.**

---

## 2026-08-30 - experiment 8: temporal wrapper REJECTED (negative result)

**Idea.** The windows of a single machine were judged separately, as if the
neighbouring hours did not exist. On day 8 the foothold lit up for ten hours
in a row - it seemed that accumulating suspicion over time ought to help both
the diluted cases and precision.

The rules were written CAUSAL (looking only into the past) and sit on top of
the trained network, with no retraining.

| rule | day 8: worst rank | AUC | day 12: worst rank | AUC |
| --- | --- | --- | --- | --- |
| network as is | 32 | 0.99999 | 83 808 | 0.96860 |
| accumulation with decay | 32 | 0.99999 | 95 638 | 0.96407 |
| deviation from its own past | 228 954 | **0.50403** | 194 520 | 0.58342 |
| suspicion x deviation | 46 | 0.99991 | 83 809 | 0.96840 |

**Not one rule helped. All three range from neutral to destructive.**

**Why "deviation from its own past" failed (AUC 0.504).** An intrusion goes on
for HOURS IN A ROW, and from the second hour on, its own values enter the
baseline the deviation is computed against. **The same self-poisoning
mechanism that was measured at the scale of days repeated at the scale of
hours.** The trick that cured the daily baseline (freezing) does not apply at
the hourly scale: there is nothing to freeze, the day has only just begun.

**Why accumulation did not help.** The persistent false alarms are domain
controllers, suspicious in all 24 windows of the day. Accumulation cements them
rather than damping them. The flaw in this expectation was predicted before
the experiment and confirmed by measurement.

**Conclusion.** The per-day signal is already strong enough (ranks 1..32 out of
231 787), and there is no headroom left in it for a temporal add-on. Blind
improvements on the working days are exhausted. Version 7 is declared final;
the held-out set is opened.

---

## 2026-08-30 - FINAL CHECK ON THE HELD-OUT SET (one run, version 7)

Weights, measurer, encoding and the baseline rule were frozen before the run.
The baseline rule ("freeze on the first week, never update afterwards") was
chosen from the day 12 experience, BEFORE a single result from the held-out
days had been seen.

**Volume:** sixteen days, **3 600 398 windows**, 64 labelled windows
(267 ground-truth events).

### Overall result

| threshold | caught | false alarms | precision |
| --- | --- | --- | --- |
| 0.5 | 29/64 | 2388 | 0.012 |
| 0.9 | 28/64 | 1451 | 0.019 |
| 0.99 | 23/64 | 476 | 0.046 |

**AUC = 0.84980** against 0.99999 on working day 8. Best ranks: 6, 13, 15, 35,
39, 40, 45, 53, 61, 67, 72, 92 - that is, a dozen windows landed in the top
hundred out of 3.6 million. Worst rank: 3 432 865.

The result is NOTICEABLY WEAKER than on the working days, and this was
predicted before the run.

### Breakdown by day (the average is not the point)

| day | labelled | in the top hundred | worst rank |
| --- | --- | --- | --- |
| 1 | 3 | 0/3 | 1 547 |
| 2 | 4 | 0/4 | 5 591 |
| 5 | 8 | 0/8 | 20 690 |
| 6 | 3 | 1/3 | 146 423 |
| 7 | 1 | 0/1 | 182 415 |
| 9 | 1 | 0/1 | 3 769 |
| **13** | 12 | **8/12** | 221 464 |
| 14 | 6 | 3/6 | 36 809 |
| 15 | 7 | 4/7 | 214 466 |
| 20 | 1 | 0/1 | 214 228 |
| **21** | 2 | **2/2** | **87** |
| 22 | 1 | 0/1 | 224 131 |
| **26** | 4 | **4/4** | **20** |
| 27 | 5 | 3/5 | 217 718 |
| 28 | 2 | 1/2 | 222 083 |
| 29 | 4 | 1/4 | 215 804 |

The spread is enormous: from 4 out of 4 in the top twenty (day 26) to zero out
of eight (day 5). An average over a spread like that is meaningless - whether
it works or not depends on the REGIME, not on luck.

### Two measured boundaries of the regime

**The lower boundary - the baseline needs time to accumulate.** The early days
(1, 2, 5, 6, 7) are a complete failure: 1 out of 19 labelled windows in the
top hundred.

| day | median machine history (events) |
| --- | --- |
| 1 | 464 |
| 2 | 963 |
| 5 | 2 192 |
| 7 | 3 057 |
| 9 and later | ~3 500 |

While there is little history, EVERYTHING looks new, and the novelty feature
carries no information. The method requires an accumulated baseline, and that
is not a setting but a condition of applicability.

**The upper boundary - a frozen baseline drifts, and the rate is measured.**
The share of windows whose machine is entirely unknown to the first-week
baseline:

| day | share of unknown machines |
| --- | --- |
| 9 | 1.1% |
| 13 | 2.6% |
| 15 | 3.3% |
| 20 | 3.8% |
| 26 | 5.1% |
| 29 | 6.1% |

The network drifts away from the snapshot at roughly **0.25% per day**, and the
machines that drifted away become false alarms: of the 476 false alarms at
threshold 0.99, **186 (39%)** are machines unknown to the baseline. On working
day 8 there were ZERO of those.

### The main conclusion of the work

A trade-off emerges, and both sides of it are measured on live data:

- **refresh the baseline often** - and it gets poisoned by what it observes
  (58% of a compromised machine's history was the intrusion itself);
- **freeze the baseline** - and it drifts at 0.25% of machines per day; after
  three weeks every sixteenth machine looks new.

The working point lies in between: a baseline no younger than a week and no
older than two or three. That is the method's regime of applicability,
measured rather than postulated.

### An honest summary for the article

- Training - synthetic data only, from `world.tdc`; real data played no part
  in training (verified in code).
- On dense activity with a fresh baseline the transfer is excellent: day 8 -
  15/15, ranks 1..32 out of 231 787; a counter needs 175 904 false alarms to
  do the same.
- On the held-out set of sixteen days - 29/64, AUC 0.850, and a spread from
  flawless to complete failure depending on the baseline regime.
- The boundaries of the regime are measured quantitatively (see above).

Published as is.

---

## 2026-08-30 - comparison on the held-out set: an engineering defect that struck twice

When comparing against the reference methods on the held-out set, the network
gave an AUC of exactly 0.50000 - the sign of a constant output, already familiar
from the earlier failure. The breakdown:

1. First attempt: the report scored the network by the field `d.net`, which
   does not exist in the new row structure - the comparison ran on
   `undefined`.
2. Second attempt (replacing the field with `d.p`) did not help, because the
   root cause was deeper: **the common loader `judge/rows.mjs` had never been
   brought into this file**. The file was still reading the table with its own
   code and passing 12 fields out of 18 into the encoding. The missing ones
   arrived empty, and the logarithm gave NaN.

This is THE SAME defect the common loader was introduced to fix - it just had
not been applied everywhere. Lesson: a single loader is mandatory in ALL
consumers, otherwise it only protects the files it was brought into. The check
"is the old loader still there?" was added to the run as an explicit line.

The counter numbers in that run were correct (their computation does not depend
on the encoding); the network number was garbage. The final comparison was
recomputed after the fix.

---

## 2026-08-30 - port to Python and a sweep over network capacity

**Why.** A remark: a JavaScript implementation shuts out the ML reader, and no
experiments on the network architecture had been run at all - the capacity of
769 weights was picked arbitrarily and never checked.

**What was done.** The implementation was rewritten in Python + PyTorch
(`net_py/`): `data.py` (reading and encoding; the only dependency is numpy - the
pandas in this environment is incompatible with numpy 2.x), `model.py` (an MLP
with a configurable list of widths), `evaluate.py` (rank-based AUC and the cost
curve in a single pass), `run.py`, `sweep.py`, `final.py`.

Python reproduces the JS result: day 8 - AUC 0.99995 against 0.99999 (the
difference comes down to the optimiser: Adam versus plain gradient descent).

### Sweep (3 seeds per architecture; selection ONLY on the working days)

| architecture | weights | day 8, AUC | day 12, AUC |
| --- | --- | --- | --- |
| flat [8] | 161 | 0.99998+-0.00001 | 0.94151+-0.00945 |
| flat [32] | 641 | 0.99997 | 0.95461+-0.01376 |
| flat [100] | 2001 | 0.99997 | 0.95939+-0.00743 |
| two-layer [24,12] (base) | 769 | 0.99997 | 0.94112+-0.00436 |
| two-layer [48,24] | 2113 | 0.99997 | 0.94646+-0.01082 |
| deep [16,16,16] | 865 | 0.99991 | 0.96520+-0.00442 |
| **deep [12]x8** | **1333** | 0.99997 | **0.97518+-0.00343** |
| wide [100,50,25] | 8251 | 0.99997 | 0.96366+-0.01136 |

**Conclusion 1. Day 8 is fully saturated.** Every architecture gives
0.99996-0.99998 with a spread of +-0.00001. **161 weights** are enough (a single
layer of eight neurons), and with three false alarms it does better than the
base network. The task there is so separable that capacity does not matter.

**Conclusion 2. Depth beats width.** On the hard day 12, the gap between the
base (0.94112) and the deep x8 (0.97518) is about seven standard
deviations - not noise. Meanwhile the wide network, six times larger (8251
weights), loses to the narrow, deep one (1333 weights).

**Conclusion 3. The spread over seeds has been measured for the first time**,
and on day 12 it turned out to be substantial (+-0.003...0.017). Earlier
comparisons of single runs have to be read with that in mind.

### The held-out set with the chosen architecture

The second and last use of the held-out set. The architecture was chosen on the
working days; the held-out set played no part in it.

| | AUC | false alarms before 16/64 |
| --- | --- | --- |
| deep x8, three seeds | **0.86175 / 0.85625 / 0.86930** | 245 / 300 / 237 |
| previous network (JS, 721 weights) | 0.84980 | 176 |
| counter: accounts | 0.61757 | 161 100 |
| counter: destinations | 0.53484 | 99 855 |

The deep network is slightly higher on AUC (0.862+-0.005 against 0.850) and
slightly more expensive in the price of the first sixteen hits. Against the
counters the gap is the same as before - hundreds of times.

---

## 2026-08-30 - COUNCIL, JUDGE AND THE MAIN FINDING: synthetic data does not produce coincidences

### The big sweep: 93 networks in 170 seconds

31 architectures, three seeds each. Refinements to the earlier conclusions:

- **the capacity floor has been found**: "flat 4" (81 weights) falls short even
  on the easy day (0.99868), while "flat 8" (161 weights) already gives 0.99998.
  The threshold lies between 4 and 8 neurons;
- **depth consistently beats width**: `deep 12x8` (1333 weights) gives 0.97518
  on day 12, while `2-layer 128-64` (10 753 weights) gives 0.96318. Eight times
  the weights, a worse result;
- **too deep is bad as well**: `12x12` (1957 weights) drops to 0.94923 and hurts
  even the easy day. The sweet spot is 6-8 layers.

### The council works, the judge does not

| | day 12 |
| --- | --- |
| best single network | 0.98183 |
| **council of 3, RANK averaging** | **0.98053** |
| council of 5, rank averaging | 0.97703 |
| council of 8, rank averaging | 0.97361 |
| judge over the trio | 0.95552 |

Rank averaging beats probability averaging across the board (the networks are
calibrated differently). More members, worse results: a trio of strong ones
beats an eight diluted with weak ones.

The judge loses to plain averaging by 2.5 points in every line-up.

### Why the judge does not work - a measurement instead of a guess

The idea: give the judge a hard proving ground where the networks actually make
mistakes (undertrained ones included). Four proving grounds were tried: the easy
synthetic exam, a HARD one (baseline cut down fourfold - the early-days regime),
undertrained networks (6 epochs instead of 120), and the union of all of them.

**On ALL proving grounds the base networks give AUC 1.0000. The undertrained
ones, after six epochs, give 0.9999. The mean spread of opinions between members
is 0.0002.**

There is no disagreement anywhere. The judge simply has nothing to learn from.

### An attempt to bring ambiguity into the world

Role 5 was added: an administrator's machine that legitimately walks across many
machines under accounts belonging to other machines - that is, with THE SAME
signature as intruder activity, but labelled normal. The share of normal windows
with 3+ moved accounts rose from 1.77% to 3.49% (in reality it is 1.19%).

The result cuts both ways:
- **the single network improved**: day 12 went from 0.98183 to **0.98592** - the
  best result in the whole project so far. The network learned not to fire on
  legitimate rounds;
- **the synthetic data did NOT get any harder**: the members' AUC stayed at
  1.00000.

The networks found a tell. Measurement showed which one - the failure rate:

| | failures | new accounts | events |
| --- | --- | --- | --- |
| ambiguous normal, synthetic | 0.019 | 0.559 | 41 |
| ambiguous normal, REALITY | 0.014 | 0.576 | 129 |
| labelled, synthetic | 0.355 | 0.997 | 20 |
| labelled, REALITY | 0.340 | 0.994 | 35 |

And the tell is NOT made up: it is there in the real data too. The centres of
both classes are reproduced almost exactly.

### THE MAIN FINDING: there are no coincidences in the synthetic data

Normal windows carrying the FULL intruder signature (account novelty >=0.9 AND
failures >=0.15):

| | such windows |
| --- | --- |
| **reality** | **51 out of 231 772 (0.022%)** |
| base world | **0 out of 3045** |
| world with the administrator | **0 out of 3035** |

Zero. Not a single one, in any version of the world. With the extra condition on
moved accounts: 35 such windows in reality, still zero in the synthetic data.

**This is the entire sim-to-real gap, pinned down to specific windows.**

We reproduced the class centres, the marginal distributions and even the tell.
What we did not reproduce is the COINCIDENCES - the rare normal windows in which
all of the intruder's features happen to line up at once. And those are exactly
what decides quality at high precision: they are the false alarms that no amount
of training removes.

**This explains everything at once:** why any architecture from 161 weights to
10 753 solves the synthetic data to 1.0000; why the judge has nothing to learn
from; why the council gives fractions of a percent instead of the +16 points it
gave in tdc-ecg; why capacity means nothing on the easy day.

### Why this cannot be removed

A coincidence is, by definition, the ABSENCE of a mechanism. Anything added to
the generator is specified as a mechanism, and a mechanism leaves a trace that
the network finds. Verified on role 5: a class designed to be indistinguishable
turned out to be distinguishable by its failure rate.

To produce "a normal window that happens to look like an intrusion", you have to
produce an intrusion and call it normal - that is, lie in the labels.

**The lesson in one sentence: synthetic data reproduces regularities; it does
not reproduce coincidences. And recognition quality at high precision is decided
by coincidences.**

This is a limit not of our generator but of training on synthetic data as a
method.

---

## 2026-08-30 - THE RICH WORLD: the attack as a process, the normal class from many mechanisms

### Idea

The previous world was static: "intruder" was decided by a coin toss on every
event, and the normal class was made of three mechanisms. Hence two
problems - we produced the intrusion at full height straight away and never its
quiet beginning, and the world had no coincidences at all (normal windows
carrying the intruder's signature).

**Change 1 - the attack became a process.** A machine gets a start moment, then
four stages of three hours each: foothold (4% of events are the intruder's),
credential harvesting (18%, failures x1.6), spreading (50%), reaching the
servers (80%, a third of the targets are servers). The range of accounts in play
widens with each stage.

**Change 2 - the normal class built from many mechanisms:** a terminal server
(40-160 people, legitimately), a service with a broken password (30-80%
failures), one-off maintenance (a legitimate burst of outside accounts within
one hour), an administrator on his rounds.

### Two mistakes along the way, both caught by measurement

**Mutually exclusive roles.** The first version made the mechanisms ROLES: a
machine is either a terminal server or a machine with a broken service.
Coincidences came out at zero again. Measurement explained why: novelty >=0.9 in
1.04% of the normal class, failures >=0.15 in 4.5%, both together - 0.000%.
Under independence you would expect 0.047%. The zero was not rarity but a
PROHIBITION BY CONSTRUCTION. Roles were replaced with independent flags: one
machine can be a terminal server, have a broken service, and be under
maintenance, all at the same time.

A side note: in reality these features are not just independent but positively
correlated (0.644% x 0.669% would give 0.004%, whereas 0.022% is observed - five
times more).

**Sample size.** 3359 normal windows against 231 779 in reality. A phenomenon
with a frequency of 0.022% has an expected count of 0.7 windows in a sample that
size - it cannot show up even in theory. The world was scaled up twentyfold: 8
million events, 2000 machines, 25 365 windows.

### Result: the world became more honest

| | previous world | rich world |
| --- | --- | --- |
| own synthetic data | 0.99993+-0.00001 | **0.99781+-0.00004** |
| day 8 | 0.99997+-0.00002 | 0.99765+-0.00049 |
| **day 12** | 0.97518+-0.00343 | **0.98779+-0.00377** |

**For the first time the synthetic data is not solved to one** - there are now
cases the network cannot sort out. And day 12 rose by 1.26 points, which is 3.5
standard deviations: for the first time an improvement on the day is above the
seed noise.

### But on the held-out set - no, again

| rich world, held-out set | AUC | false alarms before 16/64 |
| --- | --- | --- |
| seed 7 | 0.90499 | 25 851 |
| seed 17 | 0.82661 | 96 667 |
| seed 27 | 0.84538 | 41 127 |
| mean | 0.859 +- 0.033 | tens of thousands |
| **simple network, base world** | **0.862 +- 0.005** | **237-300** |

The same on AUC, a hundred times worse on the practical price, and the spread
over seeds grew sevenfold.

### THE MAIN METHODOLOGICAL RESULT

This is the FOURTH case in a row of an improvement on the working day failing to
transfer:

| improvement | day 12 | held-out set |
| --- | --- | --- |
| administrator role | better | worse |
| council | better | worse |
| judge over weak ones | a lottery | a lottery |
| rich world | better by 3.5 sigma | not better |

And in the last case the improvement was above the seed noise - and still did
not transfer.

**Explanation.** We measured the spread OVER TRAINING SEEDS and thought that was
enough. But there is a second source of noise: EXACTLY WHICH twelve windows
happened to be labelled on day 12. Reseeding cannot catch that - only a
different day can.

**Twelve examples are not a measure, whatever the seed spread.** Day 12 is
fundamentally unfit as a selection criterion.

Four times in one evening the held-out set said "no" where the working day had
said "yes". That is exactly what it is there for.

### State at the end of the session

Best and final: **a simple deep network 18-[12]x8-1, 1333 weights, trained on
the base world. Held-out set: AUC 0.862 +- 0.005, 237-300 false alarms on the
way to 16 caught out of 64 across 3.6 million windows.**

Neither the council, nor the judge, nor the symbiosis, nor the rich world has
improved on it.

---

## 2026-08-31 - MODEL FAMILIES: boosting, recurrent networks, exotica

### What prompted this

A remark: we tried two or three architectures, while there are dozens, and some
of them come with temporal memory. Worth checking.

An important caveat, made before the experiments: swapping a recurrent network
in for the MLP on a fixed vector of 18 numbers **is impossible** - there is
nothing for it to unroll over time. For sequence architectures it is the
REPRESENTATION that has to change, not the layer.

### Experiment 1 - gradient boosting (a hole in our experiments)

For tabular data, boosted trees are the standard, and we had never tried them.
Installed `xgboost` 3.2.0, trained on the same synthetic data with the same 18
features.

| model | day 8 | day 12 |
| --- | --- | --- |
| boosting: shallow trees (depth 3) | 0.99954 | 0.95211 |
| boosting: medium (depth 6) | 0.99915 | 0.95145 |
| boosting: deep (depth 10) | 0.99923 | **0.98950** |
| boosting: many weak (depth 2, 800 trees) | 0.99973 | 0.92645 |
| boosting: deep + subsampling | 0.99963+-0.00005 | 0.98885+-0.00043 |
| MLP [12]x8 (ours) | 0.99997 | 0.97518+-0.00343 |

Boosting beat our network on the hard day (0.98885 against 0.97518) and turned
out to be three times as stable. Without subsampling its spread is exactly
zero - it is deterministic.

**Held-out set: boosting AUC 0.898 / 0.944 / 0.914 = 0.918+-0.019** against
0.862+-0.005 for the network. On AUC, a clear win.

### THE MAIN DISCOVERY: AUC is the wrong metric for our task

The cost curve on the held-out set (how many false alarms on the way to the N-th
hit):

| caught | MLP | boosting | LSTM |
| --- | --- | --- | --- |
| 1 | 17 | 7 | **3** |
| 4 | 17 | 508 | 67 |
| 8 | 55 | 8 053 | 102 |
| **16** | 245 | **23 781** | **188** |
| 32 | 2 154 | 48 848 | 3 734 |
| 48 | 185 613 | 304 954 | 137 014 |

Boosting wins ONLY in the tail - on the last windows, which nobody will ever
open. In the working region it is a hundred times worse.

**Mechanism.** There are 64 positive examples and 3.6 million negative ones. AUC
averages over all pairs, so a model can rack up a high score by neatly sorting
the hopeless tail while the top of the list is dirty. And the top is all anyone
looks at.

A check on day 12 showed the same thing on other models:

| model | false alarms before the 1st | before the 3rd | before the 6th | before the 9th | AUC |
| --- | --- | --- | --- | --- | --- |
| LSTM-24 | **1** | **5** | **7** | **30** | 0.98999 |
| SSM (S4-lite) | 14 | 17 | 26 | 80 | 0.98844 |
| external memory | 8 | 250 | 1 795 | 2 715 | 0.98509 |
| LMU | 63 | 361 | 863 | 2 319 | 0.97219 |
| echo state network | **3 406** | 4 244 | 4 327 | 4 361 | 0.96859 |

**Three times in one day AUC named the wrong winner.** The echo state network,
with a respectable AUC of 0.969, needs 3406 false alarms before the FIRST window
is found, against one for the LSTM - a factor of three and a half thousand for a
difference of two hundredths in AUC.

Every earlier comparison in this diary made by AUC has to be reread with this in
mind. The cost curve is the right metric.

### Experiment 2 - a recurrent network over the sequence of a host's windows

Implementation: windows are grouped by source and ordered in time; a sequence of
up to 24 windows is fed into an LSTM/GRU; there is a prediction at every step,
so the comparison with the per-window models stays apples to apples.

| model | parameters | day 8 | day 12 |
| --- | --- | --- | --- |
| MLP [12]x8 | 1333 | 0.99997 | 0.97518+-0.00343 |
| LSTM hidden=12 | 1549 | 0.99989 | 0.98899+-0.00034 |
| **LSTM hidden=24** | 4249 | 0.99998 | **0.98999+-0.00042** |
| LSTM hidden=48 | 13105 | 0.99999 | 0.98996+-0.00074 |
| GRU hidden=48 | 9841 | 1.00000 | 0.98946+-0.00035 |

At comparable size (1549 against 1333) the recurrent network gives +1.4 points
and a spread ten times smaller.

**Held-out set, LSTM-24 (three seeds): AUC 0.922 / 0.915 / 0.890 = 0.909+-0.014,
price of the first 16 hits 136 / 188 / 499.**

The MLP, for comparison: AUC 0.862+-0.005, price 237-300.

**THIS IS THE FIRST IMPROVEMENT IN THE WHOLE PROJECT THAT HAS TRANSFERRED TO THE
HELD-OUT SET ON BOTH METRICS.** The previous four changed the data or the
add-on; this one changes the REPRESENTATION of the task - for the first time the
network sees a node's trajectory rather than an isolated window.

Worth noting separately: hand-built accumulation of suspicion failed all the way
down to AUC 0.504, while learned memory works. The difference is that the
accumulation rule was set by hand, and set wrongly, whereas the recurrent
network finds its own.

### Experiment 3 - nine architectures, including exotica

| architecture | parameters | day 8 | day 12 |
| --- | --- | --- | --- |
| **LSTM-24** | 4249 | 0.99998 | **0.98999+-0.00042** |
| two-layer LSTM | 9049 | 0.99976 | 0.98904+-0.00030 |
| diagonal SSM (S4-lite) | 2305 | 0.99999 | 0.98844+-0.00165 |
| bidirectional LSTM-16 | 4641 | 0.99999 | 0.98555+-0.00144 |
| external memory (simplified NTM) | 2418 | 0.99936 | 0.98509+-0.00121 |
| TCN (dilated convolutions) | 4849 | 1.00000 | 0.98257+-0.00012 |
| LMU (Legendre polynomials) | **723** | 0.99846 | 0.97219+-0.01137 |
| echo state network (reservoir) | **65 trainable** | 0.99410 | 0.96859+-0.00159 |
| transformer, self-attention | 10225 | 0.99990 | **0.93700+-0.01062** |

**Conclusions.**

1. **The exotica did not beat the plain LSTM.** Not external memory, not
   self-attention, not dilated convolutions.
2. **The transformer is the worst of the lot.** Explainable: self-attention
   needs a lot of data (we have 3835 sequences), and our sequences are short (24
   steps) - there is simply nothing distant to link up. Ten thousand parameters
   and the worst result: the model is bigger than the task.
3. **The frugality of the exotica is impressive but misleading.** Echo state
   network: the reservoir is random and FROZEN (5248 weights, declared via
   `register_buffer`), and only the readout is trained - 65 parameters. AUC
   0.969. But the cost curve showed that a detector built from it is useless
   (3406 false alarms before the first hit). The LMU on 723 parameters gives
   0.972, better than our original MLP on 1333, but at the top of the list it
   too is weaker than the LSTM.
4. **The diagonal SSM is the only serious alternative**: 0.98844 at 2305
   parameters against 4249 for the LSTM, and a decent cost curve (14 false
   alarms before the first).

### State at the end of the day

**Champion: LSTM-24 over the sequence of a host's windows, 4249 parameters.**

| | day 8 | day 12 | held-out set |
| --- | --- | --- | --- |
| AUC | 0.99998 | 0.98999 | 0.909+-0.014 |
| price of the first 16 hits | - | - | **136-499** |

The previous champion (MLP, 1333 parameters): held-out set AUC 0.862, price
237-300.

---

## 2026-08-31 - COINCIDENCES CAN BE GENERATED AFTER ALL: the article's conclusion is refuted

### What was claimed

The section "synthetic data does not produce coincidences" claimed that a normal
window carrying the full compromise signature cannot be generated, because "a
coincidence is the absence of a mechanism, and the generator can only generate
mechanisms". The argument was that to do so you would have to generate an
intrusion and call it normal, that is, lie in the labels.

### An objection to myself

No lying is needed. Those 51 windows in the real data are **honestly normal**:
there was no intrusion in them; legitimate activity simply happened to combine
high novelty with a high failure share. So it is enough to build a machine on
which that combination arises BY DESIGN, without a single foreign account. The
label "normal" stays true.

The objection stands. The earlier attempts failed because the mechanisms were
specified separately (a terminal server gives novelty, a broken service gives
failures) and I WAITED for them to coincide by chance. At our scale they never
did.

### What was done

`gen/world-coin.tdc` introduces an explicit coincidence mechanism: a machine
with the `isCoin` flag, during its hour `coinHour`, produces a turnover of 0.95
(almost all accounts are new to this machine, but MOVED - they already exist
elsewhere in the network) and an elevated failure share `coinFailMil` =
0.15..0.60. The `Foreign` flag stays zero: there are no foreign credentials, so
the label is honest.

Physical interpretation: a round of the machines after a password change. The
accounts are new to these machines, and some of the logins fail on stale
credentials.

### Result of the first world

| | normal windows | with the full signature | share |
| --- | --- | --- | --- |
| reality (day 8) | 231 772 | 51 | 0.0220% |
| previous base world | 3 045 | **0** | 0.0000% |
| previous rich world | 21 868 | **0** | 0.0000% |
| **world with the mechanism (share 0.5%)** | 22 416 | **11** | **0.0491%** |

Coincidences appeared, and at the same order of magnitude as in reality.

**The article's conclusion about a fundamental limit is wrong.** The limit was
not in the nature of the generator but in the mechanism never having been
specified explicitly. The wording in the article will have to be rewritten once
transfer has been measured.

### What gets checked next

Three hypotheses, each with its own control:

1. **coincidences** - six worlds with shares of 0.5 / 1.0 / 1.5 / 2.5 / 3.5 /
   5.0%;
2. **world diversity** - a control set of six worlds with the same seeds and a
   zero coincidence share (`gen/make-control.sh`), to separate the effect of
   diversity from the effect of coincidences;
3. **one network per world plus a joint decision** - the earlier ensembles
   failed for a known reason: all the members were trained on ONE world, and the
   spread of their opinions was 0.0002. Different worlds should raise that
   spread; it will be the direct measure of whether the cause has been removed.

Both AUC AND the search price are measured: after the boosting and echo-network
episodes, AUC on its own is not to be trusted.

Code: `gen/world-coin.tdc`, `gen/make-worlds.sh`, `gen/make-control.sh`,
`net_py/factorial.py`, `net_py/per_world.py`.

---

## 2026-08-31 - FACTORIAL EXPERIMENT: coincidences, volume, world diversity

### Real coincidences are not built the way I imagined

Before judging transfer, it was worth taking a look at those 51 real windows.
Medians:

| feature | ordinary normal | **real coincidences** | intrusion |
| --- | --- | --- | --- |
| events per window | 22 | **2** | 26 |
| accounts | 2 | **1** | 8 |
| destinations | 4 | **1** | 19 |
| history size | 3564 | **1** | 336 |
| known accounts | 4 | **1** | 15 |
| moved accounts | 0 | **2** | 26 |
| rhythm | 1.7 | **0.0** | 1.1 |

**Real coincidences are tiny windows on machines with almost no history.** Two
events, one account, one destination. With a single account the novelty share is
either zero or one; a failure share >=0.15 comes from one failed login out of
two. So to a large extent this is **an artifact of shares being unstable on a
small sample**, not some rich legitimate mechanism.

My generated coincidences ("the round after a password change"), by contrast:

| | events | accounts | destinations | history |
| --- | --- | --- | --- | --- |
| real | 2 | 1 | 1 | 1 |
| **mine** | **14** | **11** | **12** | 0 |
| intrusion | 26 | 8 | 19 | 336 |

**In shape, my coincidences are closer to an intrusion than to the real
coincidences.** Hence a prediction, made BEFORE measuring transfer: little
benefit and possibly harm - I am teaching the network not to fire on something
that looks like a real attack.

A separate consequence: the coincidence threshold I chose (novelty share >=0.9
AND failure share >=0.15) fires almost automatically on tiny windows. So the
article's conclusion about a "fundamental limit" rested partly on a badly chosen
threshold, not only on the nature of synthetic data.

### Six worlds: coincidence shares

| world | share in config | windows | labelled | coincidences |
| --- | --- | --- | --- | --- |
| 0 | 0.5% | 25 169 | 2 753 | 11 (0.0491%) |
| 1 | 1.0% | 25 100 | 2 732 | 4 (0.0179%) |
| 2 | 1.5% | 25 033 | 2 625 | 5 (0.0223%) |
| 3 | 2.5% | 25 154 | 2 685 | 43 (0.1914%) |
| 4 | 3.5% | 25 247 | 2 534 | 16 (0.0704%) |
| 5 | 5.0% | 25 420 | 2 682 | 14 (0.0616%) |

The real 0.0220% falls within the spread. The relation between the share in the
config and the number of coincidences is nonlinear: the mechanism does not
always produce the signature; it depends on how many of the machine's events
landed in its window.

### Result (recurrent network, 3 seeds)

| training set | windows | coinc. | d8 AUC | d12 AUC | false before 6th |
| --- | --- | --- | --- | --- | --- |
| **base world, 400k** | 3 045 | 0 | 0.99998 | **0.98999+-0.00042** | **7** |
| rich world, 8M | 21 868 | 0 | 0.99459 | 0.97082+-0.00144 | 3 801 |
| one world with 1.5% coincidences | 22 408 | 5 | 0.99541 | 0.97196+-0.00163 | 3 526 |
| six worlds merged, 0.5-5% | 135 112 | 93 | 0.99779 | 0.98054+-0.00289 | 2 948 |

**Three conclusions.**

1. **Coincidences had an effect, but a small one.** 0.97196 against
   0.97082 - within the spread; search price 3526 against 3801, that is, minus
   7%. The prediction made from the shape of the coincidences held: the
   mechanism works but does not change the picture.
2. **World diversity is more effective than coincidences**. Six merged worlds:
   0.98054 against 0.97082 for one large world, false alarms 2948 against 3801.
3. **The small base world beats them all.** 3045 windows against 135 thousand,
   and a search price of 7 against 2948 - a four-hundred-fold difference.

### The "world x architecture" interaction - a new finding

The rich world was previously measured with the FULLY CONNECTED network, and
there it was BETTER than the base world (0.98779 against 0.97518). With the
recurrent network the ranking flipped: base 0.98999 against 0.97082 for the rich
one.

Probable cause: in the rich world the attack has stages, and the first is quiet
(4% foreign events). A per-window model judges each window in isolation, while
the recurrent one sees the sequence and, having learned the quiet stages, starts
firing on quiet normal windows. For a model with temporal memory, a training set
like that turns out to be poison.

None of the earlier architecture comparisons took into account which world the
models were trained on. That is a lesson in its own right: **the architecture
and the training world cannot be chosen separately.**

### What runs next

- a control set of six worlds with a ZERO coincidence share
  (`gen/make-control.sh`) - to separate the effect of diversity from the effect
  of coincidences;
- the same sets on three architectures (`net_py/arch_on_worlds.py`) - to check
  whether the ranking flips yet again.

---

## 2026-08-31 - THE RANKING OF ARCHITECTURES DEPENDS ON THE WORLD (confirmed twice)

Three architectures on two training sets, three seeds each:

| set | model | d8 AUC | d12 AUC | false before 6th |
| --- | --- | --- | --- | --- |
| base world 400k | **recurrent** | 0.99998 | 0.98999+-0.00042 | **7** |
| base world 400k | SSM | 0.99999 | 0.98844+-0.00165 | 26 |
| base world 400k | fully connected | 0.99997 | 0.97518+-0.00343 | 13 |
| six worlds merged | **SSM** | 0.99918 | 0.98482+-0.00563 | **434** |
| six worlds merged | fully connected | 0.99528 | 0.98149+-0.00288 | 2 217 |
| six worlds merged | recurrent | 0.99779 | 0.98054+-0.00289 | 2 948 |

**The order flipped.** On the base world the recurrent network is the best (7
false alarms); on the merged worlds it is the worst (2948), and the SSM has
become the best (434).

This is the SECOND independent confirmation of the "world x architecture"
interaction. The first: the rich world improved the fully connected network
(0.97518 -> 0.98779) and wrecked the recurrent one (0.98999 -> 0.97082). One
observation can be written off as chance; two is a property.

**A consequence for all of our earlier conclusions.** The sweep of 93 networks,
the nine sequence architectures, the councils - all of it was measured on ONE
base world. The conclusions "depth beats width", "the recurrent network is the
best", "the transformer is the worst" hold for that world and do not carry over
automatically. The article has to say so explicitly.

**The training world and the architecture are one decision, not two.**

### The unpleasant outcome of the enrichment line

The small base world of 3045 windows remains the best of everything we have
built: a search price of 7 against 434 for the best combination on the merged
worlds. A sixty-fold difference.

Over the evening the world was enriched: attack stages, eight mechanisms of
normal behaviour, independent property flags, an explicit coincidence mechanism,
six worlds instead of one, 135 thousand windows instead of three. Within the
line of enriched worlds there is a gain, and it is measurable (six worlds beat
one: 2948 against 3801; coincidences beat their absence: 3526 against 3801). But
**the whole line loses to the original simple version**.

A possible explanation, still to be checked: the rich world contains attack
stages, and the first of them is quiet (4% foreign events). Training on quiet
stages teaches the model to fire on quiet windows, and quiet normal windows are
the overwhelming majority in a real network. The check: switch the stages off
and keep the other mechanisms.

---

## 2026-08-31 - THE CAUSE OF THE ENRICHMENT LINE'S FAILURE: quiet attack stages

### Hypothesis

In the base world, on a compromised machine ALL events in the period are
foreign - the attack is always loud. The rich world introduced stages, and the
first one is quiet: 4% foreign events. The suspicion: training on quiet stages
teaches the model to fire on quiet windows, and quiet normal windows are the
overwhelming majority in a real network.

### Check

The same world, the same generation, ONE config line changed: instead of `Stage
== 0 ? 0.04 : (Stage == 1 ? 0.18 : ...)` there is a constant `1.0`.

| world | model | d12 AUC | false before 6th |
| --- | --- | --- | --- |
| rich WITH stages | recurrent | 0.97196+-0.00163 | 3 526 |
| **rich WITHOUT stages** | **recurrent** | **0.99243+-0.00016** | **0** |
| base (reference) | recurrent | 0.98999+-0.00042 | 7 |
| rich WITH stages | SSM | 0.98420+-0.00192 | 245 |
| rich WITHOUT stages | SSM | 0.95273+-0.02080 | 445 |
| base (reference) | SSM | 0.98844+-0.00165 | 26 |

**The hypothesis is confirmed, and the result is the best of the whole
project.** One line, and the search price drops from 3526 to ZERO: six real
windows in a row at the top of the list, not a single false alarm between them.
AUC 0.99243 with a spread of 0.00016.

### The third case of the same mechanism

| change | intent | outcome |
| --- | --- | --- |
| training on diluted windows | teach it to see 1 foreign event out of 37 | 1428 false alarms instead of 27 |
| accumulating suspicion over hours | an intrusion lasts for hours | AUC 0.504 |
| **attack stages** | **an attack starts quietly** | **3526 false alarms instead of 7** |

All three are attempts to teach the model to see a WEAK SIGNAL. All three
produced a model that fires on WEAK NOISE. The mechanism is the same: a weak
signal in training is indistinguishable from the background noise at evaluation,
and the model memorises the noise as a feature.

**The rule: a rare phenomenon cannot be taught from its weak manifestations if
those weak manifestations are indistinguishable from the background.** Train on
clear cases, and catch the weak ones by other means - for instance, by
accumulating over time AT INFERENCE TIME, not in the training set.

### And a third confirmation of the "world x architecture" interaction

For the SSM it is the other way round: 245 false alarms with stages, 445
without. The very same change to the world improves the recurrent network
twentyfold and makes the SSM twice as bad.

Three independent confirmations on different data and different models. The
conclusion holds: **the training world and the architecture cannot be chosen
separately.**

### The project's current best result

The world `gen/world-nostage.tdc` (rich, without stages) + the recurrent network
with 4249 parameters: day 12 - AUC 0.99243, zero false alarms before the sixth
window found.

---

## 2026-08-31 - THE CONTROL EXPOSED THE TRUE CAUSE OF COINCIDENCES: window sparsity

### The control worlds did not come out at zero

Six control worlds (the same seeds, coincidence mechanism share = 0%):

| world | with the mechanism | control (mechanism off) |
| --- | --- | --- |
| 0 | 11 | 10 |
| 1 | 4 | 3 |
| 2 | 5 | 4 |
| 3 | 43 | 42 |
| 4 | 16 | 13 |
| 5 | 14 | 5 |

The substitution in the config has been verified: `percent="0,100"` is in place.
**My explicit coincidence mechanism added one window out of forty-three.**
Something else is generating the coincidences.

### What exactly: window density

The distribution of the number of events in a normal window:

| world | 1% | 10% | 25% | 50% | 75% | 90% | windows <=2 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **reality (day 8)** | 2 | 8 | 15 | 22 | 33 | 49 | **1.1%** |
| base 400k | 5 | 9 | 11 | 16 | 26 | 53 | 0.1% |
| rich 8M | 19 | 27 | 33 | 45 | 72 | 131 | 0.0% |
| coin 1.5M | 2 | 4 | 6 | 9 | 14 | 25 | 3.3% |

Coincidences showed up in the coin worlds not because of the mechanism but
because I shrank the world (1.5M events over the same 2000 machines): the
windows became four times sparser, and the shares on them drifted. It is THE
SAME mechanism as in reality (where coincidences are two-event windows),
reproduced by accident and at the wrong scale: my coincidences have 24 events
each against the real 2.

**Reality has a wide distribution: a median of 22 and a tail of 1.1% tiny
windows.** None of the earlier worlds reproduces this shape: the base one is too
narrow (tail 0.1%), the rich one too dense (tail 0%), coin uniformly sparse
(median 9).

### A methodological lesson

Without the control set the effect would have been credited to the explicit
mechanism, and a false statement would have gone into the article. The control
cost one script run.

### What is being built

`gen/world-sparse.tdc`: a world without stages, 4M events, 18% "quiet" machines
with their hours spread over 80..260 (their events get smeared into tiny
windows). The target is a median of ~22 with a tail of ~1% windows <=2, as in
reality.

---

## 2026-08-31 - A COUNCIL OF NETWORKS, EACH TRAINED ON ITS OWN WORLD (first run)

Six coin worlds (with stages - that is, poisoned; this is the first run, the
clean one will be on worlds without stages). One LSTM-24 per world, with the
judge trained on the synthetic exam `rich-exam`.

### The mechanism worked

**Spread of opinions between the networks: 0.00488** against 0.0002 for networks
trained on one world. A 24-fold increase. The diagnosis of the earlier ensemble
failure ("the members agree, so there is nothing to average") is confirmed from
the other direction: different worlds give different views.

### But quality did not improve

| method | d8 AUC | d8: before 1st | d12 AUC | d12: before 1st | d12: before 6th |
| --- | --- | --- | --- | --- | --- |
| best single | **0.99623** | **572** | **0.97299** | 2 851 | **3 410** |
| rank averaging | 0.99396 | 1 045 | 0.97083 | 3 487 | 4 030 |
| judge | 0.99406 | 655 | 0.96648 | **1 288** | 5 530 |

Neither averaging nor the judge beats the best single network on AUC. On day 12
the judge is half the price before the first hit (1288 against 2851) but twice
the price before the sixth. A mixed picture with no winner.

**A caveat without which the conclusion is wrong:** the absolute numbers here
are terrible (thousands of false alarms) because all six worlds are poisoned by
quiet attack stages - established by a separate measurement. The spread of
0.00488 may in part be a spread of errors rather than a spread of opinions. The
real test of the idea is the same experiment on six worlds WITHOUT stages; it is
queued.

Code: `net_py/per_world.py`. Log: `results/per_world_coin.log`.

---

## 2026-08-31 - THE SPARSE WORLD: coincidences of the right shape and a new best result

`gen/world-sparse.tdc`: a world without stages, 4M events, 18% "quiet" machines
with their hours spread over 80..260 - their events get smeared into tiny
windows.

### The window shape is close to reality for the first time

| | reality (day 8) | sparse world |
| --- | --- | --- |
| events per window 1% / 50% / 90% | 2 / 22 / 49 | 1 / 19 / 57 |
| windows with <=2 events | 1.1% | 6.5% |
| coincidences | 51 | 9 |
| coincidences: median events | **2** | **4** |

For the first time the coincidences are tiny, like the real ones (previously 24
events). The tail is still too fat (6.5% against 1.1%): the share of quiet
machines could be lowered, but that would be tuning on the working days, and we
do not do that before the held-out set.

### Result (3 seeds)

| model | d8 AUC | d12 AUC | d12: before 1st | before 6th |
| --- | --- | --- | --- | --- |
| **recurrent** | **1.00000** | **0.99327+-0.00104** | **0** | **0** |
| SSM | 0.99998 | 0.94309+-0.00533 | 0 | 9 |

**The recurrent network on the sparse world is the project's best result on the
working days:** day 8 is perfect, day 12 is 0.99327 against 0.99243 for the
world without stages and 0.98999 for the base one, with zero false alarms before
the sixth window found.

And once more the "world x architecture" interaction: on the same world the SSM
collapses to 0.94309 - worse than on any other world. The fourth confirmation.

### These are the working days - and what follows from that

Four times in this project a gain on the working days has failed to transfer to
the held-out set. So the next step is the held-out set, without a single change
to the world.

---

## 2026-08-31 - THE COUNCIL ON CLEAN WORLDS: the mechanism is proven, there is no gain

Six worlds without stages (`gen/make-nostage-worlds.sh`), one LSTM-24 per world.

| world | windows | labelled | coincidences |
| --- | --- | --- | --- |
| ns-0...ns-5 | 25 300-25 622 | 3 666-3 858 | 1-55 |

### Spread of opinions: 0.01409

Against 0.0002 for networks on one world (x70) and 0.00488 on the poisoned coin
worlds (x3). The idea is confirmed for the third time, each time more strongly:
the more diverse the worlds, the less the networks agree. The cause of the
earlier ensemble failure has been removed.

### But the ensemble does not win

| method | d8 AUC | d8: before 6th | d12 AUC | d12: before 1st | before 6th | before 12th |
| --- | --- | --- | --- | --- | --- | --- |
| **best single** | 1.00000 | 0 | **0.99586** | 0 | 0 | 7 313 |
| rank averaging | 1.00000 | 0 | 0.99491 | 0 | 0 | 8 420 |
| judge | 0.99889 | 257 | 0.99242 | 746 | 747 | 9 706 |

Rank averaging is level with the best single network (and it is an honest
ensemble with no selection on the test, whereas the "best single" was picked by
day 12, so its number is optimistic). The judge is worse on everything - for the
fourth time in a row. **World diversity raised the spread but did not let the
ensemble beat a single network: the networks became different, yet equally right
where it is easy and equally blind where it is hard (the same last two windows
at ranks 7313+).**

**0.99586 is a new working-days record** (previous: the sparse world, 0.99327).

### Candidates for the held-out set

Three: the sparse world (one network), the merged ns worlds (one network), the
rank ensemble of six ns networks. All three go to the held-out set at once; the
article will have to state that the champion was chosen from three candidates by
the held-out set - so its number is slightly optimistic.

---

## 2026-08-31 - THE ENSEMBLE ON THE HELD-OUT SET: the first add-on that transferred

Six LSTM-24, one per ns world (without stages), combined by rank averaging.
Trained on synthetic data only; the held-out set is used for evaluation only.

| false alarms before the N-th hit out of 64 | 1 | 2 | 4 | 8 | 16 | 24 | 32 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| previous champion: LSTM on the base world | 3 | 10 | 67 | 102 | 188 | 412 | 3 734 |
| **ensemble of six ns networks** | **0** | **2** | **2** | **3** | **7** | **19** | **621** |

AUC 0.93819 against 0.909. **In the working region, 27 times cheaper.** The
first hit comes with no false alarms at all.

This is the first ensemble-type improvement in the whole project to transfer to
the held-out set. All the earlier ones (council, judge, weak learners,
symbiosis) lost to a single network - and all of them were on ONE world. The
difference: here each network learns on its own world, with a spread of opinions
of 0.014 against 0.0002.

**Open question - where does the gain come from:** the ensemble, or the ns
worlds themselves? A single LSTM on the merged ns worlds will answer that; it is
running now. If the single network gives the same result, the credit goes to the
worlds; if worse, to the ensemble.

### An engineering failure

Two runs I had been waiting on for 28 minutes had died on the first line: a
`ytr.sum()` check had been added to `heldout_lstm.py`, but `to_sequences`
returns a list of arrays. The wait loops were polling logs that the completion
line could never reach. A mistake of the same kind as checking "the file exists"
instead of "the file is fresh": what to wait for is not the presence of the log
but a sign of a live process. Fixed, restarted.

---

## 2026-08-31 - THREE CANDIDATES ON THE HELD-OUT SET: the gain comes from the ensemble, not the worlds

All three were trained on synthetic data only. Held-out set: 3 600 398 windows, 64 labelled.

| candidate | AUC | before 1st | before 4th | before 8th | **before 16th** | before 32nd |
| --- | --- | --- | --- | --- | --- | --- |
| previous champion: one LSTM, base world | 0.909 | 3 | 67 | 102 | 188 | 3 734 |
| sparse world, one LSTM (3 seeds, median) | 0.935 | 4 | 21 | 29 | 301 | 881 |
| six ns worlds MERGED, one LSTM (3 seeds) | 0.863 | 814 | 1 978 | 6 992 | **26 297** | 98 511 |
| **six ns worlds, six LSTM, rank averaging** | **0.938** | **0** | **2** | **3** | **7** | **621** |

### Attribution

Merging the same six worlds into one set for one network fails outright: 26 297 false
alarms before the 16th, against 7 for the ensemble of the same worlds. A 3700-fold
difference on identical data. **The gain comes from the ensemble structure, not
from what is in the worlds.**

The mechanism: the worlds differ in coincidence share and seed; merged into one set,
they present the network with contradictory boundaries and it learns mush.
Trained separately, the six networks each hold an internally consistent view, and rank
averaging takes the best of each where they disagree. This matches the
measured spread of opinions: 0.014 between the separately trained networks.

**Rule: keep world diversity in separate models; never merge it into a single dataset.**

### The sparse world - ambiguous

A single network on the sparse world beats the previous champion at the
very top (before 8th: 29 against 102) and in the tail (before 32nd: 881 against
3734), but loses in the middle (before 16th: 301 against 188). The spread across
seeds is wide (133-303). The window shape is right; the stability is not there yet.
The natural next step is an ensemble of sparse worlds: the right shape combined
with separate training.

### Accounting of held-out set accesses

Three more candidates today. In total, the held-out set has now seen at least
nine configurations. The winner was picked from among them, so its number is
optimistic; the article says so explicitly.

---

## 2026-08-31 - ATTRIBUTION CLOSED: two jumps, the world and the ensemble

One LSTM on a single clean world, ns-0 (without stages, 25 300 windows), on the held-out set:

| seed | AUC | before 16th | before 32nd |
| --- | --- | --- | --- |
| 7 | 0.91789 | 15 | 1 048 |
| 17 | 0.92383 | 43 | 3 656 |
| 27 | 0.90663 | 30 | 2 382 |

Median: 0 / 1 / 1 / 2 / **30** / 222 / 2 382.

### The full ladder (false alarms before the N-th hit out of 64)

| configuration | 1 | 4 | 8 | **16** | 24 | 32 |
| --- | --- | --- | --- | --- | --- | --- |
| base world, one LSTM (previous champion) | 3 | 67 | 102 | 188 | 412 | 3 734 |
| **one clean world, one LSTM** | 0 | 1 | 2 | **30** | 222 | 2 382 |
| **six clean worlds, six LSTM, ranks** | 0 | 2 | 3 | **7** | 19 | 621 |
| six clean worlds, MERGED, one LSTM | 814 | 1 978 | 6 992 | 26 297 | 59 973 | 98 511 |

**Two independent jumps.**
1. **The world:** base -> clean (without stages, with the sparsity that comes from the small size)
   takes 188 -> 30 at the 16th. The world does matter; the previous entry's "the gain
   is not from the worlds" was incomplete.
2. **The ensemble:** one clean world -> six separately trained networks takes 30 -> 7 at the
   16th, and does even more in the tail: 222 -> 19 at the 24th, 2382 -> 621 at the 32nd.
   Right where a single network starts to make mistakes, the different views correct
   each other.
3. **Merging** the same worlds into one set for one network: 26 297, which is 140 times
   worse than the base world. Diversity merged into a dataset becomes a
   contradiction; spread across models, it becomes a strength.

**The precise statement:** the win is the clean world multiplied by separate
training. Neither of the two gives the seven on its own.

Held-out set access count: +1, at least ten configurations in total.

---


## 2026-08-31 - CONTROL: six seeds on one world. It is the different worlds that matter

Six LSTM-24 networks on ONE base world with different seeds (7...57), rank averaging,
held-out set:

| seed | AUC |
| --- | --- |
| 7 / 17 / 27 / 37 / 47 / 57 | 0.922 / 0.915 / 0.890 / 0.922 / 0.921 / 0.932 |

Spread of opinions: **0.00415** (six DIFFERENT worlds gave 0.01409).

Single-world ensemble: AUC 0.91713, false alarms 11 / 15 / 42 / 80 / **117** / 504 / 6 945.

### Full attribution ladder on the held-out set

| configuration | 1 | 8 | **16** | 24 | 32 | what it isolates |
| --- | --- | --- | --- | --- | --- | --- |
| base world, one network | 3 | 102 | 188 | 412 | 3 734 | reference point |
| base world, 6 seeds, ranks | 11 | 80 | 117 | 504 | 6 945 | averaging by itself |
| one clean world, one network | 0 | 2 | 30 | 222 | 2 382 | the clean world by itself |
| **six clean worlds, 6 networks, ranks** | **0** | **3** | **7** | **19** | **621** | clean + different worlds |
| six clean worlds, merged, one network | 814 | 6 992 | 26 297 | 59 973 | 98 511 | merging |

**The contributions, separated out:**
- averaging six seeds of one world: 188 -> 117 (x1.6), and worse in the tail
  (6945 against 3734). Weak and ambiguous;
- a clean world without stages: 188 -> 30 (x6). Strong;
- six different clean worlds trained separately: 30 -> 7 (x4), and 2382 -> 621 in the tail.
  It is the diversity of the worlds, not the number of models; the control proved it;
- merging the worlds: a catastrophe (x140 worse than the base).

**The final formula: clean world x different worlds x separate networks x ranks.**
Each factor is measured on its own; none of them gives the seven by itself.

The spread of opinions turns out to be a good predictor of how much an ensemble will help: 0.0002 (one
world, one seed set) -> no gain; 0.004 (six seeds) -> x1.6; 0.014 (six
worlds) -> x4 plus the tail. One more measurement that can be taken BEFORE
touching the held-out set.

Held-out set access count: +1, at least eleven in total.

---

## 2026-08-31 - SIX SPARSE WORLDS ON THE HELD-OUT SET: the project's best AUC, but six storms above the first attack

Putting the two wins together: the right window shape (`gen/world-sparse.tdc`, 18%
quiet machines) x six networks trained separately on six worlds with coincidence
shares of 0.5...5% (`gen/make-sparse-worlds.sh`). Rank averaging.

Shape of the six worlds: 6.5-7.3% of the normal windows have <=2 events (the ns worlds
have 3.0-3.4%, reality 1.1%), 10-15 coincidences per world.

### Single networks on the held-out set (3.6M windows, 64 labelled)

| world | AUC | false alarms before 1 / 8 / 16 / 24 / 32 |
| --- | --- | --- |
| sp-0 | 0.94621 | 11 / 18 / 34 / 229 / 801 |
| sp-1 | 0.93808 | 1 / 8 / 12 / 108 / 407 |
| sp-2 | 0.92498 | 7 / 10 / 10 / 122 / 804 |
| sp-3 | 0.94459 | 2 / 6 / 7 / 187 / 6 343 |
| sp-4 | 0.94024 | 13 / 15 / 22 / 97 / 10 846 |
| sp-5 | 0.95209 | 5 / 9 / 45 / 91 / 365 |

Every single sparse-world network beats every single ns-world network on AUC
(0.907-0.924), and beats their ensemble (0.938) too. Spread of opinions 0.00854.

### Ensemble against ensemble

| | six clean (ns) | six sparse (sp) |
| --- | --- | --- |
| AUC | 0.93794 | **0.94374** |
| false alarms before 1 / 2 / 4 / 8 | **0 / 2 / 2 / 3** | 6 / 7 / 7 / 9 |
| false alarms before 16 | **7** | 10 |
| false alarms before 24 / 32 | **19 / 621** | 61 / 3 870 |
| worst attack rank | - | 1 940 734 |

The best AUC in the project, and a cost curve that is worse along its whole length. The third law, for
the third time: AUC and the cost of the search diverge, and you cannot choose by AUC.

### What stands above the first attack (diagnosis from the saved scores)

Six windows to which ALL six networks give the maximum rank, 1.0000. The
ensemble is powerless here, because there is no disagreement:

| host | hour | events | users | new users | failure share | new triples |
| --- | --- | --- | --- | --- | --- | --- |
| C21454 | 540 | 390 | 4 | 1 | 0.93 | 362 |
| C21454 | 539 | 1 314 | 4 | 1 | 0.98 | 1 286 |
| C15244 | 348 | 2 337 | 4 | 1 | 0.25->0.99 | 2 |
| C15244 | 354 | 1 729 | 4 | 1 | 0.98 | 1 |
| C21454 | 538 | 1 220 | 3 | 1 | 0.98 | 1 197 |
| C17693 | 661 | 2 | 2 | 2 | 1.00 | 2 |

Five of the six are not tiny coincidences but **failure storms**: hundreds or
thousands of events an hour, 90-99% failures, one or two new users. C21454
also has hundreds of new triples (user x source x destination): one user
walks through hundreds of destinations and fails almost every time.
By the red team's labels this is normal. In substance, to an analyst it is a finding
(a broken service or brute force), not an error. The metric cannot see the difference.

The sixth window is C17693, slot 661: the same host as all 64 labelled windows,
two events from two new users, both failures, sitting between the labelled
slots 659 and 683. There is no way to be sure, but it looks like an unlabelled piece of the same
activity.

Ranks of the 64 labelled windows in the ensemble's ranking: 22 in the first fifty, 32 in
the first 772, then a tail stretching down to 1.94M.

### Why the networks are so sure: there are no storms in the worlds

Normal windows with >=100 events and >=90% failures:

| set | normal windows | storms | windows with >=100 new triples |
| --- | --- | --- | --- |
| LANL day 8 | 231 772 | 3 | 68 |
| LANL day 12 | 223 975 | 13 | 177 |
| ns-0 / ns-2 | 21 634 / 21 559 | 0 / 0 | 4 / 4 |
| sp-0 / sp-2 | 22 278 / 22 134 | 0 / 0 | 21 / 21 |
| synth-exam | 3 049 | 0 | 2 |

Not one training world contains a single normal storm. Role 7,
"service with a broken password", is in the config (`isBrok`, 7% of machines), but it produces
30-80% failures at ordinary volume; it never comes close to a LANL storm (126-2 351 events an hour,
1-4 users, 2-9 destinations, 90-100% failures, sometimes on a machine with no
history at all). The networks have never seen a normal storm, so they
take one for an attack. For some reason the ns networks are more restrained on the same windows; that question
stays open, and the difference between the worlds is not in the failures here (the 99th percentile of the failure share among normal windows is
0.80 in ns and 0.77 in sp).

### What next

Hypothesis: add a "storm" role to the sparse world: 1.5% of machines with 1-2
users, 2-9 destinations, 90-100% failures and a dense schedule
(1-4 hours), labelled normal. Check it first on working days 8 and 12, then
with a single access to the held-out set.

In the interest of honesty: the hypothesis came from examining the TOP of the held-out set, so
any improvement after this point is tuning on the held-out set, and the article
has to say so plainly. In parallel, the ns ensemble has been rerun with its scores
saved (a reproducibility check of the seven, and material for a window-by-window comparison).

Held-out set access count: +1 (the sp ensemble) and an examination of its top
thirty windows; at least twelve in total.

---

## 2026-08-31 - RERUN OF THE ns ENSEMBLE, TWELVE NETWORKS, TIE CHECK, STORMS THROUGH THE EYES OF THE ns NETWORKS

### Reproducibility of the seven

A second run of the six ns networks on the held-out set (same seeds): the cost curve
0 / 2 / 2 / 3 / 7 / 19 / 621 is reproduced exactly, AUC 0.93819 against 0.93794.
The individual AUCs differ from the first run in the hundredths (training is not bit-for-bit
deterministic), but the top of the ranking is stable. The scores of all the networks are now
saved (`results/ns-heldout-scores.npy`, `results/sp-heldout-scores.npy`).

### The ns networks see the same storms

The six windows that sit above the first attack in the sp ensemble sit at
ranks 2, 12, 20, 26, 28 and 3 in the ns ensemble. The ns networks' ranks on them are 0.9998...1.0000, so
the ns networks ALSO take the storms for an attack. The difference "0 against 6 false alarms before the first"
comes down to the order within the top thirty: ns puts one real attack (C17693,
slot 326) in first place, sp puts it seventh. Both families push the storms to
the very top, because none of the twelve worlds contains a storm.

### No ties

The worry: the sigmoid might have saturated to exactly 1.0 on dozens of windows, in which case
the order at the top would be set not by the network but by the sort on host name.
The check: each network has exactly one window with the maximum score, the top-100
of each ensemble has 97-98 distinct values, and the cost curve under the worst and the best
tie-breaking matches the computed one. The order at the top is real.

### Twelve networks (ns + sp)

| ensemble | AUC | false alarms before 1 / 2 / 4 / 8 / 16 / 24 / 32 |
| --- | --- | --- |
| ns x6, rank averaging | 0.93819 | 0 / 2 / 2 / 3 / 7 / 19 / 621 |
| sp x6, rank averaging | 0.94374 | 6 / 7 / 7 / 9 / 10 / 61 / 3 870 |
| ns+sp x12, rank averaging | 0.94261 | 0 / 2 / 3 / 3 / 7 / 15 / 1 144 |
| ns+sp x12, rank median | 0.94384 | 6 / 8 / 8 / 9 / 10 / 27 / 406 |

Spread of opinions across the twelve: 0.014. More worlds do no harm and barely help:
the head is the same, the tail lands between the two families. Twelve networks cannot fix
a mistake that all twelve make. An ensemble cures disagreement, not
a shared delusion, and a shared delusion comes from a shared hole in the worlds.

### The storm world on the working days (`gen/world-storm.tdc`, one world)

Added the "storm" role: 1.5% of machines, 1-2 users, 90-100% failures, all
events within 1-4 hours. The world has 66 normal storms (median 178 events), the window
shape is unchanged (1 / 19 / 59, windows with <=2 events 7.4%), 48 coincidences (median 13 events;
the sparse world had 9 with a median of 4, so the storms brought in large
coincidences).

| model | d8 AUC | d12 AUC | d12: before 1st | before 6th |
| --- | --- | --- | --- | --- |
| recurrent, sparse world | 1.00000 | 0.99327+-0.00104 | 0 | 0 |
| **recurrent, storm world** | 0.99998 | **0.99379+-0.00082** | 0 | 3 |
| SSM, sparse world | 0.99998 | 0.94309+-0.00533 | 0 | 9 |
| **SSM, storm world** | 0.99991 | **0.99316+-0.00045** | 0 | 33 |

Recurrent: AUC slightly higher (within the spread), false alarms before the 6th went from 0
to 3; where they went is checked separately (`net_py/storm_check.py`: the ranks of the 13
storms of day 12 under the networks of both worlds). The SSM on the storm world climbed from
0.943 to 0.993, the fourth confirmation of the "world x architecture" law: same
network, same day, different world, and a different architecture wins.

Held-out set access count: +2 (the twelve networks, two ways),
at least fourteen in total.

### Where the storms of day 12 went (`net_py/storm_check.py`, two networks per world)

Where the 13 normal storms of day 12 land in the ranking (out of 224k windows):

| world | seed | AUC | false alarms before 1/2/4/6/8 | top three storms | first 8 labelled |
| --- | --- | --- | --- | --- | --- |
| sparse | 7 | 0.99385 | 0/0/0/0/41 | 178, 928, 1 058 | 1 2 3 4 5 6 10 49 |
| sparse | 17 | 0.99182 | 0/0/0/0/5 | 35, 168, 217 | 1 2 3 4 5 6 7 13 |
| with storms | 7 | 0.99422 | 0/0/0/0/40 | 1 229, 1 968, 2 187 | 1 2 3 4 5 6 29 48 |
| with storms | 17 | 0.99264 | 0/0/0/3/189 | 3 539, 3 781, 4 050 | 1 2 3 4 5 9 144 197 |

The "storm" role pushes the storms down 7-100 times, and the attacks stay in the top places.
But the storms have not gone all the way into the normal range (ranks 1 000-4 000 out of 224 000), and under
seed 17 C3699@295 got into the top six: 31 events, two users, one of them
new, not a single failure: a "scanner", one user fanning out over new
destinations. The same host sits in the top thirty of the held-out set.
This is a second kind of normal that the worlds lack.

Six storm worlds launched -> ensemble -> held-out set
(`gen/make-storm-worlds.sh`, prefix st). Pitfall: the substitution pattern for the coincidence
share also matched the isStorm line (also 1.5%), so the storm share would have drifted
along with the coincidence share; caught before generation, and the pattern narrowed to the isCoin line.

### LANL fan-out windows: whose they are

Normal windows on the working days with >=100 new triples (day 8: 68 windows on 58
hosts; day 12: 177 on 114): median 163-170 events, 3-4 users,
all of them new (newUserRatio 1.0), 9-10 destinations, zero failures, host history
**0**. This is the first hour of a new host: everything is new by definition, and nothing fails.
The world does have such a role (role 2, 0.6% of machines), but its windows are four times smaller
(10-40 events against 110-324). C3699 is a different case: a known host
(history 2 277), 1-2 users, 27 new triples an hour on day 12: a scanner.
Before fixing anything, first see what exactly the storm-world network puts at the top
on the working days (`net_py/top_false.py`, queued after the chain).

---

## 2026-08-31 - SIX STORM WORLDS ON THE HELD-OUT SET (tuning, access no. 15)

The "storm" role (1.5% of machines, 1-2 of the machine's own users, 90-100% failures, 1-4 hours)
in six worlds with coincidence shares of 0.5...5%; one LSTM-24 per world; ranks.
Individual AUCs: 0.941 / 0.942 / 0.927 / 0.925 / 0.947 / 0.935; spread of opinions
0.0123.

| ensemble | AUC | false alarms before 1 / 2 / 4 / 8 / 16 / 24 / 32 |
| --- | --- | --- |
| ns x6 (clean) | 0.93819 | **0 / 2 / 2 / 3 / 7** / 19 / 621 |
| sp x6 (sparse) | 0.94374 | 6 / 7 / 7 / 9 / 10 / 61 / 3 870 |
| **st x6 (with storms)** | 0.94072 | 3 / 4 / 4 / 5 / 8 / 24 / 389 |
| ns+st x12 | 0.94167 | 0 / 2 / 3 / 4 / 7 / **11 / 357** |
| ns+sp+st x18 | 0.94206 | 0 / 2 / 3 / 4 / 7 / 13 / 587 |

Against the sparse family the "storm" role improves the whole curve (6->3 before the first, 61->24
before the 24th, 3 870->389 before the 32nd). Against the clean family the head is slightly worse and the tail twice
as good. Combining the families, ns+st, gives the best tail in the project (11 before the 24th, 357 before
the 32nd) with the head of the clean family. More DIFFERENT world families means a better tail; more seeds
of the same family does not (see the control above).

### The storms have not gone

The held-out set has 249 normal storms. Ranks of the first eight:

| family | storm ranks |
| --- | --- |
| ns | 2, 12, 19, 20, 26, 28, 35, 40 |
| sp | 1, 2, 3, 4, 5, 8, 15, 16 |
| st | 1, 2, 5, 11, 14, 17, 22, 25 |

The top of st: C21454@540 and @539 at ranks 1-2 (a storm with 362-1 286 new
triples), C17693@661 in 3rd (two events, two new users, both
failures, adjacent to the labelled slots), the first attack, C17693@326, in 4th,
C15244@354 in 5th.

### Why: the wrong storm

| set | storms | with a new user | with >=100 new triples |
| --- | --- | --- | --- |
| held-out | 249 | 173 | **106** |
| day 12 | 13 | 3 | 3 |
| st-0 / st-1 / st-2 | 66 / 60 / 72 | 39 / 28 / 36 | **1 / 0 / 0** |

The "storm" role reproduces a storm with one new user (the worlds have
28-39 of those, a share close to the held-out set's), and it did push the storms of day 12 down. But 106 of
the 249 storms in the held-out set are a fan-out over hundreds of new destinations (the same
user gets a failure from hundreds of machines in a row). The worlds have 0-1 of those: the
role has dstSpan 2..9. This is a scanner storm, and C21454 is its specimen. The second kind, C15244
(a storm plus one new user, history 155), does exist in the worlds, yet the network
still puts it in 5th place: three dozen examples are apparently too few, or
the role does not reproduce how young the host is (history 155).

Honestly: three world configurations in a row have now been evaluated on the held-out set by examining
its own top. The number "7 false alarms before the 16th for the ns ensemble" remains
the only one obtained BEFORE that examination; everything after it is tuning, and the article
will call it that. Further world edits get checked on working
days 8 and 12 (`net_py/top_false.py`), with the held-out set touched once, at the end.

Held-out set access count: +3 (st, ns+st, ns+sp+st), at least
seventeen in total.

---

## 2026-08-31 - WHAT IS LEFT ON THE WORKING DAYS: a user's relocation (`net_py/top_false.py`)

The storm-world network (seed 7), day 8: AUC 1.00000, 14 labelled windows
at ranks 1-14. Day 12: AUC 0.99422, six labelled at ranks 1-6, then
29, 48, 105, 627, 6 819, 7 969.

The top forty NORMAL windows of day 12: 22 of them belong to one host, **C3699**.
A known machine (history 2 277 records); from 6 in the morning until the evening (slots 290-311,
consecutive) there is one user, new to this machine but seen on others
(movedUserCount = all of his events), 27-51 events an hour, 1-5 destinations,
**not a single failure**. This is a person who moved to another machine and is working
there all day. The others at the top, C20621, C21542, C21919, C18025, are young
hosts (history 2-677) with one fresh user (freshUserCount = all
events: the account has never been seen anywhere before), no failures, several hours in a row:
a new account. Both pictures are a **persistent legitimate newcomer**: one new
user, zero failures, many hours in a row.

An attack looks different: 2-16 new users, failures 0.14-0.70, a few
hours and then it is gone. But there is an overlap: C17693@683 (one event, one new
user, 0 failures) is labelled. Only duration and headcount tell them
apart, which is exactly what a recurrent network over a host's sequence
could learn, if only the world had relocations. It has none: the Churn mechanism gives
one-off strangers, role 2 gives a new host, and nothing produces "a known user
came to a known machine and stayed".

### `gen/world-move.tdc`: the "relocation" and "newcomer" roles

On top of the storm world: 2% of machines get "relocation" (from the hour moveHour onwards, half
of the events come from another machine's user, `((hid*37+11) % 2000)*30`, an account already
seen elsewhere on the network), 1% get "newcomer" (the same, but the account is `90000 + hid`, seen nowhere).
No failures (the ordinary baseMil), the machine's ordinary destinations. Labelled normal.
One world: 25 760 windows, 62 storms, shape 1 / 19 / 58, windows with <=2 events 6.9%.
Checked on the working days: `eval_world` + `top_false`.

For the honesty record: this step was taken on working days 8 and 12, not on
the held-out set.

### Relocation v1: no effect. Why

The world with the "relocation"/"newcomer" roles (the arrival uses the owner's destinations):
day 12 AUC 0.99292+-0.00058, 0 false alarms before the 6th, but C3699 stayed put (ranks 11-36,
20 of the top 40 normal windows). A breakdown of the composition: windows of the "relocation" kind (moved >=10,
failures <5%, new users >=40%) already numbered 457 on 102
hosts in the storm world, coming from administrator rounds and one-off maintenance; the role added
little (438). The difference from C3699 is in the **triples**: the synthetic relocations have 0 new
triples (the arrival goes to servers the machine already knows), while C3699 has 27 out of 27
events: the arrival goes to HIS OWN servers, new both to the machine and to him.
The feature tripleNewCount = events whose three edges are all new at once.

### Relocation v2: the arrival with his own destinations - the best result on the working days

`gen/world-move.tdc`: the arrival's destinations are 5000..5904 (a range of his own,
new to everyone). World: 25 725 windows, 64 storms, shape 1 / 19 / 60, windows with <=2 events
7.1%, 21 coincidences.

| model | d8 AUC | d12 AUC | d12: before 1st | before 6th |
| --- | --- | --- | --- | --- |
| recurrent, sparse | 1.00000 | 0.99327+-0.00104 | 0 | 0 |
| recurrent, with storms | 0.99998 | 0.99379+-0.00082 | 0 | 3 |
| recurrent, relocation v1 | 1.00000 | 0.99292+-0.00058 | 0 | 0 |
| **recurrent, relocation v2** | **1.00000** | **0.99636+-0.00044** | **0** | **0** |
| SSM, relocation v2 | 0.99993 | 0.98192+-0.01630 | 0 | 7 |

`top_false` (seed 7): day 8: 15 labelled at ranks 1-15; day 12:
AUC 0.99644, **eight labelled at ranks 1-8**, zero false alarms before the 8th
(previously six at 1-6 and 40 false alarms before the 8th). **C3699 has left the top forty
entirely.** One config line, found by looking at one feature.

What is left on day 12 now is the first hours of brand-new hosts: history 0-74,
1-2 fresh accounts (freshUserCount = all events), 8-188 events, sometimes with
failures 0.67-0.99 (C22758, C22692: a new host set up with the wrong
password). In the world the "new host" role is 0.6% of machines; on day 12, hosts with
fresh accounts make up ~4%. Next step: the share of role 2 -> 3% (`gen/world-newhost.tdc`).

The SSM is unstable on every relocation world (+-0.013...0.016), the same network that
gave 0.993+-0.0005 on the storm world. The fifth confirmation of "world x architecture".

### New hosts 3% (`gen/world-newhost.tdc`): the third step of the micro-loop

One line: the share of role 2, "new host", 0.6% -> 3%. World: 26 141 windows,
80 storms, shape 1 / 19 / 60, windows with <=2 events 6.4%, 44 coincidences.

| model | d8 AUC | d12 AUC | d12: before 1st | before 6th |
| --- | --- | --- | --- | --- |
| recurrent, relocation v2 | 1.00000 | 0.99636+-0.00044 | 0 | 0 |
| **recurrent, + new hosts 3%** | **1.00000** | **0.99743+-0.00053** | **0** | **0** |
| SSM, + new hosts 3% | 0.99997 | 0.95158+-0.01427 | 0 | 0 |

`top_false` (seed 7): day 8: 15 at ranks 1-15; day 12: AUC 0.99679,
eight labelled at ranks 1-8, the ninth at 50th (was 48), the tenth at 162nd
(was 468). The new hosts have left the top; C3699 is partly back (8 windows,
from rank 15 down). What remains are windows with a single failed login on young hosts
(history 2-36): a lone coincidence, sparsity's territory. Returns are diminishing;
the micro-loop stops here.

### The micro-loop ladder on the working days (day 12, recurrent, 3 seeds)

| world | what was added | d12 AUC | before 6th |
| --- | --- | --- | --- |
| sparse | the tail of quiet machines | 0.99327+-0.00104 | 0 |
| with storms | a service with a broken password (from the held-out set) | 0.99379+-0.00082 | 3 |
| relocation v2 | an arrival with his own destinations (from day 12) | 0.99636+-0.00044 | 0 |
| **new hosts 3%** | the share of first hours of new hosts (from day 12) | **0.99743+-0.00053** | 0 |

Each step is one or two config lines, found by examining a specific
host at the top of the false alarms. This is how the generator is meant to work: reality
shows a gap, the config closes it, the network stops making that mistake.

Six final worlds launched (prefix nh, coincidence shares 0.5...5%) ->
ensemble -> held-out set. This is access no. 18, and the last in the line of worlds.

---

## 2026-08-31 - THE END OF THE LINE OF WORLDS ON THE HELD-OUT SET (access no. 18) AND ADDING FAMILIES

Six final worlds (`gen/world-newhost.tdc`: sparsity + storm +
relocation v2 + 3% new hosts; coincidence shares 0.5...5%), one LSTM-24 each.
Individual AUCs: 0.902 / 0.900 / 0.911 / 0.881 / 0.929 / 0.878, **the lowest
in the project**. Spread of opinions **0.0042**, the same as six seeds of one world: the networks
of the final family are nearly unanimous.

| ensemble | AUC | false alarms before 1 / 2 / 4 / 8 / 16 / 24 / 32 |
| --- | --- | --- |
| ns x6 (clean) | 0.938 | 0 / 2 / 2 / 3 / 7 / 19 / 621 |
| st x6 (storm) | 0.941 | 3 / 4 / 4 / 5 / 8 / 24 / 389 |
| **nh x6 (final)** | **0.907** | **1 / 1 / 1 / 1 / 2** / 43 / 2 538 |

The worst AUC and the best head: **two false alarms before the 16th attack** against seven. The tail
is worse (43 and 2 538). The third law for the fourth time, and now in both directions:
a world that taught the network that newcomers, storms and new hosts are normal made it
more cautious. It picks out strong attacks more cleanly and pushes weak ones (the ones that look like newcomers)
deeper down.

### The top of the final ensemble

Ranks 1-18: **seventeen labelled windows and one C17693@661** (two events,
two new users, both failures, the same host, between the labelled slots
659 and 683). The storms dropped to ranks 155+. The only outside hosts in
the top twenty are C7307@64 (11 events, one new user, all failures,
history 7) and C23322 (single-event windows). Ranks of the 64 labelled: 28 in
the first hundred, 32 in the first 2 570.

### Adding families - the answer to the "twenty networks" question

| ensemble | networks | AUC | false alarms before 1 / 2 / 4 / 8 / 16 / 24 / 32 |
| --- | --- | --- | --- |
| ns | 6 | 0.938 | 0 / 2 / 2 / 3 / 7 / 19 / 621 |
| ns + nh | 12 | 0.924 | 0 / 1 / 1 / 1 / 1 / 4 / 615 |
| st + nh | 12 | 0.927 | 1 / 1 / 1 / 1 / 1 / 7 / 342 |
| **ns + st + nh** | **18** | 0.932 | **0 / 1 / 1 / 1 / 1 / 4 / 316** |
| ns + sp + st + nh | 24 | 0.937 | 0 / 1 / 1 / 1 / 1 / 7 / 326 |

**Eighteen networks from three families: one false alarm before the 16th attack, four before the 24th,
316 before the 32nd.** From 188 for the previous champion (one network, base world) down to 1.
The best curve in the project at every point.

Saturation by families: one family: 7; two: 1 (tail 4...7); three: 1 / 4 / 316;
four: 1 / 7 / 326. The third family still improves the tail; the fourth (sp, which shares
its blindness to storms with st) does not. **What counts is not the number of networks but the number of DIFFERENT
views: world families with different phenomena.** Six seeds of one world gave
117; six worlds of one family, 7; three families, 1. The spread of opinions
predicts this: 0.004 / 0.014 / (higher between families).

### Honesty accounting - for the article

- **The only number obtained before examining the held-out set:** ns x6,
  7 false alarms before the 16th (AUC 0.938). That is the honest transfer result.
- The "storm" role: from examining the top of the held-out set (tuning).
- Relocation v2 and new hosts: from working days 8 and 12; but they sit on top of the storm
  world, and they were checked on the held-out set once.
- The choice of the family combination: on the held-out set (tuning).
- Held-out set accesses over the project: at least **23** (+1 nh, +4
  combinations). In the article: present the "18 networks, 1 false alarm" result
  as "after examining the errors on the held-out set", next to the honest seven.

### What the day showed

The generator closes the gaps one at a time: reality shows a host, the config
gets a line, the network stops making that mistake: the storm (ranks 1-5 -> 155+),
the relocation (C3699: 22 of the top 40 -> zero), the new hosts. Each edit is one or two
lines of TDC. The ensemble adds up families, not seeds.

### The ensemble saturation curve (`net_py/saturation.py`, an access to the saved scores)

Random subsets of the 24 networks from the four families (ns, sp, st, nh), 12
samples per point; false alarms before the 16th / 24th / 32nd, median [min..max]:

| networks | before 16th | before 24th | before 32nd |
| --- | --- | --- | --- |
| 1 | 43 [3..329] | 293 [100..424] | 1 397 [407..10 846] |
| 2 | 10 [1..108] | 109 [6..218] | 763 [253..9 711] |
| 3 | 7 [1..28] | 27 [11..73] | 724 [264..2 662] |
| 4 | 4 [1..33] | 24 [9..62] | 636 [363..1 129] |
| 6 | 3 [1..11] | 24 [7..99] | 606 [204..1 068] |
| 8 | 3 [1..5] | 10 [2..46] | 440 [320..817] |
| 12 | **1** [1..5] | **5** [1..16] | 367 [279..607] |
| 16 | 1 [1..4] | 7 [2..29] | 331 [256..516] |
| 24 | 1 | 7 | 326 |

Saturation around 12 networks: past that the median does not move, only the
spread narrows. The objection was right: "twenty is better than six", provided the twenty
are drawn from different families. A single network is a lottery (3...329); eight networks
are already reliable (1...5).

Six networks, one family against a mix (medians before 16 / 24 / 32):

| composition | before 16th | before 24th | before 32nd |
| --- | --- | --- | --- |
| ns x6 | 7 | 19 | 621 |
| st x6 | 8 | 24 | 389 |
| nh x6 | 2 | 43 | 2 538 |
| 2 ns + 2 st + 2 nh | 4 | 36 | 532 |
| 3 ns + 3 nh | 2 | 22 | 777 |

On a budget of six networks, a mix of families is no better than one good family: the gain
from diversity shows up only when each family has enough networks (4-6 each).
Bottom line: **both the number of networks and the number of families matter; saturation comes at around 12-18 networks
from 3 families**.

Held-out set access count: +1 (the final family nh), +4 (family combinations), +1 (the saturation curve over the saved scores); at least 23 over the project in total.

---

## 2026-08-31 - SUMMARY OF THE DAY

The summary of the second day (what was checked, how, why, with the numbers and with which
conclusions of the article it changes) has been moved out to FACTS.md, section 16 (16.0-16.9).
Here in the chronicle stay all the runs in order, including the failed ones and the pitfalls.

## 2026-08-31 - Article corrected against the facts

`~/IdeaProjects/TDC_press/articles/index_6.html` proofread in full against
the repository; the backup from before the edits is `index_6.html.pered-pravkami-faktov`. 14 targeted
edits: the seven was not dissected (the storms were found in the sparse family),
the attribution ladder uses clean worlds, not sparse ones (plus a definition of the clean world),
the window shape table (1st percentile / median / 90th; base world 5 / 16 / 53),
the comment on `1..4` for the storm (hours, not destinations), the difference between relocation v1/v2 is in
the Dst formula (a line added), the introduction reconciled with the ending, "three rounds"
given a reference point, C3699 after the third round, the easy day's range
0.99995-0.99998, "eight figures".
Markup checked with a parser: no unclosed tags.

## 2026-08-31 - Article: second pass, the logic of the narrative

Backup: `index_6.html.pered-logikoj`. 22 edits: notes "for those not in
the know" (percentile, seed and training seed, AUC, the rich world and the attack
stages); terms introduced on first appearance (window, fully connected network,
recurrent network/LSTM with its 0.990 on the hard day, boosting, baseline,
ranks, world family); reference points (the base world's 0.990 in the micro-loop table;
where the eighteen networks come from); the four announced "threes" laid out as lists
(the reasons for the task, the conclusions on capacity, the honest conclusions, the conditions for deployment);
the lines "administrator on rounds" and "a layer on top of weak
learners" explained. Markup checked with a parser. The insert on sparsity: backup
`index_6.html.pered-razrezhennostju`.

## 2026-08-31 - Typography: ASCII everywhere

Typography across the whole project and in the article brought to a single form:
guillemets -> straight quotes, em and en dashes -> hyphen, arrows -> "->",
greater-or-equal and less-or-equal signs -> ">=" "<=", plus-minus -> "+-", the fraction sign -> "1/2",
the multiplication sign -> "x", the single-character ellipsis -> three dots. Affected:
*.md, gen/*.tdc (comments only, checked line by line), net_py/*.py,
judge/*.mjs, exam/*, gen/*.sh and the article text (text nodes only, tags
untouched). All py/mjs/sh checked by compiling them, the HTML by a parser. Backup:
_backup-typography-*.tar.gz and index_6.html.pered-tipografikoj.
