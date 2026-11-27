# 10 — NVIDIA NIM Migration Plan

Status: proposed for review. No application code has been changed yet.

## 1. Goal and constraints

Replace Google Gemini with NVIDIA NIM while preserving the existing provider abstraction, workflow,
UI, and tests.

Hard constraints:

- `Classifier`, `SectionGenerator`, `Evaluator`, and workflow node signatures must not change.
- `MockProvider` and `--mock` must keep working without an API key or network access.
- Structured output must remain Pydantic-validated (`ClassificationResult`, `SectionDraft`,
  `EvaluationResult`).
- No streaming or tool calling is required; the UI already reports node-level progress.
- Do not commit secrets or claim free-tier limits beyond NVIDIA's official statement.

## 2. Current Gemini integration inventory

| File | Role | Lines |
|---|---|---|
| `ai/llm/gemini.py` | Gemini provider: client, structured output, text, embeddings | `16-122` |
| `ai/llm/base.py` | `LLMProvider` protocol used by the workflow | `10-33` |
| `ai/llm/mock.py` | Deterministic offline provider | `21-119` |
| `ai/llm/__init__.py` | Exports `GeminiProvider` | `1-5` |
| `ai/__init__.py` | Re-exports `GeminiProvider` | `1-17` |
| `app/settings.py` | Gemini key, model, fallback, embedding, token limit | `20-25`, `45-55` |
| `app/main.py` | CLI provider selection | `17`, `26` |
| `app/ui/workers.py` | GUI provider selection | `11`, `66-69` |
| `app/ui/pages/settings_page.py` | Gemini key/model UI and `.env` write | `37-59`, `115-139` |
| `.env.example` | Gemini environment template | `1-6` |
| `pyproject.toml` | `google-genai` dependency | `14` |
| `tests/test_settings.py` | Asserts Gemini defaults | `7`, `9` |
| `tests/test_imports.py` | Import smoke test | `1-4` |
| `ai/retriever.py` | Uses `llm.embed` for Chroma indexing/query | `47-49`, `72-74` |
| `scripts/index_reference.py` | Indexes references with `MockProvider` | `7`, `30` |
| `README.md`, `docs/STUDENT_GUIDE.md`, `docs/01-09`, `CODE_UNDERSTANDING.md` | Gemini references | multiple |

RAG is disabled in all three category configs (`rag.enabled: false`), so no production vector store
depends on Gemini embeddings today.

## 3. Model selection

NVIDIA API Catalog facts used here:

- Base URL: `https://integrate.api.nvidia.com/v1`
- Auth: `Authorization: Bearer $NVIDIA_API_KEY`
- OpenAI-compatible Chat Completions and Embeddings endpoints.
- Official FAQ: all catalog models offer a free trial tier with no credit card required. Per-model
  rate limits are not published, so no specific quota is assumed.

| Model ID | Context | Structured output | Tools | Notes |
|---|---:|---|---|---|
| `nvidia/nemotron-3.5-lightning-30b-a3b` | 1M | Trained for structured outputs; `response_format` is not listed in the OpenAPI schema, so verify live | Not documented in API schema; not required | 30B total / 3B active, production-intended, strongest reasoning of the candidates |
| `nvidia/nemotron-3.5-bolt-e4b` | 65,536 | `response_format` with `json_schema` and `strict` documented | Supported | 8B total / 4B effective, compact and fast; model card says it is intended primarily for customization/post-training rather than direct production inference |
| `mistralai/mistral-large-4-1t-a52b` | 262,144 | Catalog describes structured outputs; API schema not verified | Supported | 1T total / 52B active; optional quality override, higher latency |

### Recommendation

- Primary: `nvidia/nemotron-3.5-lightning-30b-a3b`
- Fallback: `nvidia/nemotron-3.5-bolt-e4b`
- Optional override: `mistralai/mistral-large-4-1t-a52b`

Why Lightning primary:

