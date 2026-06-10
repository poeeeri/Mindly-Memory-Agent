from app.config import Settings
from app.llm import OpenRouterClient
from app.memory.base import MemoryStore
from app.memory.extractor import FactExtractor, LLMFactExtractor
from app.memory.mempalace_memory import MemPalaceMemory

# это была заглушка для тестового запуска, пока не готов mempalace, быстро рассказать 
from app.memory.service import FactMemory 


def build_memory(settings: Settings) -> MemoryStore:
    backend = settings.memory_backend.strip().lower()
    if backend == "fact":
        return FactMemory()
    if backend == "mempalace":
        # рассказать про фреймворк (https://www.mempalace.net/what-is-mempalace) 
        # для векторного хранилища, который позволяет легко менять бэкенд 
        # (хотя сейчас поддерживает только chromaDb)
        return MemPalaceMemory(
            palace_path=settings.mempalace_path,
            collection_name=settings.mempalace_collection,
        )
    raise ValueError(f"Unsupported MEMORY_BACKEND={settings.memory_backend!r}")


# рассказать про то, как извлекаются факты, 
# что такое LLMFactExtractor и как он работает
def build_fact_extractor(settings: Settings, llm: OpenRouterClient) -> FactExtractor:
    extractor = settings.fact_extractor.strip().lower()
    if extractor == "llm":
        return LLMFactExtractor(llm=llm)
    raise ValueError(f"Unsupported FACT_EXTRACTOR={settings.fact_extractor!r}")