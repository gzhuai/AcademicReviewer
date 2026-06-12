# AI Handoff Document — AcademicReviewer

> **Who this is for:** AI coding assistants (Claude Code, Codex, Cursor, Copilot, etc.) that need to understand this codebase quickly and accurately.
> **Language:** All source code comments and docs are in Chinese. This doc is in English for maximum AI comprehension.
> **Last updated:** 2026-06-12

---

## 1. Project Summary

AcademicReviewer is a **multi-agent AI paper review system** for high school academic competitions (ISEF, John Locke, HiMCM, etc.). It uses 5 specialized LLM agents in a 2-round parallel pipeline to review student papers against competition rubrics. A companion "calibration engine" performs statistical analysis (no LLM) on winner vs. loser papers to generate scoring rule improvements.

**Stack:** Python 3.10+ / FastAPI / Gradio / SQLite / ChromaDB / httpx (no LangChain, no LlamaIndex)

**Entry points for dev:**
```
python run.py                              # Backend (FastAPI on :8000)
python app/gradio_app.py                   # Frontend (Gradio on :7860)
# Or use scripts:
scripts/start_all.bat                      # Windows one-click launcher
```

---

## 2. Module Map — What Each File Does

### Entry Points
| File | Role |
|------|------|
| `run.py` | `ensure_dirs()` → `init_db()` → `uvicorn.run("app.main:app")` |
| `app/gradio_app.py` | Gradio Web UI. Calls backend via `httpx`. 6 tabs (Submit Review, History, System Status, Calibration, Dashboard, Competition Management). |
| `launcher.py` | (Optional) Single-process launcher that starts backend in thread + frontend. Not in main workflow. |

### Core App (`app/`)
| File | Role |
|------|------|
| `app/main.py` | **FastAPI app.** All REST endpoints. File upload handling, DB session management. Defines `app = FastAPI(title="AcademicReviewer", version="0.2.0")`. |
| `app/orchestrator.py` | **Scheduler.** `Orchestrator.review()` runs Round 1 (A1+A2+A3 in `asyncio.gather`) → Round 2 (A4+A5). Computes weighted total score from per-competition `agent_weights` in `competition_registry.json` (defaults exist). Loads `style_guide` JSON and passes to A4. Uses lazy imports inside method body to avoid circular deps. |
| `app/config.py` | **Global config singleton.** `Settings` class via `pydantic-settings`. Provides `normalize_competition_name()`, `get_competition_list()`, and `api_token` (Bearer auth, optional). |
| `app/database.py` | SQLAlchemy engine + session factory. `init_db()` calls `Base.metadata.create_all()`. |

### Agents (`app/agents/`) — 5 LLM-powered reviewers
Each agent extends `BaseAgent` and has a `.txt` prompt template in `prompts/`.

| File | Agent | Prompt | Weight | What it checks |
|------|-------|--------|--------|----------------|
| `base.py` | `BaseAgent` (ABC) | — | — | `_load_prompt()`, `run()` calls `self.llm.chat_json()`, standardizes return dict with `agent/model/provider/duration_seconds` |
| `rubric_parser.py` | A1 RubricParser | `a1_rubric_parser.txt` | from registry | Parses competition rubric JSON into structured dimension tree |
| `structure_logic.py` | A2 StructureLogic | `a2_structure_logic.txt` | from registry | Checks skeleton completeness against `configs/structure_schemas/{type}.json`. Type-agnostic coaching prompt with per-type sections from config. |
| `argument_evidence.py` | A3 ArgumentEvidence | `a3_argument_evidence.txt` | from registry | Claim-evidence matching, logical fallacy detection. Type hints loaded from `configs/competition_type_hints.json`. `validation_point` type auto-switches per competition type. |
| `language_style.py` | A4 LanguageStyle | `a4_language_style.txt` | from registry | Grammar/spelling/punctuation rewrites (Iron Law: only fix surface errors). Receives `style_guide` JSON from orchestrator — e.g. tech_academic allows 40% passive, discursive caps at 30%. |
| `academic_integrity.py` | A5 AcademicIntegrity | `a5_academic_integrity.txt` | from registry | Citation matching (rules engine) + originality check (ChromaDB) + LLM synthesis |

