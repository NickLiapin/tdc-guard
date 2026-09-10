Russian version: [FACTS.ru.md](FACTS.ru.md)

A digest of the project's measured numbers. Every number points to a run in DIARY.md;
what was obtained before I started dissecting the held-out set is marked separately from what came after.

# TDC-Guard - fact pack for the article

Everything the text is allowed to claim, and nothing beyond it. The numbers are
reproducible: the configs are deterministic given the `seed`, and the Los Alamos data is public.

---

## 1. The problem

**The phenomenon:** lateral movement - operating inside the network under someone else's
valid credentials. The password is correct, nothing fails, the account is real.

**The exam data:** LANL "Comprehensive, Multi-Source Cyber-Security Events"
(A. D. Kent, 2015). 58 days, 17 684 computers, 12 425 users, 1.65 billion events.
A mirror for direct download: `lanl.ma.ic.ac.uk/data/cyber1/`.

**The labelled ground truth:** 749 red-team exercise events -
104 accounts, 301 destination machines, **4 sources**, with 94% of the events coming from a single
foothold, C17693.

**Unit of observation:** a "machine x hour" window, 18 features.

---

## 2. What was measured before the generator was written

| fact | number |
| --- | --- |
| the exercise's main "victim", U66, in a clean slice | 30 497 logins (an ordinary administrator) |
| accounts on domain controllers (legitimately) | 2500-3000 (C586, C529, C467, C1065: 2996, 2752, 2686, 2590) |
| accounts on file servers / workstations | 252, 118, 110 / 1, 2, 1 |
| share of new edges for normal windows: median / 90th / 99th percentile | **0.0000 / 0.0000 / 0.5000** |
| failure share for normal windows | 0.68% (1.54% for U-accounts) |

**Conclusion:** the naive "many accounts from one machine" counter is fooled by servers;
the signal is relational - how novel an edge is in the login graph.

---

## 3. The generator

| fact | number |
| --- | --- |
| size of the base world config | ~130 lines |
| generation speed | 400 000 events in **9 s** |
| rich world | 8 000 000 events, 2000 machines |
| training windows (base world) | 3835, of which 790 labelled |
| training windows (rich world) | 25 365, of which 3497 labelled |

**The mistake that cost more than all the tuning put together.** "Foreign" accounts were drawn as a
number from a range and existed nowhere in the network:

| in labelled windows | reality | synthetic before the fix |
| --- | --- | --- |
| account known to the network, but seen on this machine for the first time | 26 | 2 |
| account that never existed in the network at all | 0 | 11 |

After the fix (the account now belongs to another real machine in the world), day 8 at the
same full recall showed **false alarms down fourfold** (27 -> 6) and precision at the
0.99 threshold **doubled** (0.357 -> 0.714).

---

## 4. The network

| fact | number |
| --- | --- |
| final architecture | 18 -> [12]x8 -> 1 |
| weights | **1333** |
| training time | seconds on a laptop, no GPU |
| dependencies | numpy, torch |
| AUC on synthetic data with a different seed | 0.99996 |

---

## 5. Capacity sweep (93 networks in 170 s, 3 seeds each)

| architecture | weights | day 8 | day 12 |
| --- | --- | --- | --- |
| flat [4] | 81 | 0.99868+-0.00184 | 0.94208+-0.00946 |
| flat [8] | 161 | 0.99998+-0.00001 | 0.94151+-0.00945 |
| flat [100] | 2001 | 0.99997 | 0.95939+-0.00743 |
| flat [256] | 5121 | 0.99997+-0.00000 | 0.95646+-0.00693 |
| two steps [24,12] | 769 | 0.99997+-0.00002 | 0.94112+-0.00436 |
| two steps [128,64] | 10753 | 0.99995+-0.00002 | 0.96318+-0.01032 |
| deep [16,16,16] | 865 | 0.99991+-0.00004 | 0.96520+-0.00442 |
| **deep [12]x8** | **1333** | 0.99997+-0.00002 | **0.97518+-0.00343** |
| deep [12]x12 | 1957 | 0.99940+-0.00046 | 0.94923+-0.01033 |
| wide [100,50,25] | 8251 | 0.99997+-0.00003 | 0.96366+-0.01136 |

**Three conclusions.**
1. The dense day is saturated: everything from 161 weights to 10 753 gives 0.99996-0.99998.
   The capacity floor lies between 4 and 8 neurons.
