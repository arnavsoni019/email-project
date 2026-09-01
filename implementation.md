# Plan: Privacy-First Agentic Email Organiser

## Context

The user wants to build an **agentic AI email organiser** that reads their mailbox and
presents its contents in a simple, digestible way (categories, summaries, triage,
search, extracted action items). The defining requirement is **privacy**: the LLM runs
**locally** by default so email content never leaves the machine, with an **optional,
per-task opt-in to a cloud LLM** for harder work.

This is a **greenfield project** (empty working directory, Python 3.13 available). The
user is planning now and will start building later.

### Decisions locked in during planning

| Decision | Choice |
|---|---|
| Language / stack | **Python** |
| Email access | **Gmail API first** (OAuth), Outlook/MS-Graph later behind the same interface |
| Agent autonomy | **Propose → user approves** — the agent never writes to the mailbox without a click |
| Platform | **Local web app** (FastAPI backend + browser UI on `localhost`) |
| Local LLM | Two-tier via **Ollama**: `gemma3n:e4b` (light, resident) + `gemma3:12b` Q4_K_M (heavy, on-demand) |
| Cloud LLM | Opt-in per task behind an `LLMProvider` interface (e.g. Claude via Anthropic SDK) |
| Agent framework | **LangChain + LangGraph** — LangGraph's human-in-the-loop interrupt powers propose→approve; cloud gate enforced in a single `get_llm(task)` factory |
| Vector store | **ChromaDB** (embedded/persistent, local) via `langchain-chroma` |

### Hardware (this machine — build target and run target are the same box)
Confirmed via probe: AMD **Ryzen 7 7840HS** (Phoenix) + Radeon 780M iGPU, NVIDIA
**GeForce RTX 4060 Mobile** (Max-Q, AD107M, **8 GB VRAM**), ~16 GB RAM, **Fedora**.
The two-tier model split is designed around the 8 GB VRAM ceiling: keep the small model
resident in VRAM, load the 12B only when a task needs it (Q4_K_M ≈ 7–8 GB, so it will
partially offload to CPU/RAM — usable but slower).

> **Phase 0 prerequisite:** `nvidia-smi` is currently **not available**, i.e. the NVIDIA
> driver + CUDA stack is not installed. Without it Ollama silently falls back to CPU and
> the 12B model crawls. On Fedora this means installing `akmod-nvidia` + CUDA (RPM Fusion)
> and verifying `nvidia-smi` reports the 4060 **before** benchmarking any local model.

---

## Architecture Overview

Everything is a **UI-agnostic Python engine** with a thin FastAPI/web layer on top. Two
key interfaces keep the design flexible: `EmailProvider` (swap Gmail↔Outlook) and
`LLMProvider` (swap local↔cloud).

```
Browser UI (HTMX + Jinja)
        │
   FastAPI web layer  ──────────────┐
        │                           │
   Agent loop (tools) ──── proposed-action queue (awaits approval)
        │                           │
  ┌─────┴──────┬──────────┬─────────┴───────┐
  │            │          │                 │
EmailProvider LLMProvider Embeddings     Pipelines
 (Gmail API)  (Ollama /   + Vector store  (categorise, summarise,
              Cloud,      (sqlite-vec)     triage, digest, extract,
              2-tier                       Q&A, draft)
              router)
        │
   SQLite (messages, threads, categories, actions, sync_state, vectors)
```

### Privacy model
- **Default path is 100% local**: Gmail → your machine → local Gemma → SQLite. Nothing
  leaves the box.
- **Cloud is opt-in per task**, shown explicitly in the UI, with a preview of exactly
  what text would be sent. A settings flag governs which task types may use cloud.
- OAuth is only *authentication* — email content flows Google→machine directly, never
  through a third party. Gmail OAuth app stays in "testing" mode for personal use (no
  Google security review needed).

---

## Feature Set (tiered, build in this order)

**Tier 1 — Understand & sort (read-only, ship first)**
- Smart categorisation (Work / Personal / Finance / Receipts / Travel / Newsletters / Social / Urgent)
- Per-email TL;DR (one-line summaries for a scannable list)
- Thread summaries (collapse long back-and-forths)
- Priority triage ("Needs action" / "FYI" / "Ignore")
- Daily/weekly digest

**Tier 2 — Extract & answer (read-only, more agentic)**
- Action-item / deadline / meeting extraction
- Natural-language inbox Q&A + semantic search (RAG)
- Follow-up reminders ("no reply in 5 days")
- Newsletter/subscription intelligence

**Tier 3 — Act (write access, propose→approve gate)**
- Draft replies (agent proposes, user approves/edits/sends)
- Suggest label / archive / move (queued as proposed actions)

---

## Proposed Project Structure

