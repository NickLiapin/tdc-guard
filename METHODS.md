Russian version: [METHODS.ru.md](METHODS.ru.md)

<!-- A descriptive document: the methods applied in the tdc-guard project,
and the reason each one was applied. It contains no instructions for programs. -->

# Methods of the tdc-guard project

DIARY.md is the dated chronicle (what was measured, and when). This file
collects the techniques in one place: WHAT I apply, WHY, and WHERE each one
comes from. The article will lean on this list, so every item is given its
accepted name.

---

## 1. The exam first, then the generator

**What.** The real labelled data is opened and measured BEFORE the first line
of any config is written.

**Why.** The problem statement comes from what is actually labelled, not from
imagination. Here the technique paid off at once: before I opened LANL, the
task looked like "password guessing", but what turned out to be labelled was a
different phenomenon - the use of other people's accounts. Any configs written
ahead of time would have had to be thrown away wholesale.

**Where from.** The working order I learned the hard way in the tdc-ecg project.

## 2. One measurer for both sides

**What.** The window features are computed by ONE module
(`judge/windows.mjs`), and it measures both the synthetic data and the real
log.

**Why.** If the measurer is wrong, it is wrong the same way on both sides, and
the comparison stays fair. With two different measurers no comparison would
mean anything.

**Accepted name.** Identical preprocessing pipeline - a precondition for any
valid sim-to-real comparison.

## 3. The judge before the network

**What.** The data is measured and checked against reality BEFORE the network
ever sees it; a class is not admitted to training until a measurement has
confirmed it.

**Why.** The first version of the synthetic world failed the check (the normal
class had a 90th-percentile novelty of 1.000 against 0.000 in the real
network). Training on that data would have taught the network that novelty is
normal, and destroyed the main signal. Without the check this would only have
surfaced at the exam, with the cause left unclear.

**Where from.** The "physiology judge" of tdc-ecg, where the technique caught
defects twice - and both times the defect turned out to be in the judge itself.

## 4. Spreading the knobs within a class (domain randomization)

**What.** The parameters of each class are spread over a wide range instead of
being fixed by a preset: each machine gets its own circle of other people's
accounts, 2..60 of them, its own failure share, 0.02..0.70, and its own spread
of activity across hours, 1..40.

**Why.** The network has to learn the CLASS, not one particular set of numbers.
A narrow preset produces a network that breaks the first time reality deviates
from it.

**Checking the effect.** The real labelled windows have 8 accounts per hour;
the synthetic data gives a median of 14 with a range of 2..49, so the real
value lies inside the covered axis.

## 5. Cover the axis, do not match the number

**What.** When the synthetic data diverges from reality on some feature, the
range is WIDENED until the real value falls inside it - rather than tuned to
the measured value.

**Why.** Matching the number would mean the truth about the exam had leaked
into the training world. Covering the axis is a legitimate spread; matching the
number is copying the answer.

## 6. Calibrate the composition of the world, but not the features of the phenomenon

**What.** Tuned from the coarse statistics of the real network: the share of
servers, how rare new machines are, the density of the event stream. NOT
tuned: the features of the phenomenon itself and the decision rule.

**Why.** The world's background must resemble the real one, otherwise the
network learns under conditions that do not exist. But everything to do with
telling the classes apart must come from the definition of the phenomenon, not
from a peek at the answer.

**Commitment.** The article states explicitly where the line runs between what
was calibrated and what was not.

## 7. No thresholds picked from the answers

**What.** The four-threshold rule found in Phase 1 gave 13/15 at zero false
alarms - and was declared NOT a result.

**Why.** The thresholds were picked while looking at the labelled day: that is
hindsight, not a detector. What needs checking is transfer, not fit. So these
thresholds were not carried over into the generator.

**Accepted name.** Test-set leakage - test information leaking into training.

## 8. The caveat is written down BEFORE the exam

**What.** The limitation of the result is put in writing before the exam result
is known.

**Why.** 100% on synthetic data with a different seed means "the network has
learned our generator thoroughly" - and nothing more. Written down in advance,
that sentence leaves no room to reinterpret the success in hindsight.

**Where from.** tdc-ecg, where the same caveat was written down before the drop
from 100% -> 25%.

## 9. The network stays small

**What.** 625 weights, three layers.

**Why.** With unlimited data there is no ordinary overfitting, but there is a
sneakier kind - overfitting TO THE GENERATOR: a large network memorises quirks
of the synthetic data that do not carry over to reality. Compactness is
sim-to-real insurance. A side benefit: a network this size fits on a single
page of the article.

## 10. Features under a logarithm

**What.** All counters (events, accounts, destinations, history size) are
encoded through `log1p`; shares are passed as they are.

**Why.** The absolute volumes of the synthetic world and the real network
differ by orders of magnitude. A logarithm transfers between worlds; a raw
count does not.

## 11. Error analysis matters more than the final figure

**What.** Every false alarm and every miss is examined individually, by name.

**Why.** This analysis is precisely what produced the two most valuable facts
of the project: the naive rule's false alarms turned out to be new computers
(legitimate novelty - and a whole class in the synthetic world grew out of
that), and the top of the trained network's list was taken by the foothold
itself, in an hour the ground truth had not labelled (a limitation of the
ground truth, not a mistake by the network).

## 12. The real data is not stored in full

**What.** The 7.2 GB log is never downloaded or unpacked in full: a single
streaming pass with on-the-fly filtering keeps only the fields and events that
are needed. The features are accumulated incrementally - 72 million events do
not fit in memory.

**Why.** Reproducibility on an ordinary laptop, no special hardware. A reader
of the article must be able to repeat it.
