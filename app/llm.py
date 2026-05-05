import asyncio
import json
from collections.abc import AsyncIterator
import httpx
import logging

from app.config import Settings
from app.state import ChatMessage

logger = logging.getLogger(__name__)


class OpenRouterError(RuntimeError):
    def __init__(self, *, status_code: int | None, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        status = f"HTTP {status_code}" if status_code else "request error"
        super().__init__(f"OpenRouter {status}: {detail}")


class OpenRouterClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def model_name(self) -> str:
        return self._settings.openrouter_model

    @property
    # список моделей для fallback
    def model_chain(self) -> list[str]:
        fallback_models = [
            model.strip()
            for model in self._settings.openrouter_fallback_models.split(",")
            if model.strip()
        ]
        return list(dict.fromkeys([self._settings.openrouter_model, *fallback_models]))

    async def stream_chat(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        """
        проверка апи ключа и проход циклом в поисках действительной модели до тех
        пор, пока fallback-модели не кончатся -> error
        """
        if self._settings.use_fake_llm:
            async for chunk in self._fake_stream(messages):
                yield chunk
            return

        if not self._settings.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY is required unless USE_FAKE_LLM=true.")

        last_error: OpenRouterError | None = None
        for model in self.model_chain:
            try:
                async for chunk in self._stream_chat_with_model(model, messages):
                    yield chunk
                return
            except OpenRouterError as exc:
                last_error = exc
                logger.warning("openrouter.model_failed model=%s status=%s detail=%s", model, exc.status_code, exc.detail)

        if last_error:
            raise last_error
        raise OpenRouterError(status_code=None, detail="No OpenRouter models configured.")

    async def _stream_chat_with_model(
        self,
        model: str,
        messages: list[ChatMessage],
    ) -> AsyncIterator[str]:

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self._settings.openrouter_api_key}",
            "HTTP-Referer": self._settings.openrouter_referer,
            "X-OpenRouter-Title": self._settings.openrouter_app_title,
            "X-Title": self._settings.openrouter_app_title,
            "Content-Type": "application/json",
        }
        url = f"{self._settings.openrouter_base_url.rstrip('/')}/chat/completions"
        async with httpx.AsyncClient(timeout=60) as client:
            try:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    if response.status_code >= 400:
                        body = await response.aread()
                        raise OpenRouterError(
                            status_code=response.status_code,
                            detail=self._extract_error_detail(body),
                        )

                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line.removeprefix("data: ").strip()
                        if data == "[DONE]":
                            break
                        chunk = json.loads(data)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content
            except httpx.HTTPError as exc:
                raise OpenRouterError(status_code=None, detail=str(exc)) from exc

    async def complete_chat(self, messages: list[ChatMessage]) -> str:
        """
        собирает стриминг в один целостный ответ, когда нужен сразу, а не по токенам
        """
        chunks = [chunk async for chunk in self.stream_chat(messages)]
        return "".join(chunks)

    async def _fake_stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        """
        тест стриминга без апи
        """
        user_message = next((msg["content"] for msg in reversed(messages) if msg["role"] == "user"), "")
        text = f"Я рядом. Давай разберем это спокойно: {user_message}"
        for token in text.split(" "):
            await asyncio.sleep(0.01)
            yield token + " "

    @staticmethod
    def _extract_error_detail(body: bytes) -> str:
        if not body:
            return "empty error response"
        text = body.decode("utf-8", errors="replace")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return text[:500]

        error = payload.get("error", payload)
        if isinstance(error, dict):
            message = error.get("message") or error.get("detail") or str(error)
            code = error.get("code")
            return f"{message} (code: {code})" if code else str(message)
        return str(error)