- It is the production-intended, general-purpose model in the catalog.
- 1M context comfortably covers the 100,000-character assignment cap plus prompts and references.
- It has the strongest reasoning profile of the three, which matters for academic drafting and rubric
  evaluation.
- It is fast: 3B active parameters.

Why Bolt fallback:

- It has the most reliable documented structured-output path (`response_format: json_schema`,
  `strict: true`).
- 65,536 context is sufficient for normal assignment runs; it is used when Lightning fails or when a
  known-good JSON schema is required.

The provider adapter will make the model choice a setting, so switching to Bolt primary is a one-line
environment change if live testing shows Lightning structured output is unreliable. If guaranteed
native JSON schema is more important than writing quality, choose option B in section 13.

## 4. Target design

### 4.1 New provider

Create `ai/llm/nvidia.py` with `NvidiaProvider(LLMProvider)`.

- Use the official `openai` Python SDK with `base_url=settings.nvidia_base_url`.
- Import `openai` lazily inside `_get_client()` so offline mode and imports work even if the package
  is temporarily missing.
- Client settings: `timeout=settings.nvidia_timeout_seconds`, `max_retries=0` (the provider owns the
  fallback policy).
- No hardcoded model IDs in the provider; only settings.

### 4.2 Structured output strategy

`generate_structured(schema, system_prompt, user_prompt, temperature)`:

1. Build messages: `system` + `user`.
2. For each model in `[primary, fallback]`:
   - Attempt native structured output:
     `response_format={"type": "json_schema", "json_schema": {"name": schema.__name__,
     "strict": True, "schema": schema.model_json_schema()}}`.
   - Send `chat_template_kwargs.enable_thinking=false` for structured calls when the model accepts
     it, to avoid empty or truncated JSON.
   - Parse `choices[0].message.content`; strip Markdown fences; validate with
     `schema.model_validate_json(...)`.
   - If the endpoint rejects `response_format` (400/422) or returns empty/invalid JSON, retry the
     same model without `response_format` using a JSON-only instruction and the schema text.
   - If validation still fails, make one repair request containing the validation error and the
     invalid output, asking for corrected JSON only.
3. If all attempts fail, raise `RuntimeError` naming the models and the last error.

This keeps the native fast path for Bolt and gives Lightning a documented fallback path. The adapter
is model-agnostic, so future models only need a settings change.

### 4.3 Text generation strategy

`generate_text(system_prompt, user_prompt, temperature)`:

- Call `chat.completions.create` with `max_tokens=settings.nvidia_max_output_tokens`.
- Use `settings.nvidia_enable_thinking` (default `false`) via `chat_template_kwargs`.
- If the response has empty `content` but a `reasoning_content` trace, retry once with thinking
  disabled.
- Try the fallback model on transport/API errors.

### 4.4 Embeddings strategy

`embed(texts, input_type="passage")`:

- Call `client.embeddings.create` with:
  - `model=settings.nvidia_embedding_model`
  - `input=texts`
  - `dimensions=settings.nvidia_embedding_dimensions` (omit when `0`)
  - `encoding_format="float"`
  - `extra_body={"input_type": input_type, "truncate": "END"}`
- Return `[item.embedding for item in response.data]`.
- Add the optional `input_type` keyword to the `LLMProvider` protocol and to `MockProvider` (ignored)
  so `RagRetriever.retrieve` can request a query embedding. This is backward-compatible for callers.

### 4.5 Provider factory

Create `ai/llm/factory.py`:

```python
def build_llm_provider(use_mock: bool = False) -> LLMProvider:
    if use_mock or not settings.nvidia_api_key_str:
        return MockProvider()
    return NvidiaProvider()
```

Use it in `app/main.py`, `app/ui/workers.py`, and `scripts/index_reference.py` to remove duplicated
selection logic and keep RAG indexing on the same embedding model as retrieval.

## 5. Files to modify, create, and remove

### Create

