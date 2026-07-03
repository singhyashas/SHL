# Approach

## Problem Framing

The assignment is best treated as a grounded recommender, not an open-ended
chatbot. The service accepts full stateless conversation history, reconstructs
the user's latest assessment-selection intent, and either clarifies, refuses,
compares, or returns a catalog-backed shortlist. I optimized first for hard
evals: exact schema, no server-side conversation state, max 10 recommendations,
and URLs only from the SHL catalog.

## Catalog and Retrieval

The pasted SHL product catalog is kept as `shl_product_catalog.json`. A
repeatable build step in `scripts/build_catalog.py` normalizes it into
`data/catalog.json`, preserving source fields and adding retrieval-friendly
fields such as `duration_minutes`, `test_type_codes`, `aliases`, and
`search_text`.

Retrieval is implemented locally in `app/retriever.py`. I used a BM25-style
lexical ranker instead of a hosted vector database because the catalog is small,
the API has a 30 second timeout, and deterministic behavior is easier to test
and defend. Ranking combines lexical score with field boosts for product names,
aliases, categories, seniority, assessment type, and duration constraints.
Lightweight query expansion handles common hiring phrases such as Java
developer, contact center sales, graduate aptitude, personality, and
stakeholder-facing roles.

## Agent Design

The agent is rule-based and inspectable. On each `/chat` call it reads the full
message history and chooses one of five paths:

- clarify when the request lacks role, skill, or job-description context
- recommend when enough context exists
- refine by combining prior user messages with the latest constraint
- compare named SHL assessments using catalog fields only
- refuse prompt injection, off-topic requests, legal/compliance questions,
  general hiring advice, and non-SHL product comparisons

This avoids relying on an LLM to invent product URLs or remember state. The
reply text is intentionally simple; the structured recommendation payload is
the source of truth for automated evaluation.

## Evaluation

Tests cover schema compliance, catalog integrity, retrieval behavior, agent
behavior probes, and local trace replay. The evaluation harness in
`evaluation/replay.py` reports hard-check status and Recall@10 over labeled
sample traces. Current local sample replay passes hard checks and achieves
mean Recall@10 of 1.0 across the included traces.

## What Did Not Work

A naive keyword matcher over `search_text` returned plausible but noisy results,
for example promoting generic developer or broad report products over specific
Java, OPQ, or Verify assessments. I replaced it with BM25-style scoring plus
explicit field boosts and used the replay harness to tune query expansion
without introducing a brittle fixed script.

## AI Tooling

I used AI-assisted coding to scaffold modules, write tests, and iterate on
retrieval/agent behavior. The final design remains deterministic, testable, and
small enough to explain line by line in a technical deep dive.