**Agent execution model:** `BaseAgent.run(**kwargs)` → `_build_system_prompt(kwargs)` + `_build_user_message(kwargs)` → `llm.chat_json(system, user, temperature=0.2)` → dict. Each agent overrides `_build_user_message()` to format its specific input.

### LLM Adapters (`app/llm/`) — Multi-model abstraction, raw HTTP only
All adapters use `httpx.AsyncClient` with 3 retries. No LangChain. Self-register at module bottom via `LLMFactory.register("name", Class)`.

| File | Provider | Model | Notes |
|------|----------|-------|-------|
| `base.py` | ABC | — | `LLMAdapter` ABC: `chat()`, `chat_json()`, `model_name()`, `provider_name()`. `chat_json()` strips markdown fences, parses JSON, fallback to `{raw_output, parse_error}`. `LLMFactory` registry dict. |
| `openai_adapter.py` | OpenAI | gpt-5.5 | Compatible with standard OpenAI Chat Completions API |
| `deepseek_adapter.py` | DeepSeek | deepseek-chat | Custom response parsing (avoids openai SDK dep) |
| `gemini_adapter.py` | Gemini | gemini-pro | Uses Google REST API; system prompt simulated via user/model conversation pairs |
| `glm_adapter.py` | GLM (Zhipu) | glm-4-plus | OpenAI-compatible protocol |

### Models (`app/models/`)
| File | Role |
|------|------|
| `submission.py` | 3 SQLAlchemy ORM models: `Submission` (paper metadata), `Review` (agent scores + `feedback_json`), `CalibrationRecord` (sync history) |

### Utils (`app/utils/`)
| File | Role |
|------|------|
| `doc_parser.py` | `parse_document(file_path)` → `ParsedDocument(text, word_count, metadata)`. Supports `.txt`, `.md`, `.docx` (python-docx), `.pdf` (PyPDF2) |
| `citation_checker.py` | **Rule engine (zero LLM).** `check_citations(text, refs_section)` → `CitationReport(total_cites, matched_count, unmatched_cites, unmatched_refs, match_rate, format_issues)`. Uses 4 regex patterns for cite key extraction + substring matching against reference section. |
| `vector_store.py` | ChromaDB wrapper. `index_document()` chunks text and adds to collection. `check_originality()` queries top-k similar chunks, computes originality score from similarity thresholds (high≥0.75, medium≥0.50). Cosine distance, HNSW space. |
| `sync.py` | **Team collaboration.** `report_review()` / `report_calibration()` fire-and-forget POST to central server. `pull_configs_from_server(dry_run=True/False)` GETs configs, diffs, applies with backup. Uses `_get_instance_name()`: `settings.instance_name` or `socket.gethostname()`. |

### Calibration Engine (`app/calibration/`) — Phase 3, pure statistics (no LLM)
| File | Role |
|------|------|
| `engine.py` | **Pipeline orchestrator.** `run_calibration()` chains: feature extraction → Cohen's d → cross-validation → config diff → expert parsing → report generation. Features and config mappings are **per-competition-type**: `feature_names(type)` returns 21 features for research, 15 for discursive. `FEATURE_TO_CONFIG_MAP_BY_TYPE` provides type-specific mapping. |
| `feature_extractor.py` | Type-aware text feature extraction (regex + stats, zero LLM). `FEATURES_BY_TYPE` dict: research gets 21 features (including has_p_value, has_effect_size), discursive gets 15 (excluding research-only binary checks). Outputs `DocumentFeatures` dataclass. |
| `diff_generator.py` | `generate_rule_updates()` maps effect sizes to config paths via `FEATURE_TO_CONFIG_MAP_BY_TYPE`. `generate_fatal_defect_updates(competition_type)` uses `BINARY_FEATURES_BY_TYPE` — so John Locke won't suggest "missing p-value" as fatal defect. `diff_configs(old, new)` recursive dict diff. |
| `cohens_d.py` | `compute_effect_sizes(w_features, l_features)` → list of `EffectSizeResult`. Labels: large (d≥0.8), major (d≥0.5), minor (d≥0.2), none. `cross_validate(my_w, ext_w)` for external validation. |
| `report_generator.py` | `generate_calibration_report()` → Markdown string: effect size table, cross-validation table, config change proposals, manual review checklist, expert insights section. |
| `expert_annotator.py` | Mode 3: structured teacher insight parser (regex, zero LLM). Parses `### [type] feature_name` format. `FEATURE_KEYWORDS` dict maps keywords to features. |
| `expert_freeform_parser.py` | Mode 1/2: semi/free-form teacher insight parser (uses LLM for text→knowledge extraction, then local keyword mapping for feature assignment to prevent hallucination). |

