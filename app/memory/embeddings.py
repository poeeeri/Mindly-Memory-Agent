import hashlib
import math
import re


EMBEDDING_DIM = 384


def embed_text(text: str, dimensions: int = EMBEDDING_DIM) -> list[float]:
    vector = [0.0] * dimensions
    tokens = _tokens(text)
    features = tokens + _char_ngrams(" ".join(tokens), size=3)
    if not features:
        return vector

    for feature in features:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "little") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def _tokens(text: str) -> list[str]:
    return re.findall(r"[\w']{2,}", text.lower(), flags=re.UNICODE)


def _char_ngrams(text: str, *, size: int) -> list[str]:
    compact = re.sub(r"\s+", " ", text.lower()).strip()
    if len(compact) < size:
        return []
    return [compact[index : index + size] for index in range(len(compact) - size + 1)]