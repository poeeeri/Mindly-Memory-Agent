from app.config import Settings
from app.llm import OpenRouterClient
from app.memory.base import MemoryStore
from app.memory.extractor import FactExtractor, LLMFactExtractor
from app.memory.mempalace_memory import MemPalaceMemory
from app.memory.service import FactMemory


def build_memory(settings: Settings) -> MemoryStore:
    backend = settings.memory_backend.strip().lower()
    if backend == "fact":
        return FactMemory()
    if backend == "mempalace":
        return MemPalaceMemory(
            palace_path=settings.mempalace_path,
            collection_name=settings.mempalace_collection,
        )
    raise ValueError(f"Unsupported MEMORY_BACKEND={settings.memory_backend!r}")


def build_fact_extractor(settings: Settings, llm: OpenRouterClient) -> FactExtractor:
    extractor = settings.fact_extractor.strip().lower()
    if extractor == "llm":
        return LLMFactExtractor(llm=llm)
    raise ValueError(f"Unsupported FACT_EXTRACTOR={settings.fact_extractor!r}")