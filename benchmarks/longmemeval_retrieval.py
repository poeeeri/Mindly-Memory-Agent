from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.memory.embeddings import embed_text


DATASET_URLS = {
    "s": "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_s_cleaned.json",
    "oracle": "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_oracle.json",
}


@dataclass(frozen=True)
class RetrievedSession:
    session_id: str
    score: float
    text: str


def session_to_text(session: list[dict[str, str]]) -> str:
    return "\n".join(
        f"{message.get('role', 'unknown')}: {message.get('content', '')}".strip()
        for message in session
        if message.get("content")
    )


def dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def retrieve_by_memory(
    *,
    question: str,
    session_ids: list[str],
    sessions: list[list[dict[str, str]]],
    top_k: int,
) -> list[RetrievedSession]:
    query_embedding = embed_text(question)
    scored: list[RetrievedSession] = []
    for session_id, session in zip(session_ids, sessions):
        text = session_to_text(session)
        score = dot(query_embedding, embed_text(text))
        scored.append(RetrievedSession(session_id=session_id, score=score, text=text))
    return sorted(scored, key=lambda item: item.score, reverse=True)[:top_k]


def retrieve_by_message_memory(
    *,
    question: str,
    session_ids: list[str],
    sessions: list[list[dict[str, str]]],
    top_k: int,
) -> list[RetrievedSession]:
    query_embedding = embed_text(question)
    scored_messages: list[RetrievedSession] = []
    for session_id, session in zip(session_ids, sessions):
        for message_index, message in enumerate(session):
            content = message.get("content", "")
            if not content:
                continue
            role = message.get("role", "unknown")
            text = f"{role}: {content}"
            score = dot(query_embedding, embed_text(text))
            scored_messages.append(
                RetrievedSession(
                    session_id=session_id,
                    score=score,
                    text=f"{session_id}#{message_index}\n{text}",
                )
            )

    retrieved: list[RetrievedSession] = []
    seen_session_ids: set[str] = set()
    for item in sorted(scored_messages, key=lambda scored: scored.score, reverse=True):
        if item.session_id in seen_session_ids:
            continue
        seen_session_ids.add(item.session_id)
        retrieved.append(item)
        if len(retrieved) == top_k:
            break
    return retrieved


def retrieve_by_recency(
    *,
    session_ids: list[str],
    sessions: list[list[dict[str, str]]],
    top_k: int,
) -> list[RetrievedSession]:
    selected = list(zip(session_ids, sessions))[-top_k:]
    return [
        RetrievedSession(session_id=session_id, score=float(index), text=session_to_text(session))
        for index, (session_id, session) in enumerate(reversed(selected), start=1)
    ]


def score_retrieval(retrieved_ids: list[str], answer_ids: set[str]) -> dict[str, float]:
    if not answer_ids:
        return {"hit": 0.0, "recall": 0.0, "mrr": 0.0}

    retrieved_set = set(retrieved_ids)
    hit = 1.0 if retrieved_set.intersection(answer_ids) else 0.0
    recall = len(retrieved_set.intersection(answer_ids)) / len(answer_ids)
    reciprocal_rank = 0.0
    for rank, session_id in enumerate(retrieved_ids, start=1):
        if session_id in answer_ids:
            reciprocal_rank = 1.0 / rank
            break
    return {"hit": hit, "recall": recall, "mrr": reciprocal_rank}


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "examples": 0,
            "hit_at_k": 0.0,
            "recall_at_k": 0.0,
            "mrr_at_k": 0.0,
            "avg_latency_ms": 0.0,
        }
    return {
        "examples": len(rows),
        "hit_at_k": mean(row["hit"] for row in rows),
        "recall_at_k": mean(row["recall"] for row in rows),
        "mrr_at_k": mean(row["mrr"] for row in rows),
        "avg_latency_ms": mean(row["latency_ms"] for row in rows),
    }