2. Depth beats width: 1333 weights (0.975) against 10 753 (0.963).
3. Too deep is bad as well: [12]x12 drops to 0.949. The optimum is 6-8 layers.

---

## 6. Results on real data

### Day 8 - dense activity (a working day; the one the knobs were tuned on)

231 787 windows, 15 labelled.

| | |
| --- | --- |
| caught | **15 of 15** |
| false alarms at threshold 0.99 | 11 (DIARY, version 7) |
| ranks of the labelled windows | all within the first 32 of 231 787 |
| AUC | 0.99999 |

The price of full recall - how many false alarms it takes to catch all 15:

| method | false alarms |
| --- | --- |
| "accounts from one machine" counter | 175 904 |
| "destinations from one machine" counter | 206 651 |
| a rule fitted to the answers | never gets there |
| **our network** | **10** |

### The held-out set - the honest exam

Sixteen days (1,2,5,6,7,9,13,14,15,20,21,22,26,27,28,29) that were never
touched. **3 600 398 windows, 64 labelled.**

| method | AUC | false alarms before 16 of 64 |
| --- | --- | --- |
| a rule fitted to the answers | 0.516 | 536 916 |
| "destinations" counter | 0.535 | 99 855 |
| "accounts" counter | 0.618 | 161 100 |
| **our network** | **0.862 +- 0.005** | **237-300** |

The spread across days is huge: from 4 of 4 in the top twenty (day 26) to 0 of 8
(day 5). An average over a spread like that says little.

---

## 7. The main result: the baseline scissors

**The baseline poisons itself.** By day twelve the foothold "knows"
84 accounts, **and 49 of them are the very accounts that were used to move through it**.
**58.3% of the machine's "normal history" is the observed phenomenon itself.**

**A frozen baseline drifts:**

| day | machines unknown to the baseline |
| --- | --- |
| 9 | 1.1% |
| 15 | 3.3% |
| 29 | **6.1%** |

The rate is **0.25% of machines per day**. 39% of all false alarms on the held-out set
land on such machines (on day 8 there were none).

**The formula:** refresh the baseline often and it gets poisoned by what it observes;
freeze it and it drifts. The working point: a baseline no younger than a week and no
older than two or three. This holds for any behavioural detector.

---

## 8. Limits of the method (measured)

| limit | number |
| --- | --- |
| cold start | day 1: 464 history events per machine against 3500 on day 8; 1 of the 19 labelled windows in the top hundred |
| diluted windows | 1 foreign event among 37; 2 among 65 |
| zero novelty | one window: novelty 0 on all three axes, rank 210 243 of 223 987 |

---

## 9. Coincidences - why we hit a ceiling

**Normal windows with the full signature of an intruder** (novelty >=0.9 AND failures >=0.15):

| | such windows |
| --- | --- |
| reality | **51 of 231 772 (0.022%)** |
| base world | 0 of 3045 |
| rich world | 0 of 21 868 |

The features are reproduced individually, but not jointly:

| | novelty >=0.9 | failures >=0.15 | both |
| --- | --- | --- | --- |
| reality | 0.644% | 0.669% | 0.022% |
| rich world | 0.887% | 6.933% | 0.000% |

In reality the features are positively correlated (under independence it would be 0.004%;
the observed value is 0.022%, five times higher).

**The cause, found by measurement:** in the first version the mechanisms were MUTUALLY EXCLUSIVE
roles, so a coincidence was ruled out by construction. After I replaced them with independent
flags and made the world 20 times larger, the synthetic data for the first time stopped being
solved to a perfect score (0.99781 against 0.99993), but coincidences at this threshold
still never appeared.

---

## 10. What did not work (negative results)

| attempt | outcome |
| --- | --- |
| training on diluted windows | **1428 false alarms instead of 27**; the mechanism was worked out: dilution teaches that any event with triple novelty means an intruder, and 1330 normal windows contain such events |
| temporal wrapper (accumulating suspicion) | anywhere from neutral to destructive, AUC 0.504; the same self-poisoning mechanism, repeated at the scale of hours |
| council of strong networks | day 12 better, held-out set worse |
| judge over strong networks | 0.955 against 0.981 for a single network - worse in every line-up |
| judge over weak learners | the mechanism works (for the first time the judge beats averaging), but the level stays below a single network: 0.973+-0.019 |
| symbiosis (mixed pool) | 0.970+-0.028 against 0.979+-0.009 for the best member |
| rich world | day 12 +1.26 points (3.5 sigma), held-out set unchanged, cost 100 times worse |