### CLI (`cli/`)
| File | Role |
|------|------|
| `calibrate.py` | `argparse` CLI for calibration engine. Accepts `--competition`, `--type`, `--winners`, `--losers`, `--external`, `--expert-docs`, `--output`. Sets `sys.path[0]` to project root. |

### Tests (`tests/`)
| File | Role |
|------|------|
| `test_e2e.py` | Single end-to-end test. Uses `asyncio.run()` to construct LLM + Orchestrator, reviews `fixtures/sample_isef_paper.txt`, prints scores. |
| `test_agents/__init__.py` | Empty placeholder |
| `test_llm/__init__.py` | Empty placeholder |
| `fixtures/sample_isef_paper.txt` | Sample research paper for testing |

**Testing gap:** No pytest config. Unit tests for agents/llm/calibration need to be written. See `docs/测试计划与步骤.md` for planned test cases.

---

## 3. API Endpoint Reference

All under `/api/v1/`:

| Method | Path | Purpose | Key Params |
|--------|------|---------|------------|
| `GET` | `/health` | Health check | — |
| `POST` | `/review` | Submit paper for review | `file` (multipart), `competition`, `student_name?`, `model_provider?` |
| `GET` | `/competitions` | List registered competitions | — |
| `GET` | `/reviews` | Paginated review history | `offset`, `limit` |
| `GET` | `/reviews/{id}` | Single review detail | `submission_id` |
| `GET` | `/config/stats` | Config file counts + DB stats + sync status | — |
| `POST` | `/sync/review` | Receive review report from colleague | JSON body with `instance_name` |
| `POST` | `/sync/calibration` | Receive calibration report from colleague | JSON body with `instance_name` |
| `GET` | `/sync/configs` | **Download current configs** (all JSON files + version hash) | — |
| `GET` | `/admin/dashboard` | Aggregated dashboard (total reviews, calibrations by instance/competition, recent records) | — |
| `GET` | `/admin/competitions` | List all registered competitions with full config | — |
| `POST` | `/admin/competitions` | Save competition registry (add/edit/delete). Auto-backs up old config. | JSON body with `competitions` array |

All responses are JSON. Errors return `{"detail": "..."}` with appropriate HTTP status codes.

**Security:** All endpoints under `/api/v1/` are gated by optional Bearer Token auth. Set `API_TOKEN=secret` in `.env` to enable. File uploads capped at 50MB, extensions whitelisted to `.txt/.md/.pdf/.docx`.

---

## 4. Data Flow (Review Pipeline)

```
User uploads file via Gradio
        │
        ▼
POST /api/v1/review (main.py)
        │
        ├── Parse doc (doc_parser.py → ParsedDocument)
        ├── Lookup competition (orchestrator.py → competition_registry.json)
        │
        ├── Round 1: asyncio.gather(
        │       A1.run(rubric_text=json),
        │       A2.run(document_text, competition_type),
        │       A3.run(document_text, evidence_config),
        │   )
        │
        ├── Extract references section (regex)
        │
        ├── Round 2: asyncio.gather(
        │       A4.run(document_text),
        │       A5.run(document_text, refs_section, similarity_report),
        │   )
        │
        ├── _compute_total_score() → weighted sum of 5 agent scores
        │
        ├── Persist to SQLite (Submission + Review records)
        ├── Fire-and-forget sync to central server (if configured)
        │
        └── Return JSON response
```

---

## 5. Configuration System

### `.env` (environment variables)
```
OPENAI_API_KEY=sk-xxx
DEEPSEEK_API_KEY=sk-xxx
GEMINI_API_KEY=xxx
GLM_API_KEY=xxx
LLM_PROVIDER=deepseek           # which LLM to use by default
DATABASE_URL=sqlite:///./data/academic_reviewer.db
CHROMA_PERSIST_DIR=./data/chroma
HOST=127.0.0.1
PORT=8000
SYNC_SERVER_URL=                # central server URL (empty = no sync)
INSTANCE_NAME=                  # colleague name for dashboard
```

