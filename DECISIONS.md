# Technical Decisions

This file records decisions visible in the current implementation. Where the
repository does not state why a choice was made, that rationale is marked
**Not recorded** rather than inferred.

## Local classifier instead of a remote generative AI call

- **Current design:** A TF-IDF + Logistic Regression pipeline classifies the
  incident text; templates generate the summary, root-cause wording, and
  next-step suggestions.
- **Verified rationale:** README describes a local-first goal without
  requiring an external AI API.
- **Trade-off:** Runs with a local classifier artifact but does not produce
  open-ended, contextual root-cause reasoning.

## Heuristic labels for the training corpus

- **Current design:** Lines containing configured failure-related substrings
  receive anomaly label 1; other lines receive label 0.
- **Rationale:** Not recorded in code or current README beyond a practical
  prototype framing.
- **Trade-off:** Repeatable labeling is simple, but the model learns the
  labeling heuristic and its metrics do not establish real-world accuracy.

## Separate semantic retrieval and classification models

- **Current design:** `all-MiniLM-L6-v2` ranks service evidence; the saved
  TF-IDF/Logistic Regression pipeline classifies the incident prompt.
- **Rationale:** Not recorded.
- **Trade-off:** Retrieval can provide context snippets independently, but the
  classifier's decision is made on the prompt, not on the retrieved snippets.

## PostgreSQL persistence is optional for analysis

- **Current design:** The backend tries to save each analysis. An insert
  failure returns the analysis with a warning; history queries require the
  database.
- **Rationale:** Current README says the app can be tested locally without
  database persistence.
- **Trade-off:** Analysis remains available, but users may confuse a successful
  response with a saved record unless they notice the warning.

## Service-specific files as evidence sources

- **Current design:** The retriever maps the submitted service string to
  matching filenames under `data/logs`, `data/metrics`, and
  `data/deployments`.
- **Rationale:** Not recorded.
- **Trade-off:** Easy to add local fixture data; no dynamic integration with
  production logging or monitoring systems is implemented in the inspected
  code.

## Explicit local CORS origins

- **Current design:** Backend CORS allowlists configured frontend origins and
  known local development origins. The frontend API base defaults to
  `http://localhost:5000`.
- **Rationale:** Comments state local development should continue to work even
  when `FRONTEND_URL` is set to a deployed URL.
- **Trade-off:** New browser origins must be added to configuration/allowlists.

## Historical state

Git history contains earlier Gemini-related commits, including model changes
and retry handling. The current checked-out README and working-tree
implementation use the local classifier path instead. Historical commits
should not be taken as evidence that Gemini is currently part of the runtime.
