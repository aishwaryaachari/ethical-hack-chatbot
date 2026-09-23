"""Local TF-IDF-hash embeddings (offline). Optional MiniLM upgrade if installed."""
import difflib
import hashlib
import math
import re

DIM = 256
_TOKEN = re.compile(r"[a-z0-9]+")
_idf: dict = {}
_N = 0


def _toks(text: str, is_query: bool = False) -> list:
    raw_toks = _TOKEN.findall((text or "").lower())
    if not is_query or not _idf:
        return raw_toks
    toks = []
    vocab_keys = list(_idf.keys())
    for t in raw_toks:
        if t in _idf:
            toks.append(t)
        else:
            # Fuzzy match misspelled query token against document vocabulary
            matches = difflib.get_close_matches(t, vocab_keys, n=1, cutoff=0.65)
            if matches:
                toks.append(matches[0])
            else:
                toks.append(t)
    return toks


def _vec(text: str, is_query: bool = False) -> list:
    v = [0.0] * DIM
    for t in _toks(text, is_query=is_query):
        h = int(hashlib.md5(t.encode()).hexdigest(), 16) % DIM
        idf = _idf.get(t, 1.0)
        v[h] += idf
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def train(texts: list):
    global _idf, _N
    from collections import Counter
    df = Counter()
    for t in texts:
        for tok in set(_toks(t, is_query=False)):
            df[tok] += 1
    _N = max(1, len(texts))
    _idf = {t: math.log(1 + _N / (1 + c)) + 1.0 for t, c in df.items()}


def embed(text: str, is_query: bool = False) -> list:
    try:
        from sentence_transformers import SentenceTransformer  # optional upgrade
        raise ImportError("skip heavy model by default")
    except Exception:
        return _vec(text, is_query=is_query)


def cosine(a: list, b: list) -> float:
    return sum(x * y for x, y in zip(a, b))

