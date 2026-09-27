# DraftClaim subject-compatibility diagnostic

## Scope

This eval-only experiment adds deterministic `subject / predicate / value` signatures before
confirming semantic duplicates. It uses the unchanged frozen 15-case Development set and the
same boundary-v2 prompt. Production, validation, and holdout are untouched.

- Dataset SHA-256: `35db5be33aedcc35122f2cdc4138ee72bb7505d480978996f56f92f1e967aa69`
- Freeze manifest SHA-256: `2d8d0d46f923e7eaed16f622d90d71dffd225e5249d4093226bf3b7410838378`
- Evaluated commit: `94352dd79ef989ab6cce7f4df03e0ccd98d99a49`
- Duplicate policy: bidirectional NLI entailment AND resolved, equal subjects
- Effect: diagnostic only; no extracted claim is removed

## Three-run result

All three runs produced the same 43 claims and identical metrics:

- JSON/schema valid rate: 100%
- Required-claim recall: 96.97%
- Extra-claim rate: 11.63%
- Unsupported-claim rate: 4.65%
- NLI-retained claim rate: 95.35%
- Exact claim-set stability: 100%
- Mean pairwise claim Jaccard: 100%
- Subject-signature resolution rate: 79.07%
- NLI semantic-duplicate candidate rate: 6.98% (3/43)
- Subject-conflict rejection rate: 4.65% (2/43)
- Confirmed semantic-duplicate rate: 2.33% (1/43)
- Runtime: 31.98 s, 22.37 s, and 22.11 s

## Duplicate funnel

All three duplicate candidates came from `ce-010`:

1. `生产组装保持不变` -> `默认检索行为保持不变`: rejected because subjects differ.
2. `生产组装保持不变` -> `默认检索行为没有改变`: rejected because subjects differ.
3. `默认检索行为保持不变` -> `默认检索行为没有改变`: confirmed.

The protection layer therefore rejected both observed NLI false positives and retained the one
true duplicate. Observed confirmed precision is 100% (1/1), but the sample is too small to claim
general precision.

## Limits and decision

Signature extraction resolved 79.07% of claims. Unresolved pronouns, omitted subjects, unusual
word order, and predicates outside the deterministic marker list remain deliberately
unconfirmed. This favors false negatives over destructive false positives, which is appropriate
for a diagnostic layer.

The subject-compatibility layer is accepted as an eval-only diagnostic. It is not approved for
production deduplication. The next evidence-building step should add a separately frozen fixture
set of positive and negative duplicate pairs, including pronouns, aliases, nested subjects,
numbers, dates, and negation, before considering broader integration.
