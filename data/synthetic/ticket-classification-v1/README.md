# Synthetic ticket classification corpus v1

Author: ResolveFlow AI project development, 2026-10-19. All 280 examples were
written synthetically for this project; no customer records, downloads or external
dataset are used. `tickets.jsonl` is the authoritative versioned dataset. It is
UTF-8 JSON Lines with `id`, `group_id`, `title`, `description`, and `label`.

Each of seven categories has 20 scenario groups with two related phrasings: 40
examples per class. Groups capture shared intent/context, including paraphrases
and shared titles. Seed 42 splits groups separately per label into 12 train,
4 validation and 4 test groups (24/8/8 records per class; 168/56/56 overall).
The split manifest and byte-level SHA-256 are saved with each trained model.

The single category definition is `resolveflow.ml.contracts.Category`. Existing
free-text application categories remain valid; these labels are recommendations,
not a destructive remapping of historical tickets.

Labeling rules:

- Billing: transactions, invoices, receipts, tax, refunds and payment failures.
- Technical Support: malfunctioning existing features or integrations.
- Account Access: authentication, recovery, invitations and permissions.
- Subscription Management: changes to an existing plan, seats, term or renewal.
- Product Inquiry: capabilities or pricing questions while evaluating a product.
- General Support: help channels, guidance and management of support conversations.
- Other: unrelated, unintelligible or non-support requests, not a universal OOD detector.

Boundary examples intentionally share vocabulary: payment rejection versus a
software error; product SSO capabilities versus inability to sign in; evaluating
pricing versus changing an active subscription. The corpus includes short and
longer requests, varied phrasing, a few spelling errors and ambiguous intents.
Labels are manually chosen under these rules, not independent expert annotations.

Loading rejects invalid labels, duplicate IDs, normalized exact duplicates and
cross-group token-trigram Jaccard similarity >=0.8. The similarity check catches
some lexical copies, not all semantic duplicates; manual group review remains
necessary. Do not scatter paraphrases into different groups to improve metrics.
Features are fitted only on training records. Final test data is not used to pick
hyperparameters or the fixed initial threshold.

This small, balanced English corpus is a development baseline. It does not capture
real class prevalence, languages, domain terminology, customer writing styles or
all out-of-distribution requests. Related phrasings inside each test group mean
there are 28 independent held-out scenarios, not 56 independent customer cases.
Do not infer production accuracy or statistically reliable confidence from it.
Use a new dataset version and a new immutable model version for future changes.