**Spread of opinions among the strong networks: 0.0002.** They make their mistakes in the same
places, so there is nothing to average.

---

## 11. Methodological conclusion

Four improvements in a row that showed gains on the working day **did not transfer** to the
held-out set - including one that stood 3.5 times above the seed noise.

The reason: we measured the spread across training seeds, but there is a second source of noise -
**exactly which 12 windows happened to be labelled**. Reseeding cannot catch it.

**Twelve examples are not a measure, whatever the seed spread.**

---

## 12. Comparison with existing work

**Academic papers on the same data:** modern graph methods reach AUC 0.92-0.95 on
LANL. Our held-out result of 0.862 is lower. But those methods
train on the labelled Los Alamos data itself; we did not use a single
real line of it. A head-on AUC comparison across different protocols is not valid.

**Industrial systems:** Microsoft Defender for Identity, Exabeam, IBM QRadar
UBA, Splunk UBA, Varonis. They build a profile of your network. They need weeks of observation,
and some need labelled incidents, which an ordinary organisation does not have.

**Our difference:** the model arrives already trained, from a world that does not exist. But the
network's history is still needed - as measured on the early days.

### The practical outcome of the comparison

Picking the right reference point matters. Against the EXPECTATION that "the detector
catches everything" the result is modest. Against what is actually deployed, it is noticeably better:

| on the held-out set | AUC | false alarms before 16 of 64 |
| --- | --- | --- |
| threshold "destinations" counter | 0.535 | 99 855 |
| threshold "accounts" counter | 0.618 | 161 100 |
| **network trained on synthetic data** | **0.862** | **237** |

**A 400-600x gain in the cost of alarms** - even though the counters work directly
on the real data and the network has never seen it. On these days the threshold rules do
little better than random (0.5 = chance).

Hence the honest position on deployment: **as an additional first-pass triage layer**
the method is usable right now. It does not replace industrial systems and is not
fit for automatic blocking, but it gives the analyst a meaningful queue
where threshold rules give noise. And, unlike systems trained on their own data,
it needs not a single labelled incident from your network.

---

## 13. Mistakes in our own engineering

| mistake | how it was found |
| --- | --- |
| the exam passed 12 of the 16 features, the missing ones arrived empty | AUC exactly 0.50000 |
| the same defect repeated in the comparison file | AUC exactly 0.50000 a second time |
| the threshold search was quadratic and never finished on 3.6M values | the run never completed |
| the wait condition checked that the file existed, not that it was fresh | the "result" matched the old one digit for digit |
| our own rule "check the synthetic data before training" was broken | the result halved |

---

## 14. Code

```
gen/world.tdc              base world, ~130 lines
gen/world-rich.tdc         rich world: attack stages, independent mechanisms
gen/measure-synth.mjs      measuring the synthetic data
judge/windows.mjs          feature measurer (shared by synthetic and real data)
judge/rows.mjs             loader that checks all features are present
net_py/data.py             reading and encoding, numpy is the only dependency
net_py/model.py            MLP with a configurable architecture
net_py/evaluate.py         rank-based AUC and the cost curve, one pass
net_py/sweep_big.py        sweep over 31 architectures
net_py/council.py          council and judge
net_py/weak_council.py     weak learners
net_py/symbiosis.py        mixed pool
exam/*.mjs                 runs on real data
```

**Honesty check, done by measurement:** day 8 was recomputed with two
independent implementations of the measurer, and **231 787 rows matched exactly** (the only
difference being how zeros are written).

---

## 15. Material for illustrations

| chart | data |
| --- | --- |
| capacity curve | the table in section 5: weights against AUC on day 12 |
| depth against width | the same data, two lines |
| novelty distribution | normal (median 0.0000) against labelled (1.0000) |
| baseline drift | 1.1% -> 3.3% -> 6.1% over days 9/15/29 |
| price of full recall | the tables in section 6, logarithmic scale |
| transfer of improvements | the table in section 11: working day against held-out |
| baseline poisoning | 58.3% of the machine's history is the phenomenon itself |