| File | Purpose |
|---|---|
| `ai/llm/nvidia.py` | NVIDIA NIM provider |
| `ai/llm/factory.py` | Shared provider selection |
| `tests/unit/test_nvidia_provider.py` | Mocked unit tests for the new provider |
| `tests/integration/test_nvidia_live.py` | Opt-in live smoke test, skipped without `NVIDIA_API_KEY` |
| `docs/10_NVIDIA_NIM_MIGRATION_PLAN.md` | This plan |

### Modify

| File | Change |
|---|---|
| `ai/llm/base.py` | Add optional `input_type` to `embed` |
| `ai/llm/mock.py` | Accept and ignore `input_type` |
| `ai/llm/__init__.py` | Export `NvidiaProvider`, `build_llm_provider`; stop exporting Gemini |
| `ai/__init__.py` | Same exports |
| `app/settings.py` | Add `nvidia_*` settings; remove `gemini_*` in the cleanup step |
| `app/main.py` | Use `build_llm_provider` |
| `app/ui/workers.py` | Use `build_llm_provider` |
| `app/ui/pages/settings_page.py` | NVIDIA key/model fields; write `NVIDIA_*`; fix `.env` path |
| `.env.example` | Replace Gemini variables with NVIDIA variables |
| `pyproject.toml` | Add `openai`; remove `google-genai` in the cleanup step |
| `tests/test_settings.py` | Assert NVIDIA defaults |
| `tests/test_imports.py` | Import `NvidiaProvider` / factory |
| `ai/retriever.py` | Pass `input_type="query"` for retrieval |
| `scripts/index_reference.py` | Use `build_llm_provider` instead of hardcoded `MockProvider` |
| `README.md`, `docs/STUDENT_GUIDE.md` | NVIDIA key instructions |
| `docs/01-09`, `CODE_UNDERSTANDING.md` | Update provider references after the code is stable |

### Remove

| File | When |
|---|---|
| `ai/llm/gemini.py` | Cleanup step, after the NVIDIA path passes tests and a live smoke test |
| `google-genai` from `pyproject.toml` | Same cleanup step |
| `GEMINI_*` settings and `.env.example` entries | Same cleanup step |

## 6. Environment and settings changes

New `.env.example` block:

```env
NVIDIA_API_KEY=nvapi-your-key
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=nvidia/nemotron-3.5-lightning-30b-a3b
NVIDIA_FALLBACK_MODEL=nvidia/nemotron-3.5-bolt-e4b
NVIDIA_MAX_OUTPUT_TOKENS=8192
NVIDIA_TIMEOUT_SECONDS=60
NVIDIA_ENABLE_THINKING=false
NVIDIA_EMBEDDING_MODEL=nvidia/nemotron-3.5-embed-1b
NVIDIA_EMBEDDING_DIMENSIONS=1024
```

Keep `GOOGLE_OAUTH_*`, `PDF_*`, `LOG_LEVEL`, and `STORAGE_DIR` unchanged.

Settings additions in `app/settings.py`:

- `nvidia_api_key: SecretStr`
- `nvidia_base_url: str`
- `nvidia_model: str`
- `nvidia_fallback_model: str`
- `nvidia_max_output_tokens: int`
- `nvidia_timeout_seconds: int`
- `nvidia_enable_thinking: bool`
- `nvidia_embedding_model: str`
- `nvidia_embedding_dimensions: int`
- `nvidia_api_key_str` property and `require_nvidia_key()`.

Provider-side clamping:

- Lightning `max_tokens` maximum is 32768; Bolt is 65536. Clamp the configured value to the model
  limit to avoid API errors.
- Keep the default at 8192 to preserve current output sizes.

Settings page changes:

- Label the field "NVIDIA NIM API Key".
- Model choices: Lightning, Bolt, Mistral Large 4.
- Write `NVIDIA_API_KEY`, `NVIDIA_MODEL`, and `PDF_ENGINE` to the project-root `.env`.
- Fix the existing path bug: `app/ui/pages/settings_page.py` currently resolves to `app/.env`, not the
  project-root `.env` that `app/settings.py` loads.
