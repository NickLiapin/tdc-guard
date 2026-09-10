Russian version / Русская версия: [README.ru.md](README.ru.md)

# tdc-guard

A small neural network trained only on made-up authentication logs produced by the
TDCv2 data constructor, and tested on the real authentication logs of Los
Alamos National Laboratory. The task is lateral movement: logging in with
valid but stolen accounts, machine after machine. This repository holds
everything the article refers to: the world configs, the feature measurer,
the networks, the exam scripts, the lab diary and the fact sheet.

The tool all of this is built around: https://github.com/NickLiapin/tdcv2
(npm package `tdcv2`).

## What you can reproduce here

1. A fully connected network with 1333 weights ("weights" and "parameters"
   mean the same thing below), trained on the base world, and its exam on
   LANL days 8 and 12.
2. A recurrent network with 4249 parameters on the sixteen-day held-out set:
   188 false alarms before the sixteenth attack is found.
3. An ensemble of six networks trained on six different worlds: the same 3.6
   million windows, 7 false alarms before the sixteenth attack.
4. The micro-loop: how taking apart the one machine at the top of the
   false-alarm list turns into two lines of config, and how the error goes
   away after that.

Every number in the article is in the logs under `results/` and in
`FACTS.md`; `DIARY.md` records where each one came from.

## Words you need before reading further

- **Red team** - the people who, by arrangement with LANL, staged the attack.
  Their actions are recorded in `data/redteam.txt`, and only those count as
  "truth": a window is labelled if one of these events falls inside it.
- **Days** - the data set counts time in seconds from its first record; a
  day is 86 400 seconds. Day 8 is seconds 691 200 to 777 600, day 12 is
  1 036 800 to 1 123 200. `slot` in the scripts' output is the hour number,
  counted the same way.
- **Measurer** - the code that computes window features from an authentication
  log. It is the same code for synthetic data and for the real network:
  `judge/windows.mjs`.
- **Features** - eighteen numbers per window, in the order of the CSV
  header: `events`, `users`, `dsts` - the number of events, distinct accounts
  and distinct destinations; `newUsers`, `newDsts` - how many of those
  accounts and destinations the machine had never seen before;
  `newUserRatio`, `newDstRatio`, `newEdgeRatio` - the same, as fractions of
  events; `failRatio` - the fraction of failed logins; `rhythm` - how evenly
  the events are spread across the hour; `historySize` - the size of the
  machine's baseline (the `history` column in `top_false.py` is this number);
  `knownUsers` - accounts the machine already knew; `userSrcNewRatio` - the
  fraction of events whose account is on this machine for the first time;
  `tripleNewCount`, `tripleNewRatio` - events whose three edges
  (account-machine, machine-destination, account-destination) are all new,
  as a count and as a fraction; `minUserScope` - the narrowest account in the
  window: how many machines it was known on; `movedUserCount` - events by
  accounts known to the network but new to this machine; `freshUserCount` -
  events by accounts never seen anywhere. All of them are computed in
  `judge/windows.mjs`.
- **Seed** - the number all of the generator's randomness is derived from:
  one seed, one world, byte for byte. A training seed is the same thing for
  a network's initial state; "three seeds" means three training runs from
  different starting points, to see the spread.
- **AUC** - area under the ROC curve: the probability that a random labelled
  window scores higher than a random ordinary one. 1.0 is a perfect
  ordering, 0.5 is a coin flip.
- **World config and roles** - a world is described by a single `.tdc` file
  for the TDCv2 generator. The machines in it are assigned roles
  (workstation, server, new host, compromised host, service with a broken
  password, and others); a role's share is set by a `percent` line, and
  `isCoin`, `isStorm`, `isMove` are the names of such roles in the config.
