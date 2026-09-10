Russian version: [ARCHITECTURES.ru.md](ARCHITECTURES.ru.md)

<!-- The architectures tested in the tdc-guard project, with the measured numbers.
The document is descriptive: it records what was tested and what the results were. -->

# The list of architectures tested in tdc-guard

**Task:** binary classification of a "source x hour" window (lateral movement
in authentication logs). Training on TDCv2 synthetic data only, evaluation on
real LANL logs.

**The input differs between the fully connected and the sequence models:**
- fully connected - a vector of 18 aggregated window features;
- sequence models - a sequence of up to 24 windows of a single node, with a
  prediction at every step.

**Evaluation sets:**
| name | windows | labelled | property |
| --- | --- | --- | --- |
| day 8 | 231 787 | 15 | easy, saturated by almost any model |
| day 12 | 223 987 | 12 | hard, this is where the models differ |
| held-out | 3 600 398 | 64 | held out, not used during tuning |

All runs use 3 seeds; the mean +- standard deviation is reported.

---

## 1. Fully connected networks: 31 configurations, 93 trained networks, 170 seconds

Why: the basic family for tabular data; I checked how the result depends on
capacity and on shape (width versus depth).

| architecture | weights | day 8 | day 12 |
| --- | --- | --- | --- |
| flat [4] | 81 | 0.99868+-0.00184 | 0.94208+-0.00946 |
| flat [8] | 161 | 0.99998+-0.00001 | 0.94151+-0.00945 |
| flat [16] | 321 | 0.99997+-0.00001 | 0.94619+-0.01355 |
| flat [32] | 641 | 0.99997+-0.00001 | 0.95461+-0.01376 |
| flat [64] | 1281 | 0.99997+-0.00001 | 0.95296+-0.00952 |
| flat [128] | 2561 | 0.99996+-0.00002 | 0.96274+-0.00202 |
| flat [256] | 5121 | 0.99997+-0.00000 | 0.95646+-0.00693 |
| 2 layers [16,8] | 449 | 0.99995+-0.00004 | 0.95278+-0.01589 |
| 2 layers [24,12] | 769 | 0.99997+-0.00002 | 0.94112+-0.00436 |
| 2 layers [32,16] | 1153 | 0.99996+-0.00001 | 0.95968+-0.01217 |
| 2 layers [48,24] | 2113 | 0.99997+-0.00001 | 0.94646+-0.01082 |
| 2 layers [64,32] | 3329 | 0.99996+-0.00002 | 0.96147+-0.00836 |
| 2 layers [128,64] | 10753 | 0.99995+-0.00002 | 0.96318+-0.01032 |
| 3 layers [16,16,16] | 865 | 0.99991+-0.00004 | 0.96520+-0.00442 |
| 3 layers [24,24,24] | 1681 | 0.99995+-0.00002 | 0.95284+-0.01278 |
| 3 layers [32,32,32] | 2753 | 0.99997+-0.00001 | 0.95870+-0.01089 |
| 3 layers [64,32,16] | 3841 | 0.99996+-0.00001 | 0.95620+-0.01233 |
| deep [12]x4 | 709 | 0.99996+-0.00003 | 0.95619+-0.00626 |
| deep [12]x6 | 1021 | 0.99994+-0.00005 | 0.94210+-0.01622 |
| **deep [12]x8** | **1333** | 0.99997+-0.00002 | **0.97518+-0.00343** |
| deep [12]x10 | 1645 | 0.99995+-0.00003 | 0.96627+-0.00497 |
| deep [12]x12 | 1957 | 0.99940+-0.00046 | 0.94923+-0.01033 |
| deep [8]x8 | 665 | 0.99880+-0.00113 | 0.94800+-0.01881 |
| deep [16]x8 | 2225 | 0.99993+-0.00005 | 0.96421+-0.01450 |
| deep [24]x8 | 4681 | 0.99978+-0.00023 | 0.96148+-0.01067 |
| deep [20]x6 | 2501 | 0.99994+-0.00003 | 0.96727+-0.00978 |
| deep [32]x6 | 5921 | 0.99993+-0.00007 | 0.97430+-0.01526 |
| bottleneck [32,8,32] | 1193 | 0.99998+-0.00000 | 0.95741+-0.01204 |
| bottleneck [64,8,64] | 2377 | 0.99997+-0.00001 | 0.96914+-0.00867 |
| pyramid [100,50,25] | 8251 | 0.99997+-0.00003 | 0.96366+-0.01136 |
| pyramid [64,48,32,16] | 6449 | 0.99994+-0.00004 | 0.97076+-0.00939 |