### `configs/` directory (competition rules)
```
configs/
├── competition_registry.json   # Maps competition name → type/subtype/config references
├── rubrics/                    # Scoring rubrics (isef_2026.json)
├── structure_schemas/          # Expected paper structures per type (8 files)
├── evidence_patterns/          # Evidence requirements per type (9 files)
├── style_guides/               # Style templates per type (6 files)
└── citation_rules/             # Citation format rules (apa.json, mla.json, chicago.json)
```

`competition_registry.json` is the single source of truth for which competition maps to which configs. Adding a new competition = add an entry here + create corresponding JSON files.

---

## 6. Coding Conventions

| Aspect | Rule |
|--------|------|
| **Imports** | Stdlib → third-party → `app.*`, all absolute. No `import *`. Lazy imports inside methods to avoid circular deps (see `orchestrator.py`) |
| **Naming** | Classes: PascalCase. Functions/vars: snake_case. Private: `_` prefix. Constants: UPPER_SNAKE. Module files: snake_case. |
| **Type hints** | Used on function signatures and dataclass fields. Not universal on private methods. |
| **Docstrings** | Module-level docstrings on complex files. Class-level brief descriptions. Function docstrings are sparse. |
| **LLM adapters** | Each is a class implementing `LLMAdapter(ABC)`. Self-registers at module bottom: `LLMFactory.register("name", Class)`. All use raw `httpx.AsyncClient`, 3 retries. |
| **Agents** | Extend `BaseAgent`. Override `_build_user_message()`. Prompt templates in `prompts/` directory. Return dict always includes `agent`, `model`, `provider`, `duration_seconds`. |
| **Error handling** | Exceptions caught at API layer (main.py) → 400/500 responses. Agent errors collected in `report.errors` list, don't crash the pipeline. |
| **Path resolution** | Use `Path(__file__).resolve().parent.parent` pattern for configs/prompts/data directories. Avoid hardcoded paths. |
| **File encoding** | Always `encoding="utf-8"` when reading/writing text files. |

---

## 7. Dependencies (`requirements.txt`)

```
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
sqlalchemy>=2.0.0
python-docx>=1.1.0
PyPDF2>=3.0.0
python-multipart>=0.0.12
httpx>=0.28.0
chromadb>=0.5.0
gradio>=5.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
openai>=1.0.0
google-generativeai>=0.8.0
zhipuai>=2.0.0
```

Key implications:
- `chromadb` brings `onnxruntime`, `numpy`, `tokenizers` as transitive deps (~400MB venv)
- `gradio` brings `rich`, `markdown_it`, `pygments`, `huggingface_hub`, `safehttpx`, `groovy`
- `PyPDF2` for PDF parsing (note: scanned PDFs extract poorly, prefer .txt/.docx)
- All LLM calls are raw HTTP — the `openai`/`google-generativeai`/`zhipuai` packages may not be needed at all (most adapters use httpx directly)

---

## 8. Key Architecture Decisions

1. **No orchestration framework.** Agents are pure async functions, not LangChain chains. The orchestrator is ~200 lines of plain Python.

2. **Two-round parallelism.** Round 1 (A1+A2+A3) runs first because A2 and A3 need the document text. Round 2 (A4+A5) waits for Round 1 to complete. This is hardcoded in `orchestrator.py`, not configurable.

3. **Config-driven extensibility.** Adding a new competition type = adding new JSON files under `configs/`. No code changes needed for the agents (they load configs at runtime).

4. **Calibration engine is LLM-free.** Feature extraction, Cohen's d, diff generation all use pure math/regex. Only the "teacher insight" parser (Modes 1/2) calls LLM, and even then, feature mapping is local keyword matching to prevent hallucination.

5. **Sync is fire-and-forget.** `sync.py` uses `asyncio.ensure_future()` — failures don't block the user. The `SYNC_SERVER_URL` in `.env` controls whether sync is active.