- **Recurrent network and SSM** - two architectures that read one machine's
  hours in order: an LSTM with 24 hidden units and 4249 weights (the
  article's main network, `LSTM-24` in the logs) and a state-space model,
  SSM, from `net_py/exotic.py`. "Fully connected" is the plain network that
  looks at a single window without its neighbours.
- **Council, judge, rank averaging** - a council is several networks whose
  outputs are combined; rank averaging is the simplest way to do it (each
  network ranks all the windows, and a window gets its mean rank); a judge is
  a small model trained to weigh the networks' votes. Judges never beat rank
  averaging in this project. **Spread of opinions** - the mean standard
  deviation of the networks' scores across windows; it predicts whether a
  council will help (0.0002 means the networks agree and there is nothing to
  average).
- **Cost curve** - false alarms as a function of attacks found; "false alarms
  before the N-th" is one point on it. **Attribution ladder** - the table in
  step 4 that isolates what each factor (a clean world, several worlds,
  separate networks) contributes. **Seed control** - six networks on one
  world with different training seeds, to show that averaging by itself buys
  little.
- **Baseline scissors, temporal wrapper, diluted windows** - names from the
  "what did not work" sections: the baseline either gets poisoned or drifts;
  accumulating suspicion across neighbouring hours with a hand-written rule
  (the temporal wrapper) made things worse; training on windows where a
  single foreign event hides among dozens of normal ones (diluted windows)
  taught the network the wrong lesson. **Relocation** is the `isMove` role: a
  person moves to another machine and works there all day.
- **Window** - one machine over one hour: everything it did in that hour.
  Every table is in units of windows. A labelled window is one that received
  at least one red-team event.
- **Baseline** - a machine's accumulated history: which accounts and which
  destinations have already been seen on it. Novelty is computed relative to
  the baseline. The baseline gets "poisoned" when the intrusion it is
  observing becomes part of it, and "drifts" when it is frozen for too long.
- **Working days** - LANL days 8 and 12. Every knob was turned on them.
  **Held-out set** - sixteen other days (1, 2, 5, 6, 7, 9, 13, 14, 15, 20,
  21, 22, 26, 27, 28, 29), 3.6 million windows, 64 labelled; touched only for
  the final measurements.
- **False alarms before the N-th** - the project's main measure: how many
  false alarms sit above the N-th real attack in the list sorted by the
  network's score. The working days have 12-15 attacks, so there it is
  "before the 6th"; the held-out set has 64, so there it is "before the
  16th". AUC is printed as well, but it lies on rare events; the article has a
  whole section on that.
- **Coincidence** - a normal window that happens to carry the full attack
  signature: many new accounts and many failures at once. In the scripts
  these are windows with newUserRatio >= 0.9 and failRatio >= 0.15 and the
  label "normal". "Coincidence share 0.5%-5%" in the six-world sets is the
  parameter of the isCoin role: a machine where all of this legitimately
  happens at once.
- **Attack stages** - in the rich world the attack goes through four stages,
  from a quiet foothold to reaching the servers. The quiet stages taught the
  network to fire on any quiet window, which is why the "no-stage world"
  (nostage) and every world after it have no stages.
- **World family** - one config replicated with six seeds and coincidence
  shares of 0.5, 1, 1.5, 2.5, 3.5 and 5 percent. Families are named after
  their file prefix: `ns` - no stages, `sp` - sparse, `st` - with storms,
  `nh` - final, with new hosts, `coin` and `ctrl` - the world with an explicit
  coincidence mechanism and its control. A family's files are
  `results/ns-0-windows.csv` ... `ns-5-windows.csv`. "Clean world" in the
  diary and the article means the world without stages, family `ns`.
- **What the scripts print.** The measurer: "read N" - log lines (fewer
  than 400 thousand in the base world, because some of the events fall past
  the end of the observation period), "windows M", "labelled K". Network
  evaluation: AUC, then "false alarms before 16/64" - false alarms before the
  16th attack out of 64, "before all" - before the last one, "worst rank" -
  the rank of the last attack in the list. In `top_false.py`: `slot` - the
  hour number from the start of the log, `history` - baseline size,
  `tripleN` - events whose three edges are all new, `movedUs` and `freshUs` -
  accounts known to the network but new to this machine, and accounts never
  seen anywhere.

The bilingual glossary is in `GLOSSARY.md`.

## What you will need

- Node.js 20 or newer and the generator: `npm install -g tdcv2`. To check:
  `tdcv2 --version` should print `tdcv2 0.3.0` - all the numbers were
  obtained on this version. Worlds are deterministic by seed: same config,
  same seed, same file byte for byte, and every step below comes with numbers
  to check against.
- Python 3.10 or newer: `pip install -r requirements.txt`. That gets you
  numpy, torch and xgboost (the last only for `net_py/boosting.py`; everything
  else works without it). No GPU needed; everything trains on a CPU in
  seconds or minutes.
- Disk space and patience for the LANL data. The authentication log
  `auth.txt.gz` is 7.2 GB, but you do not have to keep the whole thing: the
  scripts in `exam/` stream it and keep only the fields they need. The slices
  come out at 0.4-1.3 GB; the full held-out slice takes several hours to
  download. Synthetic data is not free either: the base sets from step 2 take
  about 700 MB in `data/`.
- The short path: the two window tables for the working days
  (`results/day8-shared.csv` and `results/day12-frozen-windows.csv`, 13 MB
  each) are right here in the repository. With them, step 2, step 3 except
  for its last command, and step 5 can be reproduced in about 45 minutes with
  no LANL data at all; steps 0 and 1 are needed only for the held-out set,
  `heldout_lstm.py` and step 4.
- Memory: the measurer over 3.6 million windows, and the generator for worlds
  with 4-8 million events, need node with a bigger heap. The scripts set
  `NODE_OPTIONS=--max-old-space-size=8192` themselves; for `exam/sealed.mjs`,
  12288 is better.

## Layout

### gen - worlds

| file | what it is |
|---|---|
| `world.tdc` | the base world, 135 lines, 400 thousand events. Everything started here; the article takes it apart in full |
| `world-rich.tdc` | the rich world: 8 million events, the attack as a staged process. It turned out worse than the base world on the held-out set; kept as a negative result |
| `world-nostage.tdc` | the same rich world without attack stages. Six of these make up the ensemble with 7 false alarms |
| `world-sparse.tdc` | the sparse world: 18% quiet machines whose events are spread over 80-260 hours. Coincidences arise in it on their own |
| `world-storm.tdc` | plus the "storm" role: a service with a broken password, hundreds of failures per hour |
| `world-move.tdc` | plus a person relocating to another machine, and a fresh account |
| `world-newhost.tdc` | the final world: the same plus 3% new hosts, 210 lines |
| `world-coin.tdc` | a world with an explicit coincidence mechanism. It made no difference, and that matters |
| `make-base.sh` | the base sets: training and exam synthetic worlds, rich, no-stage, sparse |
| `make-control.sh` | the control for world-coin: the same worlds with the coincidence mechanism set to zero |
| `make-worlds.sh`, `make-nostage-worlds.sh`, `make-sparse-worlds.sh`, `make-storm-worlds.sh`, `make-newhost-worlds.sh` | sets of six worlds from one config with different seeds and coincidence shares from 0.5% to 5% - one script per family |
| `run-storm.sh`, `run-move.sh`, `run-newhost.sh` | one turn of the micro-loop: world, windows, evaluation on the working days, the top forty false alarms |
| `measure-synth.mjs` | runs the same measurer over a synthetic log as over the real one |

The configs with Russian comments, as quoted in the Russian article, are in
`ru/gen/`; the logic is the same byte for byte.

### judge - the measurer

| file | what it is |
|---|---|
| `windows.mjs` | the only place where the features of a "machine per hour" window are computed. It measures both the synthetic data and LANL, so if it is wrong, it is wrong the same way on both sides |
| `rows.mjs` | the window table loader. Fails unless every feature is present. Written after two runs with an AUC of exactly 0.50000 |
| `measure.mjs` | the first version of the measurer, before the shared module. Kept for the record |

### exam - real data

| file | what it is |
|---|---|
| `slice.sh` | a streaming slice of auth.txt.gz for days 0-9 into `data/auth_d0_d9.csv.gz` |
| `slice12.sh` | the same for days 0-12 into `data/auth_d0_d12.csv.gz` |
| `slice-sealed.sh` | the same through the end of day 29 into `data/auth_sealed_full.csv.gz`: the held-out set |
| `day8-shared.mjs` | day 8 windows with the shared measurer, history = days 0-7 |
| `day12-frozen.mjs` | day 12 windows with the baseline frozen at days 0-7. This is "day 12" in every table |
| `day12.mjs` | the same day with the baseline grown through day 11: exactly the case where the baseline is poisoned by what it observes. Needed only for the baseline-scissors section |
| `sealed.mjs` | the held-out set: sixteen days, 3.6 million windows. Writes `results/sealed-windows.csv` |
| `day8.mjs` | the very first run over day 8, before the shared measurer |
| `real.mjs`, `score.mjs`, `baselines.mjs`, `wrapper.mjs` | the exam of the first, JavaScript version of the network: the network against counters and a threshold rule, and the temporal wrapper |

### net - the first version of the network

The dependency-free JavaScript network the project started with: `train.mjs`
trains it, `ablate.mjs` switches features off one at a time, `model*.json`
are its weights, `train_encode.mjs` is the feature encoding shared by all the
exams (the counters are log-transformed). The network from the article lives
in `net_py`; the weights here are used only by `exam/real.mjs`, `score.mjs`,
`baselines.mjs` and `wrapper.mjs`.

### net_py - the networks from the article

| file | what it is |
|---|---|
| `data.py` | reads windows and encodes features, without pandas: the held-out set is 3.6 million rows |
| `model.py` | the fully connected network, layer widths given as a list |
| `evaluate.py` | AUC via ranks and the cost curve in a single pass |
| `run.py` | trains on synthetic data, checks on days 8 and 12; with `--sealed`, on the held-out set as well |
| `sweep_big.py` | a sweep over 31 architectures, three seeds each |
| `boosting.py` | gradient boosting on the same features |
| `recurrent.py` | a recurrent network over the sequence of one machine's windows |
| `exotic.py` | nine sequence architectures, from convolutions to external memory |
| `council.py` | averaging probabilities, averaging ranks, a trainable judge |
| `eval_world.py` | one world, two architectures (recurrent and SSM), three seeds, evaluation on the working days |
| `heldout_lstm.py` | one recurrent network trained on a given world, against the held-out set |
| `per_world.py` | a network per world, one shared decision |
| `heldout_ensemble.py` | six networks on six worlds, rank averaging, the held-out set. The main result |
| `heldout_sameworld.py` | control: six seeds of one world |
| `top_false.py` | the top forty false alarms with their features - the micro-loop tool |
| `storm_check.py` | where a network ranks the normal storms of day 12 |
| `saturation.py` | the saturation curve: quality versus the number of networks |
| `judge_lab.py`, `weak_council.py`, `weak_verify.py`, `symbiosis.py`, `final*.py` | judges over networks, weak learners, symbiosis: the experiments from the "what did not work" section |
| `factorial.py`, `arch_on_worlds.py`, `rich_test.py`, `rich_sealed.py`, `boosting_sealed.py`, `ambig_test.py`, `sweep.py` | the rich world, architectures on different worlds, diluted windows, the early sweep. Each is described in DIARY.md |

### Documents

- `DIARY.md` - the diary: every run in order, mistakes and dead ends
  included. Russian original: `DIARY.ru.md`.
- `FACTS.md` - the fact sheet, marking what was obtained honestly and what
  came after the held-out set had been taken apart. Russian: `FACTS.ru.md`.
- `METHODS.md` - how the measurer, the features and the exam are built.
  Russian: `METHODS.ru.md`.
- `ARCHITECTURES.md` - the full tables across all architectures. Russian:
  `ARCHITECTURES.ru.md`.
- `GLOSSARY.md` - the terms in both languages.
- `results/*.log` - the output of the runs the article and the diary refer
  to. Besides the ones named in the table of numbers below, there are:
  `base_gen.log` (step 2), `coin_gen.log` and `ctrl_gen.log` (the world with a
  coincidence mechanism and its control), `nostage.log` (the rich world with
  and without stages), `factorial.log` and `arch_worlds.log` (architectures
  on different worlds), `per_world_coin.log` (the first council over worlds),
  `heldout_sparse.log` (a single sparse-world network on the held-out set),
  `storm_check.log`, `sparse_world.log` (the sparse world on the working
  days, step 3), `ns_gen.log`, `rich_gen.log` and `sparse_gen.log` (what the
  measurer printed when those worlds were first built). The diary entry for
  the same day describes each of them. The same logs as printed by the first
  version of the scripts, with Russian labels, are in `results/ru/`.

## How to reproduce, step by step

All commands are run from the repository root.

### Step 0. The LANL data

The data set is open, no registration required; the description and files
are at https://csr.lanl.gov/data/cyber1/. The scripts download from the
mirror `https://lanl.ma.ic.ac.uk/data/cyber1/`, which serves the files
directly and supports resumed downloads; if it is down, replace the address
in them with `https://csr.lanl.gov/data/cyber1/auth.txt.gz`. Two files are
needed.

```bash
mkdir -p data results
curl -o data/redteam.txt.gz https://lanl.ma.ic.ac.uk/data/cyber1/redteam.txt.gz
gunzip -k data/redteam.txt.gz
```

The authentication log is sliced as a stream, without ever saving the
whole file:

```bash
./exam/slice.sh          # days 0-9,  ~0.4 GB, about an hour
./exam/slice12.sh        # days 0-12, ~0.5 GB, an hour and a half
./exam/slice-sealed.sh   # days 0-29, ~1.3 GB, several hours
```

If you already have auth.txt.gz on disk, replace `curl ... | gunzip` in the
scripts with `gunzip -c path/auth.txt.gz`.

### Step 1. Windows of the real days

```bash
node --max-old-space-size=8192 exam/day8-shared.mjs     # results/day8-shared.csv
node --max-old-space-size=8192 exam/day12-frozen.mjs    # results/day12-frozen-windows.csv
node --max-old-space-size=12288 exam/sealed.mjs         # results/sealed-windows.csv
```

What you should get: day 8 - 231 787 windows, 15 labelled; day 12 -
223 987 windows, 12 labelled; the held-out set - 3 600 398 windows, 64
labelled. The scripts print these numbers at the end.

The first two files are the working days; you can turn any knob you like on
them. The third is the held-out set. It stays honest only until the first
look at it, and the diary keeps count of how many times it was consulted
during the project.

### Step 2. Synthetic data

```bash
./gen/make-base.sh | tee results/base_gen.log
```

Six window tables appear in `results/`. This takes about fifteen minutes:
half a minute for each base world, four to five for the rich ones, four for
no-stage, two for sparse. While a big world is being generated the generator
is silent and the file appears only at the end - it has not hung. After each
world the measurer prints a "read, windows, labelled" line; this is what you
should get:

| set | purpose | read | windows | labelled |
|---|---|---|---|---|
| synth-train | training for the fully connected network and the boosting | 363 337 | 3 835 | 790 |
| synth-exam | the same world, another seed: the exam on synthetic data | 364 225 | 3 798 | 749 |
| rich-train | the rich world, training for the judge experiments (`per_world.py`, `factorial.py`) | 7 246 138 | 25 365 | 3 497 |
| rich-exam | the rich world, another seed: the judge trains on it | 7 294 018 | 25 501 | 3 448 |
| nostage | the rich world without stages: the comparison in `eval_world.py` | 1 359 554 | 25 187 | 3 754 |
| sparse | the sparse world: the micro-loop starts here | 3 483 968 | 26 062 | 4 068 |

The same output is in `results/base_gen.log` in the repository - check
against it. If you do not need a set, comment out its line in `make-base.sh`.

### Step 3. Networks on one world

```bash
python3 net_py/run.py --hidden 12,12,12,12,12,12,12,12
python3 net_py/sweep_big.py
python3 net_py/boosting.py
python3 net_py/eval_world.py results/sparse-windows.csv "sparse"
python3 net_py/eval_world.py results/nostage-windows.csv "no stages"
python3 net_py/heldout_lstm.py results/synth-train-windows.csv "base"   # needs the held-out set
```

- `run.py`: eight layers of twelve is the 1333-weight network from the
  article; the script says so itself: `18-12-...-12-1 - 1333 weights`. Then
  one line per set: AUC, "false alarms before N/K" (before a quarter of the K
  labelled windows have been found), "before M" (before half of them),
  "before all" and "worst rank". On synthetic data the AUC is about
  0.9999, on day 8 about 0.99999, on day 12 with seed 7 it is 0.97640 with 6
  false alarms before the 6th out of 12. The spread across seeds for this
  network is 0.975 +- 0.003. The `--sealed` flag adds a line for the held-out
  set if it exists. About ten seconds.
- `sweep_big.py`: 31 architectures, three seeds each; the table matches
  `results/sweep_big.log` line for line. Three minutes on a CPU; it leaves
  behind a 57 MB `results/_sweep_store.npy`, which can be deleted.
- `boosting.py`: six boosting rows, with the names and numbers from
  `ARCHITECTURES.md`, section 5. The reference network row is not computed
  by default: on macOS, torch and xgboost in the same process crash Python
  with code 139. That row is in the output of `run.py`; if you want everything
  in one table, use the `--with-net` flag.
- `eval_world.py`: one world, two architectures (recurrent and SSM), three
  seeds, days 8 and 12. The second argument is only a caption for the
  output. Columns: day 8 AUC, day 12 AUC, false alarms before the 1st and
  before the 6th attack of day 12. For the sparse world you should get:
  recurrent 1.00000 / 0.99327+-0.00104 / 0 / 0, SSM 0.99998 /
  0.94309+-0.00533 / 0 / 9 (`results/sparse_world.log`). For the no-stage
  world: recurrent 0.99243+-0.00016 / 0, SSM 0.95273+-0.02080 / 445
  (`results/nostage.log`, where the same world is called "rich WITHOUT
  stages" and compared against the staged one). Two minutes per world.
- `heldout_lstm.py`: one recurrent network on the chosen world, against the
  held-out set. For the base world that is the 188 false alarms before the
  16th. Without `results/sealed-windows.csv` the script stops and says what
  is missing.

### Step 4. Six worlds, six networks

```bash
./gen/make-nostage-worlds.sh && python3 net_py/heldout_ensemble.py ns   # 7 false alarms before the 16th
python3 net_py/heldout_sameworld.py                                    # control: six seeds of one world
./gen/make-sparse-worlds.sh  && python3 net_py/heldout_ensemble.py sp   # sparse
./gen/make-storm-worlds.sh   && python3 net_py/heldout_ensemble.py st   # with storms
./gen/make-newhost-worlds.sh && python3 net_py/heldout_ensemble.py nh   # final
python3 net_py/saturation.py                                           # the saturation curve over all four families
```

The letters after `heldout_ensemble.py` are the family prefix from the word
list above: the script reads `results/<prefix>-0..5-windows.csv`. Everything
in this step needs `results/sealed-windows.csv`; without it the scripts stop
with a hint before generating anything (both the `make-*-worlds.sh` scripts
and the Python scripts check; set `FORCE=1` to build the worlds anyway). A
set of six worlds takes ten to twenty minutes to generate, depending on the
family; training six networks and running 3.6 million windows through them
takes about ten more. The `make-*-worlds.sh` scripts make six copies of the
config in a temporary directory, substituting the coincidence share into the
`isCoin` line, and check that exactly one such line was found. The networks'
scores are saved to `results/<family>-heldout-scores.npy`, so any new
combination of families can be computed without retraining;
`saturation.py` expects all four files.

What you should get (false alarms before the 1st / 8th / 16th / 24th /
32nd): clean worlds 0 / 3 / 7 / 19 / 621, the seed control 11 / 80 / 117 /
504 / 6945, sparse 6 / 9 / 10 / 61 / 3870, with storms 3 / 5 / 8 / 24 / 389,
final 1 / 1 / 2 / 43 / 2538. The logs containing these lines are in
`results/`.

### Step 5. The micro-loop

```bash
./gen/run-storm.sh | tee results/storm_world.log            # the storm world: windows, the events-per-window shape line, evaluation on days 8 and 12
python3 net_py/top_false.py results/storm-windows.csv | tee results/top_false_storm.log   # the forty top false alarms of day 8 and day 12 with features
python3 net_py/storm_check.py results/sparse-windows.csv results/storm-windows.csv | tee results/storm_check.log   # where the storms of day 12 went
./gen/run-move.sh | tee results/move2_world.log             # plus relocation; prints the forty top ones itself at the end
./gen/run-newhost.sh | tee results/newhost_world.log        # plus new hosts; the same
```

Each `run-*.sh` takes about four minutes; they write `results/storm-windows.csv`,
`move-windows.csv`, `newhost-windows.csv`. For the storm world you should get
0.99379+-0.00082 on day 12, for the relocation 0.99636+-0.00044, for new
hosts 0.99743+-0.00053; the full output is in `results/storm_world.log`,
`move2_world.log`, `newhost_world.log`. The log `move_world.log` is the first
version of the relocation, which did not work (0.99292); `run-move.sh` has
the second version built in. `storm_check.py` prints the ranks of the
thirteen day-12 storms under the networks of two worlds; the reference is
`results/storm_check.log`. `top_false.py` also saves the scores to
`results/<world>-day8-shared-scores.npy` and
`...-day12-frozen-windows-scores.npy`; they can be deleted. Its columns are
the features from the word list, abbreviated: `newUs` = newUsers, `newDst` =
newDsts, `nuRatio` = newUserRatio, `failR` = failRatio, `history` =
historySize, `tripleN` = tripleNewCount, `movedUs` = movedUserCount,
`freshUs` = freshUserCount.

The point of the loop: look at the top forty false alarms, find the machine
sitting at the top, work out which phenomenon the world is missing, add a
role to the config, check on the working days. Do not touch the held-out set
while doing this.

## Where to find the numbers from the article

| number | where |
|---|---|
| 188 false alarms before the 16th, one recurrent network | `FACTS.md`, section 16.2, and `DIARY.md`, the entry "MODEL FAMILIES: boosting, recurrent networks, exotica" (the price of the first 16 hits is 136 / 188 / 499 across three seeds); the same line is given for comparison in `results/heldout_ns0.log` |
| ranks of the day-12 storms before and after the "storm" role | `results/storm_check.log` |
| 7 false alarms before the 16th, six clean worlds | `results/heldout_ensemble.log`, repeated in `results/ns_ensemble_rerun.log` |
| 117, six seeds of one world | `results/heldout_sameworld.log` |
| 26 297, six worlds merged into one set | `results/heldout_nsmerged.log` |
| sparse, storms, final on the held-out set | `results/sparse_ensemble.log`, `storm_ensemble.log`, `newhost_ensemble.log` |
| the saturation curve | `results/saturation.log` |
| the table of 31 architectures | `results/sweep_big.log`, `ARCHITECTURES.md` |
| nine exotic architectures | `results/exotic.log` |
| the micro-loop, day by day | `results/storm_world.log`, `move_world.log`, `move2_world.log`, `newhost_world.log`, `top_false_storm.log` |
| the attribution ladder and everything else | `FACTS.md`, section 16 |

## On honesty

The held-out set in this project was opened more than once: the diary keeps
a running count (the "Held-out set access count" lines), and `FACTS.md`,
section 16.7, adds it up: no fewer than twenty-three times. The numbers
obtained before I first looked at the top of its false alarms are marked
"before the review" in `FACTS.md`; everything after that is "after the
review". If you repeat this, keep your own held-out set closed until the very
last run: it is the one rule here that really saved the project.

## Author and license

Nick Liapin. MIT, see LICENSE.