**Findings.**
- The capacity floor: [4] (81 weights) falls short even on the easy day; [8]
  (161 weights) already gives 0.99998.
- The easy day saturates: everything from 161 to 10 753 weights lands in the
  0.99996-0.99998 range with a spread of +-0.00001.
- On the hard day depth pays off more than width: [12]x8 (1333) gives
  0.97518, [128,64] (10 753) gives 0.96318.
- Past 8 layers without residual connections the results degrade: [12]x12
  drops to 0.94923 and hurts even the easy day (0.99940).

**Best:** [12]x8, 1333 weights. On the held-out set: AUC 0.862+-0.005, and the
first 16 hits cost 237-300 false alarms.

---

## 2. Recurrent networks over a node's sequence of windows

Why: every node has an hour-by-hour history; I checked whether trainable
temporal memory buys anything.

| architecture | parameters | day 8 | day 12 |
| --- | --- | --- | --- |
| LSTM hidden=12 | 1549 | 0.99989+-0.00011 | 0.98899+-0.00034 |
| **LSTM hidden=24** | **4249** | 0.99998+-0.00003 | **0.98999+-0.00042** |
| LSTM hidden=48 | 13105 | 0.99999+-0.00001 | 0.98996+-0.00074 |
| GRU hidden=12 | 1165 | 0.99942+-0.00056 | 0.98657+-0.00194 |
| GRU hidden=24 | 3193 | 0.99991+-0.00010 | 0.98774+-0.00131 |
| GRU hidden=48 | 9841 | 1.00000+-0.00000 | 0.98946+-0.00035 |

**Findings.** At comparable size (1549 against 1333 for the fully connected
network) the LSTM gains +1.4 points on the hard day with a tenth of the spread.
Growing capacity beyond hidden=24 adds nothing.

**On the held-out set (LSTM-24, three seeds):** AUC 0.922 / 0.915 / 0.890 = **0.909+-0.014**;
the first 16 hits cost **136 / 188 / 499** false alarms.

This is the only change in the whole project that improved the result on the
working day and on the held-out set at the same time.

---

## 3. Other sequence architectures

Why: to check whether more elaborate handling of the history buys anything.

| architecture | parameters | day 8 | day 12 |
| --- | --- | --- | --- |
| **LSTM-24** (for comparison) | 4249 | 0.99998 | **0.98999+-0.00042** |
| LSTM-24 in two layers | 9049 | 0.99976+-0.00011 | 0.98904+-0.00030 |
| diagonal SSM (S4-lite) | 2305 | 0.99999+-0.00000 | 0.98844+-0.00165 |
| bidirectional LSTM-16 | 4641 | 0.99999+-0.00001 | 0.98555+-0.00144 |
| external memory (simplified NTM) | 2418 | 0.99936+-0.00013 | 0.98509+-0.00121 |
| TCN (dilated convolutions) | 4849 | 1.00000+-0.00000 | 0.98257+-0.00012 |
| LMU (Legendre polynomials) | 723 | 0.99846+-0.00098 | 0.97219+-0.01137 |
| echo state network (reservoir) | 65 trainable | 0.99410+-0.00001 | 0.96859+-0.00159 |
| transformer, self-attention | 10225 | 0.99990+-0.00014 | 0.93700+-0.01062 |

**How the less familiar ones are built:**
- **diagonal SSM** - a linear recurrence with a trainable decay on each state
  channel, a simplified variant of S4;
- **external memory** - a GRU-cell controller plus 8 memory cells of width 8;
  content-based addressing, and the network decides for itself what to write
  and what to read;
- **LMU** - memory is encoded in an orthogonal basis of Legendre polynomials
  (the matrices A and B are fixed; only the projections are trained);
- **echo state network** - the 64x64 reservoir is random and frozen (5248
  weights are never trained); only the linear readout, 65 parameters, is
  trained;
- **TCN** - causal convolutions with dilations 1, 2, 4; coverage without
  recurrence.

**Findings.**
- None of them beat the plain LSTM-24.
- The transformer is the worst of the lot and the largest. The sequences are
  short (24 steps), and there are few training sequences.
- The diagonal SSM comes closest in quality at half the size (2305 against
  4249).
- The LMU, with 723 parameters, gives 0.97219 - higher than the fully
  connected network with 1333.
- The echo state network, with 65 trainable parameters, gives an AUC of 0.96859.

---

## 4. The cost curve on real day 12 (not AUC)