## Update of the reference table (2026-08-31, night) - the same held-out set (16 LANL days, 64 windows, 3.6M windows)

The "whose" column: **mine** - the networks from this article, trained on TDCv2 synthetic data only;
**others'** - published research papers, trained on labelled
LANL data. The "when" column: "before the review" - the number was obtained before I
started dissecting the errors on the held-out set (honest transfer); "after
the review" - the world was edited on the basis of held-out set errors (tuning, to be flagged
as such in the article).

| whose | solution | ROC AUC | false alarms before the 16th of 64 | training | when |
|---|---|---|---|---|---|
| others' | LMTracker (heterogeneous graph embedding) | ~0.95 | not published | labelled LANL | - |
| **mine** | **six LSTM-24, sparse worlds, rank averaging** | **0.944** | 10 | synthetic only | before the review |
| mine | six LSTM-24, storm worlds | 0.941 | 8 | synthetic only | after the review |
| **mine** | **six LSTM-24, clean worlds, rank averaging** | **0.938** | **7** | synthetic only | before the review |
| mine | twenty-four LSTM-24, four world families | 0.937 | 1 | synthetic only | after the review |
| mine | eighteen LSTM-24, three world families | 0.932 | **1** | synthetic only | after the review |
| others' | UGEA-LMD (continuous-time dynamic graph) | 0.9254 | not published | labelled LANL | - |
| mine | XGBoost boosting (from the article) | 0.918 | 23 781 | synthetic only | article |
| mine | one LSTM-24, base world (from the article) | 0.909 | 188 | synthetic only | article |
| mine | six LSTM-24, final worlds | 0.907 | 2 | synthetic only | after the review |
| mine | MLP, 1333 parameters (from the article) | 0.862 | - | synthetic only | article |
| - | accounts-per-machine counter (rule) | 0.618 | ~161 000 | - | article |
| - | destinations counter (rule) | 0.535 | - | - | article |
| others' | Argus (RNN + GNN) | AUC not published | - | labelled LANL | - |
| others' | UltraLMD++ (graph foundation model) | AUC not published, recall@budget | - | labelled LANL | - |

One LSTM-24 has 4 249 parameters, an ensemble of six 25 494, an ensemble of eighteen
76 482. The single networks of the sparse worlds: 0.925...0.952 (the best is 0.952, but picking
the best by the held-out set is tuning; the median is 0.942).

**How to read it.** By AUC the synthetic approach has entered the range of the research
papers: above UGEA-LMD (0.9254), below LMTracker (~0.95), with a gap of ~0.006 to the upper
bound. The article's caveat stands: the evaluation protocols differ (splits,
transductive/inductive), a head-on AUC comparison is not valid, and this is a coordinate
system, not a tournament. For the price of the search there are no reference points: none of the
others publish it, except UltraLMD++ (recall@budget, a different scale). AUC and price
diverge here too: the best AUC (0.944) does not come with the best price (1).

---

## 16. Day two (2026-08-31, evening and night): what was checked, how, why, and what came of it

A summary of the second pass. This is the continuation of the work after the article was written. It
refutes some of the article's conclusions - below I say which ones, and on what evidence. All numbers
were obtained on the same held-out set as in the article (16 LANL days, 64
labelled windows, 3.6M windows) unless marked "day 12" (a working day).
The detailed chronicle, run by run, is in DIARY.md under the entries dated 2026-08-31.

### 16.0. The reference point - the article's summer result

One LSTM-24 (4 249 parameters), base world `gen/world.tdc`: held-out
set AUC **0.909**, false alarms before the 16th attack found **188**. Three of the article's
conclusions that the evening refuted or amended:

| article's conclusion | what turned out |
| --- | --- |
| "synthetic data does not produce coincidences - normal windows with the attack signature" | it does: not through an explicit mechanism, but through window sparsity (section 16.1) |
| "a council of strong networks does not transfer to the held-out set" | it does transfer if the networks are trained on DIFFERENT worlds rather than a single one (section 16.2) |
| "0.909 is below everyone who publishes AUC" | 0.938-0.944 before the review, inside the range of the research papers (table in section 15) |

### 16.1. Hypothesis: coincidences can be produced

