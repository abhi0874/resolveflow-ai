# Synthetic retrieval corpus v1

Fourteen fictional support policy documents, each producing one stored chunk with
Step 6's default chunker. Twenty-four frozen questions include paraphrases,
two deliberately ambiguous questions and three questions with no supporting source.
`relevant` lists all acceptable source IDs; an empty list means no answer exists.
Since each scored document is one passage, passage and document relevance coincide.
These policies are fictional evaluation data, **not claims about implemented product
features or contractual customer policies**. There is no real customer information.

The 0.30 cosine threshold, 384-dimensional pinned MiniLM model, token-window policy
and K=1/3/5 were selected before inspecting these results. No training, fine-tuning,
query rewriting or final-set threshold optimization was performed. Repeated runs
verify implementation and add timing measurements; this set is no longer an unseen
benchmark for future tuning. Create a new frozen test set before comparing tuned
candidates. Labels were manually authored with the synthetic documents and have no
independent annotation study.

See docs/RETRIEVAL_EVALUATION.md for actual results, errors and limitations. The
committed report records the dataset SHA-256, model revision, packages and rankings.
