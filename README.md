# Mindly Memory Agent

MVP of a conversational agent with persistent long-term memory. The first slice is:

```text
WebUI -> FastAPI -> LangGraph -> OpenRouter -> streaming response
```

Long-term storage can run in two modes:

- `MEMORY_BACKEND=fact`: in-process `FactMemory`, useful for fast tests.
- `MEMORY_BACKEND=mempalace`: persistent MemPalace/Chroma storage under `MEMPALACE_PATH`.

`DummyMemory` remains as a backwards-compatible alias in tests and imports.

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Set `OPENROUTER_API_KEY` in `.env`, then run:

```bash
cd client
npm install
npm run build
cd ..
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

To run the app and PostgreSQL in Docker:

```bash
docker compose up --build
```

The app is available at `http://127.0.0.1:8000`. In compose, chat history uses
PostgreSQL automatically through the internal service URL
`postgresql://mindly:mindly@postgres:5432/mindly`.

For frontend development, run FastAPI on `8000` and Vite separately:

```bash
cd client
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/chat`, `/memory`, `/health`, and `/app-config` to FastAPI.

For a local smoke test without OpenRouter, set:

```text
USE_FAKE_LLM=true
```

By default, long-term memory extraction is explicit and cheap:

```text
MEMORY_REFRESH_MODE=manual
```

Use `POST /memory/refresh` or the UI `Update memory` button to persist new
facts. For experiments you can set `MEMORY_REFRESH_MODE=every_message`, but it
adds an extra fact-extraction step after every chat response.

The default OpenRouter model is `google/gemini-2.5-flash`: it is paid, but relatively inexpensive and fast. You can switch it in `.env` through `OPENROUTER_MODEL`.

## Demo flow

1. Send: `У меня сын Костик, он недавно пошел в школу.`
2. Click `Память` to inspect extracted facts.
3. Send: `Что ты помнишь обо мне?`
4. Send: `Забудь, что у меня есть сын Костик.`
5. Send: `Что ты помнишь обо мне?`


Memory records are stored as structured facts:

```json
{
  "id": "...",
  "user_id": "demo_user",
  "text": "У пользователя есть сын Костик.",
  "source": "user_message",
  "created_at": "..."
}
```

Short-term chat history is separate from long-term memory:

- `GET /chat/history?user_id=...` returns the current dialog history.
- `DELETE /chat/history?user_id=...` clears only the current dialog.
- `POST /chat/new?user_id=...` starts a new chat by clearing only dialog history.
- `DELETE /memory/all?user_id=...` clears only long-term facts.

By default chat history is kept in memory for fast local tests. To persist it in
PostgreSQL, start the database and switch the history backend:

```bash
docker compose up -d postgres
```

```text
CHAT_HISTORY_BACKEND=postgres
CHAT_HISTORY_MAX_MESSAGES=0
DATABASE_URL=postgresql://mindly:mindly@127.0.0.1:5432/mindly
```

The initial table is defined in `db/init.sql`. The app also runs
`CREATE TABLE IF NOT EXISTS` on startup when the PostgreSQL backend is enabled.
Set `CHAT_HISTORY_MAX_MESSAGES` to a positive number if you want to keep only
the latest N messages per user.

## Long-term memory benchmark

The repository includes a LongMemEval-S retrieval benchmark runner for the
long-term memory layer. It downloads the public cleaned LongMemEval-S split,
indexes each candidate session with the same local hashing encoder used by the
MemPalace/Chroma backend, and compares:

- `no_memory`: no long-term memory context.
- `recency`: the latest `top_k` sessions.
- `memory_session`: vector retrieval where each session is indexed as one
  memory chunk.
- `memory_message`: vector retrieval where each message is indexed as a
  separate memory chunk and mapped back to its session. This approximates more
  frequent memory updates.

Download and run:

```bash
python benchmarks/longmemeval_retrieval.py --download --top-k 5
```

The dataset is stored under `data/benchmarks/`, which is ignored by git. The
latest checked-in result is in
`docs/benchmark_results/longmemeval_s_retrieval.json`.

Current LongMemEval-S result (`500` examples, `top_k=5`):

| Strategy | Hit@5 | Recall@5 | MRR@5 | Avg retrieval latency |
| --- | ---: | ---: | ---: | ---: |
| no_memory | 0.00% | 0.00% | 0.0000 | 0.00 ms |
| recency | 23.60% | 13.58% | 0.1047 | 0.00 ms |
| memory_session | 59.40% | 46.33% | 0.4194 | 615.28 ms |
| memory_message | 78.20% | 64.66% | 0.6306 | 641.93 ms |

This benchmark measures retrieval quality, not LLM answer generation quality.

## Tests

```bash
pytest
cd client
npm run lint
npm run build
```