**What was done.** A world with an explicit coincidence mechanism (`world-coin.tdc`: a machine
where new accounts and failures legitimately occur together) and, as a control, the same worlds
with the mechanism turned down to zero (`make-control.sh`).
**What happened.** The control worlds produced coincidences just as well. So it is not the
mechanism that breeds coincidences but the fact that the world got smaller (1.5M events over the same
machines) and the windows thinned out: in sparse windows the shares "float". This is the same route by which
coincidences arise in reality (there they are two-event windows).
**What was built.** The sparse world `gen/world-sparse.tdc`: 18% "quiet"
machines whose events are spread over 80-260 hours. For the first time the window shape is close to
reality: events 1 / 19 / 57 against 2 / 22 / 49 in LANL, and the coincidences are
tiny (median 4 events against 2 in the real ones; previously 24). An LSTM trained on
it: day 12 AUC 0.99327, zero false alarms before the 6th - the best working-day result
at that point.
**Methodological lesson.** Without the control, the effect would have been credited to the explicit mechanism and
a falsehood would have gone into the article. The control cost one run.

### 16.2. Hypothesis: many worlds, one network per world, a joint decision

**What was done.** Six worlds without attack stages, with coincidence shares of
0.5...5% and different seeds (`make-nostage-worlds.sh`, prefix ns), one
LSTM-24 per world, combined by rank averaging (no trained judge).
Separately, controls to break the contribution down: six seeds of ONE world; one
clean world, one network; six worlds MERGED into a single set for one network.

**Attribution ladder on the held-out set** (false alarms before the N-th attack):

| configuration | 1 | 8 | **16** | 24 | 32 | what it isolates |
| --- | --- | --- | --- | --- | --- | --- |
| base world, one network (article) | 3 | 102 | 188 | 412 | 3 734 | reference point |
| base world, 6 seeds, ranks | 11 | 80 | 117 | 504 | 6 945 | averaging by itself |
| one clean world, one network | 0 | 2 | 30 | 222 | 2 382 | the clean world by itself |
| **six clean worlds, 6 networks, ranks** | **0** | **3** | **7** | **19** | **621** | clean + different worlds |
| six clean worlds, merged, one network | 814 | 6 992 | 26 297 | 59 973 | 98 511 | merging |

Ensemble AUC 0.938 (against 0.909). A repeat run reproduced the curve
0 / 2 / 2 / 3 / 7 / 19 / 621 exactly.
**The formula:** clean world x different worlds x separate networks x ranks. No
single factor gets to seven on its own. Merging the worlds into one set is a
catastrophe (140 times worse than the base): diversity poured into one dataset
turns into contradiction; spread across models, it turns into strength.
**A predictor available before the exam:** the spread of opinions among the networks (mean sigma of scores per window):
0.0002 for networks from one set -> no benefit; 0.004 for six seeds -> x1.6; 0.014
for six worlds -> x27. It can be measured without touching the held-out set.
**The ensemble and "one world per network" turned out to be the main idea.** It is the first add-on
in the whole project to survive the held-out set.

### 16.3. Combining the two gains - and the network's first real mistake

**What was done.** Six sparse worlds (prefix sp), the same ensemble.
**What happened.** AUC **0.944** - the best in the project, with every single network
(0.925...0.952) above any of the ns ones. But the cost curve is worse: 6 / 7 / 7 / 9 / 10 /
61 / 3 870 - **six false alarms before the very first attack**. The third law (AUC and price
diverge), for the third time.
**Diagnosis** (from the saved scores; the first time we looked at the top of the
held-out set): five of the six are **failure storms**: hosts C21454 and
C15244, 390-3 391 events per hour, 90-99% failures, one new user,
hundreds of new triples on C21454. Normal according to the labels, in fact a broken service
or brute force; a find for an analyst, an error for the metric. The sixth is C17693@661:
two failures from two new accounts on the attacked host, between the labelled
hours; it looks like an unlabelled part of the same activity. **All 18 networks
of the three families give the storms the top rank** - the ensemble has nothing to correct.
**The cause:** normal storms (>=100 events, >=90% failures) occur in LANL 3-13 times a
day, 249 of them in the held-out set; in the training worlds, zero. The role "service with a
broken password" existed in the config, but it produced 30-80% failures at ordinary
volume.
**The law:** an ensemble cures disagreement, not a shared delusion. A shared
delusion comes from a shared hole in the worlds, and only a world can close it.
**Verified that this is not an artefact:** there are no ties at the top (each network has
exactly one window with the maximum score, the ensemble's top 100 holds 97-98 distinct
values; the curve is the same under worst-case and best-case tie-breaking).