How many false alarms have to be looked through before N real windows are
found. The ordering here does not match the ordering by AUC.

| architecture | before the 1st | before the 3rd | before the 6th | before the 9th | AUC |
| --- | --- | --- | --- | --- | --- |
| **LSTM-24** | **1** | **5** | **7** | **30** | 0.98999 |
| diagonal SSM | 14 | 17 | 26 | 80 | 0.98844 |
| external memory | 8 | 250 | 1 795 | 2 715 | 0.98509 |
| LMU | 63 | 361 | 863 | 2 319 | 0.97219 |
| echo state network | 3 406 | 4 244 | 4 327 | 4 361 | 0.96859 |

The echo state network, with an AUC of 0.969, needs 3406 false alarms before
the first window is found, against one for the LSTM.

---

## 5. Gradient boosting (XGBoost)

Why: the standard choice for tabular data.

| configuration | day 8 | day 12 |
| --- | --- | --- |
| depth 3, 200 trees | 0.99954 | 0.95211 |
| depth 6, 300 trees | 0.99915 | 0.95145 |
| depth 10, 300 trees | 0.99923 | 0.98950 |
| depth 2, 800 trees | 0.99973 | 0.92645 |
| depth 10 + subsample 0.8 | 0.99963+-0.00004 | 0.98885+-0.00043 |
| depth 14 + subsample 0.8 | 0.99963+-0.00005 | 0.98886+-0.00043 |

**Findings.** Without subsampling it is deterministic (the spread is exactly
zero). On the hard day it beats the fully connected network (0.98885 against
0.97518).

**On the held-out set:** AUC 0.898 / 0.944 / 0.914 = **0.918+-0.019** - higher
than anything else. But the first 16 hits cost **23 781** false alarms, against
188 for the LSTM and 245 for the fully connected network. The high AUC comes
from the tail of the list.

---

## 6. Ensembles and meta-models

Why: to check whether combining several models yields a gain.

| method | day 12 |
| --- | --- |
| best single network | 0.98183 |
| council of 3, rank averaging | 0.98053 |
| council of 5, rank averaging | 0.97703 |
| council of 8, rank averaging | 0.97361 |
| judge (meta-model) over a council of 3 | 0.95552 |
| judge over a council of 8 | 0.96546 |
| judge over 12 weak learners, 16 epochs | 0.97347+-0.01876 |
| judge over a mixed pool (6 weak + 6 strong) | 0.96993+-0.02752 |
| best single member of the same mixed pool | 0.97931+-0.00879 |

**Findings.**
- Rank averaging beats probability averaging everywhere.
- More members, worse result.
- The meta-model loses to plain averaging in every line-up.
- The mean spread of predictions across the strong networks is **0.0002**:
  they make their mistakes in the same places.
- Weak learners (a subsample of features and windows, few epochs) give the
  judge some spread of opinions to work with, and for the first time it
  overtakes averaging (0.97347 against 0.95882), but the absolute level stays
  below a single network.

**On the held-out set:** council of 3 - AUC 0.847 at a price of 591 false
alarms. Worse than a single network.

---

## 7. Held-out summary

| model | AUC | price of the first 16 hits |
| --- | --- | --- |
| fully connected [12]x8, 1333 parameters | 0.862+-0.005 | 237-300 |
| **LSTM-24, 4249 parameters** | **0.909+-0.014** | **136-499** |
| boosting (XGBoost) | 0.918+-0.019 | ~24 000 |
| council of 3 + world with an administrator | 0.847 | 591 |
| judge over weak learners (3 pools) | 0.956 / 0.833 / 0.872 | 469 / 80 170 / 82 665 |
| counter "accounts from the source" | 0.618 | 161 100 |
| counter "destinations from the source" | 0.535 | 99 855 |

---

## 8. Conditions common to all measurements

- training on TDCv2 synthetic data only; real data was used solely for
  evaluation;
- Adam optimizer, learning rate 3e-3, 120 epochs (60 for sequence models),
  batch size 128 (64 for sequence models);
- the positive class weighted via `pos_weight` in `BCEWithLogitsLoss`;
- count features passed through `log1p(x)/8`, shares as they are, rhythm clipped at 8;
- 3 seeds per configuration; the mean +- standard deviation is reported;
- code: `net_py/sweep_big.py`, `net_py/recurrent.py`, `net_py/exotic.py`,
  `net_py/boosting.py`, `net_py/council.py`, `net_py/weak_council.py`,
  `net_py/symbiosis.py`.