- Upsert keys instead of only replacing lines that already exist.
- Keep the current plaintext `.env` behavior for this migration; moving the key to `keyring` is a
  separate security improvement.

## 7. Embedding compatibility assessment

Current state:

- Gemini path uses `gemini-embedding-001`.
- Mock path uses 768-dimensional SHA-256 pseudo-vectors.
- RAG is disabled in every category config.
- No application code depends on a persisted production vector store today.

NVIDIA path:

- `nvidia/nemotron-3.5-embed-1b` returns 2048-dimensional vectors natively and supports
  `dimensions` from 128 to 2048.
- It requires `input_type`: `passage` for indexing and `query` for retrieval. Using the wrong mode
  materially reduces retrieval accuracy.
- Maximum input is 10,240 tokens; `truncate=END` is safe for long chunks.

Plan:

- Default to 1024 dimensions for storage efficiency, configurable through
  `NVIDIA_EMBEDDING_DIMENSIONS`.
- Add `input_type` to the provider contract and pass `"query"` from `RagRetriever.retrieve`.
- Changing embedding model or dimensions invalidates existing Chroma collections. Because RAG is
  disabled, there is no production impact; if `storage/rag` exists from earlier experiments, delete
  it or reindex with the NVIDIA provider before enabling RAG.
- Update `scripts/index_reference.py` to use the same provider factory so indexed vectors and query
  vectors come from the same model.

Compatibility conclusion: the migration is safe for current behavior. Enabling RAG after migration
requires a one-time reindex, not a schema change.

## 8. Test plan

### Unit tests, no network

`tests/unit/test_nvidia_provider.py` with a mocked `openai.OpenAI` client:

- Structured output with native `response_format` returns a validated Pydantic model.
- Structured output falls back to prompt-JSON when the endpoint rejects `response_format`.
- Invalid JSON triggers one repair retry and then validates.
- Primary model failure falls through to the fallback model.
- Text generation returns `choices[0].message.content`.
- Empty content with `reasoning_content` retries with thinking disabled.
- Embeddings send `model`, `dimensions`, `input_type`, and `truncate`; response vectors are returned.
- Missing API key raises a clear `ValueError`.

### Settings and factory tests

- `Settings(_env_file=None)` uses the NVIDIA defaults.
- `build_llm_provider(use_mock=True)` returns `MockProvider`.
- `build_llm_provider(use_mock=False)` returns `MockProvider` when no key is configured.
- `build_llm_provider(use_mock=False)` returns `NvidiaProvider` when a key is configured.
- `test_imports.py` imports the new provider and factory without `google-genai`.

### Existing tests

- `tests/integration/test_workflow.py` and `tests/unit/test_rag.py` continue to pass with
  `MockProvider`.
- UI smoke test still loads the settings page.

### Opt-in live smoke test

`tests/integration/test_nvidia_live.py`, skipped unless `NVIDIA_API_KEY` is set:

- One `ClassificationResult` call.
- One short `SectionDraft` call.
- One `EvaluationResult` call.
- One embedding call with both `passage` and `query`.
- Verify `response_format` behavior on Lightning and Bolt; log which path succeeded.

### Commands

```powershell
uv sync
uv run pytest
uv run ruff check .
uv run mypy .
```

Live smoke:

```powershell
$env:NVIDIA_API_KEY="nvapi-..."
uv run pytest tests/integration/test_nvidia_live.py -m live -s
```

If `mypy` is not part of the project's normal workflow, keep it advisory.

## 9. Implementation sequence

Each step should leave the application runnable and tests passing.

1. **Settings and dependency.** Add `nvidia_*` settings, `openai` dependency, and update
   `.env.example`. Keep Gemini settings and provider working for rollback.
2. **Provider implementation.** Add `ai/llm/nvidia.py` and mocked unit tests. Do not switch runtime
   selection yet.
3. **Factory and runtime switch.** Add `ai/llm/factory.py`; switch `app/main.py` and
   `app/ui/workers.py` to it; update exports. Run the test suite.