6. **All state is local.** SQLite + ChromaDB are file-based. No external database server needed. Data dirs created automatically via `ensure_dirs()`.

7. **Competition-type-aware calibration.** The calibration engine uses different feature sets per competition type: research gets 21 features (including p-value/effect size), discursive gets 15. Fatal defect detection also varies — John Locke will never suggest "missing p-value" as a critical flaw. Agent weights are per-competition in `competition_registry.json` (e.g., John Locke weights Structure at 30%, ISEF weights Evidence at 30%).

8. **Security is opt-in.** Bearer Token auth is available but disabled by default (`API_TOKEN=""`). All `/api/v1/*` endpoints accept a `Depends(_verify_api_token)` parameter that passes through when unconfigured. File uploads validated server-side (50MB cap, extension whitelist).

---

## 9. Common Pitfalls / Gotchas

- **Circular imports:** `orchestrator.py` imports agent classes inside `review()` method body. If you add new imports at module level in orchestrator, you'll hit circular deps with `app.agents.*`.

- **Gradio CSS/theme:** Using `gr.themes.Soft()`. Gradio 6.0+ may warn about constructor params — they've been moved to `launch()`. The warning is cosmetic.

- **ChromaDB embedding:** Uses default `all-MiniLM-L6-v2` ONNX model (~80MB download on first use). If offline, `check_originality()` will be skipped gracefully.

- **Database migrations:** None. `Base.metadata.create_all()` on every startup. Adding columns to existing tables requires manual migration or DB deletion.

- **PDF quality:** `PyPDF2` extracts text well from native PDFs, fails on scanned/image PDFs. Recommend `.txt` or `.docx` for best results.

- **Windows `asyncio`:** The project uses `asyncio.gather()` — ensure `asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())` if running on Windows with subprocess spawn issues (not currently set, may need adding).

- **Configuration sync:** `pull_configs_from_server()` overwrites local `configs/` directory. Old configs are backed up to `data/configs_backup_TIMESTAMP/` before overwrite.

---

## 10. How to Add a New Feature

### Add a new Agent (A6)
1. Create `app/agents/new_agent.py` extending `BaseAgent`
2. Set `agent_name`, `prompt_template_path`
3. Override `_build_user_message()` to format input
4. Create `prompts/a6_new_agent.txt`
5. In `orchestrator.py`, add import (lazy, inside `review()`) and schedule in appropriate round
6. Add weight to `AGENT_WEIGHTS`
7. Add score handling in `_compute_total_score()`
8. Add DB column in `Review` model

### Add a new LLM provider
1. Create `app/llm/new_adapter.py` implementing `LLMAdapter`
2. Implement `chat()`, `model_name()`, `provider_name()`
3. Add `LLMFactory.register("new_provider", NewAdapter)` at module bottom
4. Add API key to `config.py` Settings class
5. Import in `app/llm/__init__.py` (try/except pattern)

### Add a new competition type
1. Use the **"Competition Management"** Gradio tab (visual form, no coding required)
2. Or manually add entry to `configs/competition_registry.json` with required fields:
   - `type`, `structure_schema`, `evidence_config`, `style_template`, `citation_style`
   - `agent_weights` (optional — falls back to `DEFAULT_AGENT_WEIGHTS` if omitted)
   - `aliases` for common alternate names
3. Create corresponding JSON files under `configs/structure_schemas/`, `configs/evidence_patterns/`, `configs/style_guides/`
4. Add type hint entry to `configs/competition_type_hints.json` for A3 reasoning
5. No code changes required — agents, orchestrator, and calibration engine all read from config
6. Unknown competitions gracefully fall back to research type defaults

---

## 11. Documentation Index

| Doc | Language | Audience |
|-----|----------|----------|
| `AI_HANDOFF.md` (this file) | English | AI assistants |
| `README.md` | Chinese | End users, developers |
| `docs/使用指南.html` | Chinese | End users (teachers) |
| `docs/architecture/Agent架构设计方案_v1.5_5Agent专用开发版.md` | Chinese | Developers — **the spec to read first** |
| `docs/architecture/技术方案与执行计划_v1.6.md` | Chinese | Developers — tech stack & implementation plan |
| `docs/测试计划与步骤.md` | Chinese | QA — 49 test cases |
