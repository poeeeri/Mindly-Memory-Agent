from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.memory.embeddings import embed_text
from app.memory.extractor import normalize_sentence, terms
from app.memory.models import MemoryFact

FACTS_ROOM = "facts"
FORBIDDEN_TOPICS_ROOM = "forbidden_topics"


class MemPalaceMemory:
    """MemPalace/Chroma-backed implementation of the MemoryStore contract."""

    def __init__(self, *, palace_path: str, collection_name: str = "mindly_memory_facts") -> None:
        from mempalace.palace import get_collection

        self.palace_path = str(Path(palace_path))
        self.collection_name = collection_name
        Path(self.palace_path).mkdir(parents=True, exist_ok=True)
        self._collection = get_collection(
            self.palace_path,
            collection_name=self.collection_name,
            create=True,
        )

    def search(self, user_id: str, query: str) -> list[str]:
        if not query.strip():
            return [fact.text for fact in self.list_facts(user_id)[-5:]]

        result = self._collection.query(
            query_embeddings=[embed_text(query)],
            n_results=5,
            where={"user_id": user_id},
            include=["documents", "metadatas", "distances"],
        )
        documents = result.documents[0] if result.documents else []
        return [document for document in documents if document]

    def add(self, user_id: str, text: str) -> None:
        self.add_fact(user_id=user_id, fact_text=text)

    def add_fact(self, user_id: str, fact_text: str, source: str = "user_message") -> None:
        fact_text = normalize_sentence(fact_text)
        if not fact_text:
            return
        existing_texts = {fact.text for fact in self.list_facts(user_id)}
        if fact_text in existing_texts:
            return

        now = datetime.now(timezone.utc).isoformat()
        self._collection.upsert(
            documents=[fact_text],
            ids=[str(uuid4())],
            metadatas=[
                {
                    "user_id": user_id,
                    "source": source,
                    "created_at": now,
                    "wing": user_id,
                    "room": FACTS_ROOM,
                }
            ],
            embeddings=[embed_text(fact_text)],
        )

    def add_forbidden_topic(self, user_id: str, topic: str) -> bool:
        topic = normalize_sentence(topic)
        if not topic:
            return False
        if topic in self.list_forbidden_topics(user_id):
            return False

        now = datetime.now(timezone.utc).isoformat()
        self._collection.upsert(
            documents=[topic],
            ids=[str(uuid4())],
            metadatas=[
                {
                    "user_id": user_id,
                    "source": "forbidden_topic",
                    "created_at": now,
                    "wing": user_id,
                    "room": FORBIDDEN_TOPICS_ROOM,
                }
            ],
            embeddings=[embed_text(topic)],
        )
        return True

    def list_forbidden_topics(self, user_id: str) -> list[str]:
        result = self._collection.get(
            where={"user_id": user_id},
            include=["documents", "metadatas"],
        )
        return [
            document
            for document, metadata in zip(result.documents, result.metadatas)
            if document and metadata.get("room") == FORBIDDEN_TOPICS_ROOM
        ]

    def forget(self, user_id: str, query: str) -> int:
        query_terms = terms(query)
        if not query_terms:
            return 0

        facts = self.list_facts(user_id)
        ids_to_delete = [
            fact.id for fact in facts if query_terms.intersection(terms(fact.text))
        ]
        if not ids_to_delete:
            return 0
        self._collection.delete(ids=ids_to_delete)
        return len(ids_to_delete)

    def forget_all(self, user_id: str) -> int:
        result = self._collection.get(where={"user_id": user_id})
        count = len(result.ids)
        if result.ids:
            self._collection.delete(where={"user_id": user_id})
        return count

    def list_facts(self, user_id: str) -> list[MemoryFact]:
        result = self._collection.get(
            where={"user_id": user_id},
            include=["documents", "metadatas"],
        )
        facts: list[MemoryFact] = []
        for fact_id, document, metadata in zip(result.ids, result.documents, result.metadatas):
            if metadata.get("room", FACTS_ROOM) != FACTS_ROOM:
                continue
            facts.append(
                MemoryFact(
                    id=fact_id,
                    user_id=metadata.get("user_id", user_id),
                    text=document,
                    source=metadata.get("source", "unknown"),
                    created_at=self._parse_datetime(metadata.get("created_at")),
                )
            )
        return facts

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime:
        if not value:
            return datetime.now(timezone.utc)
        return datetime.fromisoformat(value)