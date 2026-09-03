# Decision log

## Template

Context:
Options:
Decision:
Consequences:

## 2026-09-03 — eval qrels labelling

Context:
Need >= 25 queries with 3–10 relevant docs each for nDCG/Recall/MRR.
Helper only prints top 20; labels have to be human.

Options:
1. Label only from helper top 20
2. Use helper as a pool, skip junk hits, copy ids for paraphrases from the matching lexical topic
3. Let the agent invent qrels from titles alone

Decision:
Option 2. 33 queries (q01–q33). Binary relevant=1. Never marked seed_titles or
ATTRIBUTION. Paraphrases are q30–q33 (volcanoes, computers, WWII, nutrition).
q30–q33 reuse the lexical topic's qrels so a miss in the hybrid top 20 is not
treated as "not relevant".

Consequences:
Eval will not score 1.0. Paraphrases should look worse at alpha=1 than alpha=0.
q32/q33 are the better zero-overlap candidates for Scenario C.