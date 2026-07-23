# mailorg — privacy-first agentic email organiser

Reads your Gmail and makes it digestible (categories, TL;DRs, triage, search, extracted
action items). The LLM runs **locally by default** via Ollama, so email content never
leaves your machine. Cloud LLM use is **opt-in per task**. The agent **proposes** actions
(labels, archives, drafts) and never writes to your mailbox without your approval.

See [implementation.md](implementation.md) for the full plan and phases, and
[CLAUDE.md](CLAUDE.md) for how we work on this project together.

## Requirements

- Python 3.13+
- [Ollama](https://ollama.com) running locally, with the models pulled:
  ```sh
  ollama pull gemma4:e4b     # light / resident
  ollama pull gemma4:12b     # heavy / on-demand
  # ollama pull nomic-embed-text   # only needed for Phase 4 (search)
  ```
- An NVIDIA GPU with a working driver is recommended (check with `nvidia-smi`).

## Setup

```sh
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install the project (editable) with core dependencies
pip install -e .
#   ...or add optional groups as you reach those phases:
#   pip install -e ".[rag]"     # Phase 4: semantic search
#   pip install -e ".[cloud]"   # Phase 6: cloud opt-in
#   pip install -e ".[dev]"     # linting + tests

# 3. Configure
cp .env.example .env            # then edit as needed

# 4. Initialise the local database
python -m mailorg.db
```

## Project layout

```
mailorg/
  config.py            # typed settings + privacy policy (cloud gate)
  db.py                # SQLite schema + helpers (single local file)
  providers/
    email/             # EmailProvider interface + Gmail impl   (Phase 1)
    llm/               # LLMProvider interface + Ollama/cloud    (Phase 2/6)
  embeddings/          # local embeddings + vector store         (Phase 4)
  agent/               # tools, agentic loop, proposed-action queue (Phase 5)
  pipelines/           # categorise / summarise / triage / ...   (Phase 2+)
  web/                 # FastAPI + HTMX UI                        (Phase 3)
data/                  # DB, OAuth token, client secret (git-ignored)
```

## Privacy model

- Default path is 100% local: Gmail → your machine → local Gemma → SQLite.
- Cloud is opt-in per task, gated by both `CLOUD_ENABLED` and a task allowlist.
- Your emails, OAuth token, and database live under `data/`, which is git-ignored.