def run_benchmark(dataset: list[dict[str, Any]], *, top_k: int) -> dict[str, Any]:
    strategy_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    type_rows: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))

    for item in dataset:
        answer_ids = set(item["answer_session_ids"])
        strategies = {
            "no_memory": [],
            "recency": retrieve_by_recency(
                session_ids=item["haystack_session_ids"],
                sessions=item["haystack_sessions"],
                top_k=top_k,
            ),
        }

        started = time.perf_counter()
        strategies["memory_session"] = retrieve_by_memory(
            question=item["question"],
            session_ids=item["haystack_session_ids"],
            sessions=item["haystack_sessions"],
            top_k=top_k,
        )
        memory_session_latency_ms = (time.perf_counter() - started) * 1000

        started = time.perf_counter()
        strategies["memory_message"] = retrieve_by_message_memory(
            question=item["question"],
            session_ids=item["haystack_session_ids"],
            sessions=item["haystack_sessions"],
            top_k=top_k,
        )
        memory_message_latency_ms = (time.perf_counter() - started) * 1000

        for strategy, retrieved in strategies.items():
            retrieved_ids = [session.session_id for session in retrieved]
            metrics = score_retrieval(retrieved_ids, answer_ids)
            row = {
                "question_id": item["question_id"],
                "question_type": item["question_type"],
                "hit": metrics["hit"],
                "recall": metrics["recall"],
                "mrr": metrics["mrr"],
                "latency_ms": {
                    "memory_session": memory_session_latency_ms,
                    "memory_message": memory_message_latency_ms,
                }.get(strategy, 0.0),
                "retrieved_ids": retrieved_ids,
                "answer_ids": sorted(answer_ids),
            }
            strategy_rows[strategy].append(row)
            type_rows[strategy][item["question_type"]].append(row)

    summary = {strategy: aggregate(rows) for strategy, rows in strategy_rows.items()}
    by_type = {
        strategy: {question_type: aggregate(rows) for question_type, rows in sorted(groups.items())}
        for strategy, groups in sorted(type_rows.items())
    }
    return {"summary": summary, "by_question_type": by_type}


def download_dataset(split: str, path: Path) -> None:
    url = DATASET_URLS[split]
    path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, path)


def load_dataset(path: Path, *, limit: int | None) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if limit is not None:
        return data[:limit]
    return data


def format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def print_summary(result: dict[str, Any], *, top_k: int) -> None:
    print(f"LongMemEval retrieval benchmark, top_k={top_k}")
    print("strategy      examples  hit@k    recall@k  mrr@k    avg_latency_ms")
    for strategy, row in result["summary"].items():
        print(
            f"{strategy:<12}  {row['examples']:>8}  "
            f"{format_percent(row['hit_at_k']):>7}  "
            f"{format_percent(row['recall_at_k']):>8}  "
            f"{row['mrr_at_k']:.4f}  "
            f"{row['avg_latency_ms']:.2f}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run LongMemEval-S retrieval benchmark.")
    parser.add_argument("--split", choices=sorted(DATASET_URLS), default="s")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data/benchmarks/longmemeval_s_cleaned.json"),
        help="Path to LongMemEval JSON file.",
    )
    parser.add_argument("--download", action="store_true", help="Download dataset if missing.")
    parser.add_argument("--limit", type=int, default=None, help="Limit examples for a smoke run.")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/benchmark_results/longmemeval_s_retrieval.json"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.download and not args.dataset.exists():
        download_dataset(args.split, args.dataset)
    if not args.dataset.exists():
        raise SystemExit(
            f"Dataset not found: {args.dataset}. Run with --download or place the JSON there."
        )

    started = time.perf_counter()
    dataset = load_dataset(args.dataset, limit=args.limit)
    result = run_benchmark(dataset, top_k=args.top_k)
    result["metadata"] = {
        "dataset_path": str(args.dataset),
        "split": args.split,
        "examples": len(dataset),
        "top_k": args.top_k,
        "embedding": "app.memory.embeddings.embed_text hashing encoder",
        "memory_refresh_mode_default": "manual",
        "strategy_notes": {
            "memory_session": "Indexes each LongMemEval session as one memory chunk.",
            "memory_message": "Indexes each message as a separate memory chunk and returns unique sessions.",
        },
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print_summary(result, top_k=args.top_k)
    print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()