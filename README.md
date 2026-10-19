# Manuscript Reviewer

A **privacy-aware, multi-agent system for scholarly peer review**. It reads a
manuscript, decides what kind of paper it is, has **two independent reviewer
agents** assess it against a journal-specific rubric, and a **judge** reconcile
their verdicts into a final accept/reject decision with an author decision
letter.

The whole thing is **provider-agnostic**: each role can run on a local model
(Ollama), OpenAI, or Anthropic. The default keeps everything **local so the
manuscript never leaves your machine**.

---

## Why these design choices

### The 4-role pipeline

```
 manuscript (PDF/txt/md)
        │
        ▼
 ┌──────────────┐   deterministic parsing + author redaction (no LLM)
 │  Ingestion   │   → clean, de-identified sections
 └──────┬───────┘
        ▼
 ┌──────────────┐   "Editor": identifies field/type, picks the rubric,
 │   Triage     │   defines the two reviewer personas
 └──────┬───────┘   → understand scope first, then assign roles
        ▼
 ┌──────────────┐   two experts review INDEPENDENTLY against the rubric:
 │  Reviewer 1  │   scores, strengths/weaknesses, recommendation,
 │  Reviewer 2  │   and a concrete "path to acceptance"
 └──────┬───────┘
        ▼
 ┌──────────────┐   "Area Chair": reconciles disagreements, grounds the
 │    Judge     │   decision in the rubric's weighted-score thresholds,
 └──────┬───────┘   writes the author letter
        ▼
   Review report (Markdown or JSON)
```

- **Triage first** — the paper's field determines *which rubric* applies and
  *what expertise* the reviewers should embody.
- **Rubrics are config, not code** — each venue is a YAML file in
  [`config/rubrics/`](config/rubrics). Add a journal by adding a file; no code
  changes. Criteria are weighted and mapped to accept / minor / major / reject
  thresholds, so the final decision is **rule-based, not vibes-based**.
- **Independence** — reviewers get fresh model clients and never see each
  other's output, mirroring real double-blind review.

### Do we need LLMs?

Yes, for the open-ended reasoning (judging novelty, soundness, writing
feedback). But parsing, redaction, score aggregation, and the final
accept/reject rule are all **deterministic, no model required**. LLMs sit at the
center, wrapped in deterministic scaffolding.

### Keeping the manuscript from leaking

Unpublished manuscripts are sensitive IP and many venues forbid uploading them
to public AI tools. This system gives you, strongest-privacy-first:

1. **Local models via Ollama (default)** — nothing leaves your machine.
2. **Your own OpenAI / Anthropic keys** — frontier quality, but the (redacted)
   text is sent to the provider. Use only where policy permits, ideally with
   retention/training disabled.
3. **`privacy.local_only: true`** — a hard switch that *refuses to run* if any
   role is pointed at a cloud provider, so you can't leak by accident.
4. **Author redaction** (`privacy.redact_author_identity`) — strips names,
   affiliations, emails, and acknowledgements before any text is sent, enabling
   double-blind review.

> Redaction protects *author identity*. It does **not** protect the paper's
> *ideas*. For sensitive IP, keep the reviewer role on a **local** provider.

**GitHub Copilot models are intentionally not supported** — Copilot is licensed
for in-editor coding assistance, exposes no general document API, and doesn't
provide the retention guarantees unpublished manuscripts need.

---

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .            # core (local Ollama path)
pip install -e ".[all]"     # add OpenAI + Anthropic backends
```

### Local models (default)

Install [Ollama](https://ollama.com), then pull the models named in
[`config/config.yaml`](config/config.yaml):

```bash
ollama pull llama3.1:8b     # triage
ollama pull qwen2.5:32b     # reviewers + judge (use the largest you can run)
```

### Cloud backends (optional)

```bash
cp .env.example .env        # add OPENAI_API_KEY / ANTHROPIC_API_KEY
```

Then set a role's `provider` to `openai` or `anthropic` in
[`config/config.yaml`](config/config.yaml).

---

## Usage

```bash
# List available venue rubrics
manuscript-reviewer --list-rubrics

# Review a manuscript, print a Markdown report
manuscript-reviewer path/to/paper.pdf

# Write JSON instead, to a file
manuscript-reviewer path/to/paper.pdf --json -o review.json

# Use a specific config
manuscript-reviewer path/to/paper.pdf -c config/config.yaml
```

From Python:

```python
from manuscript_reviewer.pipeline import ReviewPipeline

report = ReviewPipeline().run("path/to/paper.pdf")
print(report.decision.recommendation, report.decision.accepted)
print(report.to_markdown())
```

### Try it with no model (offline)

Set every role's `provider` to `mock` in the config to run the full pipeline
deterministically with no network and no model — useful for development:

```bash
manuscript-reviewer examples/sample_manuscript.txt -c your_mock_config.yaml
```

---

## Configuration

[`config/config.yaml`](config/config.yaml) controls everything:

- `roles.{triage,reviewer,judge}` — `provider` (`ollama`/`openai`/`anthropic`/`mock`),
  `model`, `temperature` per role. Mix freely (e.g. local triage + cloud reviewers).
- `privacy.redact_author_identity` — double-blind redaction on/off.
- `privacy.local_only` — refuse to run with any cloud provider.
- `review.num_reviewers` — number of independent reviewers (default 2).
- `review.default_rubric` — fallback when triage can't match a venue.

---

## Project layout

```
config/
  config.yaml            # providers, per-role backends, privacy switches
  rubrics/*.yaml         # one rubric per venue (the "journal criteria")
prompts/                 # triage / reviewer / judge prompt templates
src/manuscript_reviewer/
  ingestion/             # parsing (PDF/txt/md) + author redaction
  llm/                   # provider-agnostic clients + factory
  agents/                # triage, reviewer, judge
  rubrics.py             # rubric loading + weighted scoring/decision rules
  pipeline.py            # orchestration + report rendering
  cli.py                 # command-line entry point
tests/                   # run with: pytest
```

## Tests

```bash
pytest
```

Tests use the offline `mock` backend, so they run fast with no model or network.