### 16.4. The micro-loop: reality shows a host, the config gets a line

Three edits to the world in a row, each one or two lines of TDC, each prompted by dissecting
a specific host at the top of the false alarms. Checked on the working days
(`net_py/top_false.py`: the forty top NORMAL windows of day 12 with their features),
LSTM-24, 3 seeds:

| world | what was added | how it was found | d12 AUC | before the 6th |
| --- | --- | --- | --- | --- |
| sparse | a tail of quiet machines | LANL window shape | 0.99327+-0.00104 | 0 |
| with storms (`world-storm.tdc`) | 1.5% of machines: 1-2 of their own users, 90-100% failures, 1-4 hours | top of the HELD-OUT set (tuning) | 0.99379+-0.00082 | 3 |
| relocation v2 (`world-move.tdc`) | 2% of machines: from the hour moveHour onwards, half the events come from another machine's user who goes to HIS OWN servers; 1% - a fresh account | day 12: host C3699 accounted for 22 of the 40 top normal windows | **0.99636+-0.00044** | 0 |
| new hosts 3% (`world-newhost.tdc`) | "new host" role share 0.6% -> 3% | day 12: the first hours of new hosts | **0.99743+-0.00053** | 0 |

What happened to the errors: the day 12 storms fell from ranks 35-1 058 to
1 229-4 050; C3699 left the top forty entirely; on day 12 the eight
labelled windows took ranks 1-8. **Relocation v1** (the arriving user goes to the
owner's destinations) had no effect - the difference from C3699 turned out to lie in the
"new triples" feature (27 of 27 events for the real relocation, 0 for the synthetic one):
a person who has moved to another machine goes to his own servers, which are new to that machine.
One line, and the host was gone. This is exactly what the generator is for: the gap is spotted in
reality, closed in the config, and the network stops making the mistake.

**The final family on the held-out set** (six `world-newhost` worlds, prefix nh):
AUC **0.907** (the worst), curve **1 / 1 / 1 / 1 / 2** / 43 / 2 538 - the best head
in the project and the worst tail. Ranks 1-18: seventeen attacks and C17693@661.
The storms sit at ranks 155+. A world that taught the network that newcomers, storms and new
hosts are normal made it more cautious: strong attacks come out cleaner, weak ones (which look like
newcomers) sink deeper. The spread of opinions in the final family is 0.0042 - seed-level: the networks
are almost unanimous, and the ensemble has nothing to correct.

### 16.5. Adding families together - the answer to "what if there were twenty networks"

| ensemble | networks | AUC | false alarms before 1 / 2 / 4 / 8 / 16 / 24 / 32 |
| --- | --- | --- | --- |
| ns (clean) | 6 | 0.938 | 0 / 2 / 2 / 3 / 7 / 19 / 621 |
| st (storm) | 6 | 0.941 | 3 / 4 / 4 / 5 / 8 / 24 / 389 |
| nh (final) | 6 | 0.907 | 1 / 1 / 1 / 1 / 2 / 43 / 2 538 |
| ns + st | 12 | 0.942 | 0 / 2 / 3 / 4 / 7 / 11 / 357 |
| ns + nh | 12 | 0.924 | 0 / 1 / 1 / 1 / 1 / 4 / 615 |
| **ns + st + nh** | **18** | 0.932 | **0 / 1 / 1 / 1 / 1 / 4 / 316** |
| ns + sp + st + nh | 24 | 0.937 | 0 / 1 / 1 / 1 / 1 / 7 / 326 |

**Eighteen networks from three families: one false alarm before the 16th attack, four before the 24th,
316 before the 32nd.** From 188 (article) down to 1. To find 16 attacks, an analyst went
through 204 windows in the summer; now it is 17.

**Saturation curve** (random subsets of the 24 networks, median over 12
samples, false alarms before 16 / 24 / 32): 1 network - 43 (from 3 to 329) / 293 / 1 397;
2 - 10 / 109 / 763; 4 - 4 / 24 / 636; 6 - 3 / 24 / 606; 8 - 3 (from 1 to 5) /
10 / 440; **12 - 1 / 5 / 367**; 16 - 1 / 7 / 331; 24 - 1 / 7 / 326.
Saturation sets in around 12 networks. On a budget of six networks, a mix of families (2+2+2 -
4 / 36 / 532) is no better than one good family (7 / 19 / 621): family diversity
only works when each family has enough networks (4-6 apiece).
**The answer:** both factors help as they grow - the number of networks up to ~12, and the number of world FAMILIES with
different phenomena up to ~3; a fourth family (sp, which shares its blindness to storms with st)
adds nothing; seeds of one world are no substitute for worlds (117 against 7).

### 16.6. Side facts

- SSM (`DiagSSMBody`): on the storm world 0.993+-0.0005, on the relocation
  worlds 0.982+-0.013...0.016, on the final one 0.952+-0.014 - the same network, the same
  day; the fifth confirmation of the law "world and architecture are one decision".
  The nine architectures were not re-run on the final world; their ranking there
  may differ.
- The ensemble of eighteen: 76 482 parameters; a single network, 4 249.
- The tail: half of the labelled windows sit at ranks between 3 thousand and 2 million
  and, by the hour's features, are indistinguishable from noise (one event, one new
  user, no failures). Any gain there can only come from other features (links
  between hosts), not from networks and not from worlds.

