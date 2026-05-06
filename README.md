# Mindly Memory Agent

MVP of a conversational agent with persistent long-term memory. The first slice is:

```text
WebUI -> FastAPI -> LangGraph -> OpenRouter -> streaming response
```

Long-term storage is currently represented by in-process `FactMemory`, so the agent architecture is ready for MemPalace/Chroma without blocking on infrastructure. `DummyMemory` remains as a backwards-compatible alias in tests and imports.

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Set `OPENROUTER_API_KEY` in `.env`, then run:

```bash
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

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

## Tests

```bash
pytest
```
