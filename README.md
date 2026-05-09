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

## Tests

```bash
pytest
cd client
npm run lint
npm run build
```