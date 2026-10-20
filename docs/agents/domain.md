# Domain Docs

How sessions and the engineering skills consume this repository's domain documentation.

## Before exploring, read these

- `GLOSSARY.md` at the repo root, or `GLOSSARY-MAP.md` when it exists: it points at one
  `GLOSSARY.md` per context, so read each one relevant to the topic.
- `docs/adr/`: the ADRs that touch the area you are about to work in. In a multi-context
  repository also check each context's own `docs/adr/`.

If a file is absent, proceed silently: do not flag it and do not suggest creating it upfront.
`domain-modeling` creates glossary entries and ADRs lazily, when a term or decision is
actually resolved.

## Layout

Single context: `GLOSSARY.md` and `docs/adr/` at the repository root.

## Use the glossary's vocabulary

Name domain concepts as `GLOSSARY.md` defines them in issue titles, specs, refactor
proposals, hypotheses and test names, and avoid the synonyms it lists under _Avoid_. A
concept the glossary lacks is a signal: either the language is invented, or there is a gap
for `domain-modeling`.

## Flag ADR conflicts

When an output contradicts an existing ADR, say so explicitly instead of overriding it
silently, for example: _Contradicts ADR-0007 (event-sourced orders), but worth reopening
because..._

The glossary holds terms and meanings only. Purpose and non-goals belong in the README; hard
boundaries and ownership in `AGENTS.md`.