```
mailorg/
  pyproject.toml            # deps (see below)
  .env.example              # OAuth client, model tags, optional cloud keys
  README.md
  scripts/
    setup_ollama.sh         # ollama pull gemma3n:e4b / gemma3:12b / nomic-embed-text
  app/
    main.py                 # FastAPI entrypoint (uvicorn)
    config.py               # settings: model tiers, cloud toggle, categories
    db.py                   # SQLite schema + query helpers
    providers/
      email/
        base.py             # EmailProvider interface (list/get/modify/labels)
        gmail.py            # Gmail API impl + OAuth (installed-app flow)
      llm/
        base.py             # LLMProvider interface (generate / generate_json)
        ollama.py           # local two-tier (light=e4b, heavy=12b)
        cloud.py            # opt-in cloud backend
        router.py           # task → tier/provider routing
    embeddings/
      embedder.py           # local embeddings via Ollama nomic-embed-text
      vectorstore.py        # sqlite-vec wrapper (semantic search)
    agent/
      tools.py              # search_emails, get_thread, categorise, propose_* ...
      loop.py               # agentic tool-use loop
      actions.py            # proposed-action queue + executor (applies on approval)
    pipelines/
      categorise.py  summarise.py  triage.py
      digest.py      extract.py    qa.py     draft.py
    web/
      routes.py             # /auth, /sync, /inbox, /message, /digest, /ask, /actions
      templates/            # Jinja + HTMX
      static/
```

### Key libraries
- Gmail: `google-api-python-client`, `google-auth-oauthlib`, `google-auth`
- Web: `fastapi`, `uvicorn`, `jinja2` (+ HTMX for interactivity without a JS build)
- LLM + agent: `langchain` + `langgraph` over `langchain-ollama` (local models at `localhost:11434`); `langchain-anthropic` for the cloud opt-in
- Vectors: `chromadb` via `langchain-chroma` (embedded/persistent, local — a separate store beside SQLite)
- Embeddings: Ollama `nomic-embed-text` through `langchain-ollama`
- Core: `pydantic` (config + structured LLM outputs), `pydantic-settings`

---

## Build Phases (for when the user starts)

**Phase 0 — Foundations**
- **Install NVIDIA driver + CUDA on Fedora** (`akmod-nvidia` + CUDA via RPM Fusion) and
  confirm `nvidia-smi` sees the RTX 4060 — required before Ollama can use the GPU.
- Install Ollama; `scripts/setup_ollama.sh` to pull the three models (`gemma3n:e4b`,
  `gemma3:12b`, `nomic-embed-text`). Confirm exact Gemma tags at this point.
- `pyproject.toml`, `.env.example`, config, SQLite schema (`db.py`).

**Phase 1 — Gmail sync (read-only)**
- `EmailProvider` interface + `GmailProvider`: OAuth installed-app flow, initial backfill,
  incremental sync via Gmail History API (`historyId` in `sync_state`). Parse + store messages/threads.
- Smoke test: sync inbox, confirm rows in SQLite.

**Phase 2 — LLM layer + Tier 1 features**
- `LLMProvider` + `OllamaProvider` (two-tier) + `router`. `generate_json` for structured categorisation.
- Pipelines: `categorise`, `summarise` (per-email + thread), `triage`. Run E4B for bulk.
- This is the **first "does it actually work" checkpoint** — validate local model quality here.

**Phase 3 — Web UI (local)**
- FastAPI + HTMX: inbox list (category + TL;DR + priority), message/thread view, digest page, settings (local/cloud toggle, cloud task allowlist).

**Phase 4 — RAG search & Q&A (Tier 2)**
- Embeddings pipeline + `sqlite-vec` store. `qa.py` + `/ask` endpoint (agent searches, reads, answers). Action-item extraction + follow-up reminders.

**Phase 5 — Agent actions (Tier 3, propose→approve)**
- Agent tools that emit **proposed actions** (label/archive/draft) into the queue instead of executing. Approve/reject UI. `executor` applies approved actions via Gmail API.

**Phase 6 — Cloud opt-in + polish**
- `CloudProvider` wired behind the router (exact model + SDK pinned at build time). Consent is
  the Settings switch itself: a task shows `LOCAL`/`CLOUD` and the destination model and host
  are named on screen. **Decided against a per-question consent preview** — the switch is a
  deliberate act, and a dialog confirmed on every question becomes a reflex rather than
  consent. Then: Outlook/MS-Graph provider behind `EmailProvider`.

---

## Verification (per phase, end-to-end)

- **Phase 1:** run sync against the user's real Gmail; assert message/thread rows and a
  persisted `historyId`; re-run and confirm only new mail is fetched (incremental works).
- **Phase 2:** run `categorise`/`triage` over ~50 real emails; manually spot-check accuracy;
  confirm E4B stays resident and 12B loads only on heavy calls (`ollama ps`).
- **Phase 3:** open `localhost` UI, confirm inbox renders categories/TL;DR/priority and the
  digest reads sensibly.
- **Phase 4:** ask real questions ("when is my flight?", "receipts this month") and verify
  the agent retrieves the right emails and answers correctly.
- **Phase 5:** trigger a proposed label/archive/draft; confirm **nothing changes in Gmail
  until approved**, then confirm approval applies the change via the API.
- **Phase 6:** flip a task to cloud; confirm the Settings screen names the destination model
  and marks that task `CLOUD`, that the request actually reaches the provider (check the
  provider dashboard, not just the app), and that local-only tasks still never call out.

---

## Open items to settle at build time (sensible defaults chosen, adjustable)
- Exact category list (starting set proposed above).
- Digest cadence (default: on-demand + daily).
- ~~Confirm Gemma tags~~ — **resolved:** Gemma 4 is installed; using `gemma4:e4b` (light) + `gemma4:12b` (heavy).
- Which cloud provider/model for the opt-in path (pin when Phase 6 starts).