### 16.7. Honesty - what to call what

- **Honest transfer** (obtained BEFORE I first looked at the top of the
  held-out set): ns x6 - AUC 0.938, 7 false alarms before the 16th; sp x6 - AUC
  0.944, 10 false alarms. These are the results that may replace the summer's 0.909 / 188.
- **After the review** (tuning): the "storm" role came out of the top of the
  held-out set; relocation and new hosts were found on day 12, but they are built on the
  storm world; the choice of family combination was made on the held-out set. The result "18
  networks, 1 false alarm before the 16th, AUC 0.932" goes into the article only with this mark,
  next to the honest seven.
- Accesses to the held-out set over the life of the project: at least 23. Each one lowers
  its value; the real test of the 1 is a fresh LANL day we have never
  touched, accessed exactly once. Not done.
- Window C17693@661 (first for every family) counts as a false alarm by the labels; sitting
  next to the labelled hours of the same host, it is most likely the same
  activity without a label. It goes into the article as is, with this caveat.

### 16.8. What this changes in the article

1. Section 9 "Coincidences - why we hit a ceiling": we do not hit a ceiling -
   sparsity produces coincidences (section 16.1), and the control proved it.
2. Section 10, the row "council of strong networks - held-out set worse": true
   for networks from one world; for networks from different worlds it transfers (section 16.2).
   Extend the line "spread of opinions 0.0002" into the series 0.0002 / 0.004 / 0.014.
3. Section 12 and the reference table: 0.909 -> 0.938-0.944 (honest) - inside the
   range of the research papers, above UGEA-LMD, below LMTracker.
4. The main result: 188 -> 7 (honest) -> 1 (after the review) false alarms before the 16th.
5. A new law to add to the previous three: an ensemble cures disagreement, not a shared
   delusion; only a world closes a shared delusion.
6. A new chapter on the micro-loop (section 16.4) - this is the generator's demonstration piece:
   "TDCv2 can imitate any crap - the question is how you write the config":
   three hosts, three lines, three errors gone.

### 16.9. Where things are

- World configs: `gen/world-sparse.tdc` -> `world-storm.tdc` -> `world-move.tdc`
  -> `world-newhost.tdc` (final); the sets of six: `gen/make-{nostage,sparse,storm,newhost}-worlds.sh`.
- Training and exam: `net_py/heldout_ensemble.py <prefix>` (six networks ->
  the held-out set, saves `results/<prefix>-heldout-scores.npy`),
  `net_py/heldout_sameworld.py` (seed control), `net_py/per_world.py`.
- Dissections: `net_py/top_false.py` (top normal windows of days 8/12),
  `net_py/storm_check.py` (storm ranks), `net_py/saturation.py` (saturation
  curve).
- Held-out scores: `results/{ns,sp,st,nh}-heldout-scores.npy`
  (3.6M x 6 each) - any new combination can be computed without retraining.
- Logs: `results/{sparse,storm,newhost}_ensemble.log`,
  `results/ns_ensemble_rerun.log`, `results/{storm,move,move2,newhost}_world.log`,
  `results/saturation.log`.