4. **Settings page.** Replace Gemini fields with NVIDIA fields, fix the `.env` path, upsert keys, and
   update UI tests.
5. **Embeddings.** Extend the protocol and `MockProvider` with `input_type`; update
   `RagRetriever` and `scripts/index_reference.py`. Run RAG tests.
6. **Cleanup.** Remove `ai/llm/gemini.py`, Gemini exports/settings, and `google-genai`; update
   `README.md`, `docs/STUDENT_GUIDE.md`, and provider references in docs.
7. **Live validation.** Run the opt-in live test against both models. If Lightning structured output
   is unreliable, flip the default to Bolt primary and Lightning fallback.
8. **Final verification.** Run the full suite, `ruff`, and a manual CLI/GUI smoke test.

## 10. Remaining limitations and risks

- NVIDIA's free trial is official, but per-model quotas and rate limits are not published. Handle
  429 responses with backoff and surface a clear error.
- Lightning's OpenAPI schema does not document `response_format`, even though the model was trained
  for structured outputs. The adapter's prompt-JSON fallback covers this; live validation decides the
  default model.
- Bolt's model card says it is intended primarily for customization/post-training, not direct
  production inference. It is a good fallback but not the preferred primary for quality.
- Bolt's 65,536 context may be exceeded by very large reference contexts. Lightning's 1M context is
  the fallback.
- Pydantic JSON schemas with `$defs` and defaults may be rejected by strict `json_schema` mode on
  some models. The adapter falls back to prompt-JSON if that happens.
- Structured output is probabilistic even with schema enforcement; validation and one repair retry
  reduce but do not eliminate failures.
- The settings page still writes the API key to `.env` in plaintext. Moving it to `keyring` is a
  follow-up security improvement.
- Model IDs can change or be deprecated. All IDs live in settings, not code.
- The models are English-centric. Verify quality if the app is used for other languages.
- No streaming is added; the UI continues to show node-level progress only.
- No usage/token accounting is added in this migration. The existing technical debt remains.

## 11. Configure and run

1. Create an NVIDIA API key at `https://build.nvidia.com/settings`.
2. Install dependencies:

   ```powershell
   uv sync
   ```

3. Copy `.env.example` to `.env` and set:

   ```env
   NVIDIA_API_KEY=nvapi-...
   ```

4. Optional model override:

   ```env
   NVIDIA_MODEL=nvidia/nemotron-3.5-bolt-e4b
   NVIDIA_FALLBACK_MODEL=nvidia/nemotron-3.5-lightning-30b-a3b
   ```

5. Offline smoke test (no key needed):

   ```powershell
   uv run python -m app.main --mock --cli --title "Smoke" --prompt "Ohm's law"
   ```

6. Live CLI test:

   ```powershell
   uv run python -m app.main --cli --title "Ohm's Law" --prompt "Discuss Ohm's law and calculate current for V=12V, R=4 ohms."
   ```

7. GUI:

   ```powershell
   uv run python -m app.main
   ```

8. Tests:

   ```powershell
   uv run pytest
   uv run ruff check .
   ```

## 12. Rollback

- Before step 6, Gemini remains available: restore `GeminiProvider` in `app/main.py` and
  `app/ui/workers.py`, and set `GEMINI_API_KEY`.
- After step 6, rollback means reverting the cleanup commit; no database migration is involved.
- No persisted data changes are required. If RAG was enabled, reindex after switching embedding
  providers.

## 13. Approval checklist

Please confirm before implementation:

- [ ] Model choice: A) Lightning primary, Bolt fallback (recommended), or B) Bolt primary,
      Lightning fallback for maximum native JSON-schema reliability.
- [ ] Embedding dimensions: 1024 (recommended) or native 2048.
- [ ] Remove Gemini code and `google-genai` in the same migration, or keep them for one release.
- [ ] Keep the settings page writing the key to `.env` for now, or move it to `keyring` as part of
      this work.
