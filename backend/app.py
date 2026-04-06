"""Recommendation API with stronger retrieval.

Implements roadmap improvements:
- exposes recommendation logic behind an HTTP API
- allows the UI to request recommendations instead of using in-file mock state
- upgrades ranking from simple tag-overlap to vector similarity retrieval
"""Minimal recommendation API (standard-library only).

Implements change #1 from roadmap:
- exposes recommendation logic behind an HTTP API
- allows the UI to request recommendations instead of using in-file mock state
"""

from __future__ import annotations

import difflib
import json
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import List
from urllib.parse import parse_qs, urlparse

try:
    # Preferred semantic retrieval.
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    SentenceTransformer = None

try:
    # Fallback retrieval if sentence-transformers is unavailable.
    from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
    from sklearn.metrics.pairwise import cosine_similarity  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    TfidfVectorizer = None
    cosine_similarity = None


@dataclass(frozen=True)
class Song:
    artist: str
    title: str
    lyrics_snippet: str
    tags: tuple[str, ...]


CATALOG: List[Song] = [
    Song("The Handsome Family", "Blindman", "dark folk storytelling about uncertain roads", ("folk", "dark", "story")),
    Song("Nick Drake", "River Man", "acoustic melancholy with poetic introspection", ("folk", "acoustic", "melancholy")),
    Song("Tom Waits", "Hold On", "gritty blues ballad about resilience and hope", ("blues", "gritty", "story")),
    Song(
        "Leonard Cohen",
        "Famous Blue Raincoat",
        "poetic confession and memory in a reflective tone",
        ("poetic", "folk", "melancholy"),
    ),
    Song("Bob Dylan", "Shelter from the Storm", "classic folk narrative with protective imagery", ("folk", "story", "classic")),
    Song("Coldplay", "Yellow", "romantic melodic anthem with bright emotional tone", ("pop", "romantic", "melodic")),
    Song("Coldplay", "Shiver", "alternative pop yearning and emotional vulnerability", ("pop", "melodic", "alt")),
    Song("Snow Patrol", "Chasing Cars", "slow emotional anthem about presence and connection", ("pop", "emotional", "anthem")),
    Song("Keane", "Somewhere Only We Know", "nostalgic piano pop about shared places and memory", ("pop", "piano", "nostalgic")),
    Song("The Fray", "How to Save a Life", "emotional piano-driven reflection and guidance", ("pop", "piano", "emotional")),
]


def _build_text(song: Song) -> str:
    tags_text = " ".join(song.tags)
    return f"{song.title} {song.artist} {song.lyrics_snippet} {tags_text}"


    Song("The Handsome Family", "Blindman", ("folk", "dark", "story")),
    Song("Nick Drake", "River Man", ("folk", "acoustic", "melancholy")),
    Song("Tom Waits", "Hold On", ("blues", "gritty", "story")),
    Song("Leonard Cohen", "Famous Blue Raincoat", ("poetic", "folk", "melancholy")),
    Song("Bob Dylan", "Shelter from the Storm", ("folk", "story", "classic")),
    Song("Coldplay", "Yellow", ("pop", "romantic", "melodic")),
    Song("Coldplay", "Shiver", ("pop", "melodic", "alt")),
    Song("Snow Patrol", "Chasing Cars", ("pop", "emotional", "anthem")),
    Song("Keane", "Somewhere Only We Know", ("pop", "piano", "nostalgic")),
    Song("The Fray", "How to Save a Life", ("pop", "piano", "emotional")),
]


def _normalize(text: str) -> str:
    return " ".join("".join(ch.lower() if ch.isalnum() or ch.isspace() else " " for ch in text).split())


def _match_title(query: str) -> tuple[Song | None, bool]:
    titles = [song.title for song in CATALOG]
    clean_query = _normalize(query)

    exact = next((song for song in CATALOG if _normalize(song.title) == clean_query), None)
    if exact:
        return exact, False

    fuzzy = difflib.get_close_matches(query, titles, n=1, cutoff=0.55)
    if not fuzzy:
        return None, False

    matched_title = fuzzy[0]
    return next(song for song in CATALOG if song.title == matched_title), True


class Retriever:
    """Vector-based retrieval with optional semantic embeddings.

    Mode priority:
    1) sentence-transformers embeddings (semantic)
    2) TF-IDF + cosine similarity (fallback)
    """

    def __init__(self, songs: List[Song]) -> None:
        self.songs = songs
        self.documents = [_build_text(song) for song in songs]
        self.mode = "none"
        self.embeddings = None
        self.vectorizer = None
        self.tfidf_matrix = None
        self.vocab = None
        self.idf = None
        self.lite_vectors = None

        # Try semantic embeddings first.
        if SentenceTransformer is not None:
            try:
                model = SentenceTransformer("all-MiniLM-L6-v2")
                self.embeddings = model.encode(self.documents, normalize_embeddings=True)
                self.mode = "embeddings"
                return
            except Exception:
                # Fall through to TF-IDF fallback.
                pass

        # TF-IDF fallback (still much better than tag-overlap heuristic).
        if TfidfVectorizer is not None and cosine_similarity is not None:
            self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
            self.tfidf_matrix = self.vectorizer.fit_transform(self.documents)
            self.mode = "tfidf"
            return

        # Zero-dependency fallback: tiny TF-IDF implementation.
        tokenized = [doc.lower().split() for doc in self.documents]
        vocab = sorted({tok for toks in tokenized for tok in toks})
        if not vocab:
            return
        self.vocab = {tok: i for i, tok in enumerate(vocab)}
        doc_count = len(tokenized)
        df = [0] * len(vocab)
        for toks in tokenized:
            seen = {self.vocab[tok] for tok in set(toks)}
            for idx in seen:
                df[idx] += 1
        self.idf = [1.0 + (doc_count / (1 + count)) for count in df]
        self.lite_vectors = []
        for toks in tokenized:
            vec = [0.0] * len(vocab)
            if toks:
                for tok in toks:
                    vec[self.vocab[tok]] += 1.0
                length = float(len(toks))
                for i in range(len(vec)):
                    vec[i] = (vec[i] / length) * self.idf[i]
            self.lite_vectors.append(vec)
        self.mode = "lite_tfidf"

    def similar_indices(self, seed_idx: int, top_n: int) -> list[int]:
        if self.mode == "embeddings" and self.embeddings is not None:
            seed_vec = self.embeddings[seed_idx]
            scores = [sum(a * b for a, b in zip(vec, seed_vec)) for vec in self.embeddings]
        elif self.mode == "tfidf" and self.vectorizer is not None and self.tfidf_matrix is not None:
            seed_vec = self.tfidf_matrix[seed_idx]
            scores = cosine_similarity(seed_vec, self.tfidf_matrix).flatten().tolist()
        elif self.mode == "lite_tfidf" and self.lite_vectors is not None:
            seed_vec = self.lite_vectors[seed_idx]
            seed_norm = sum(v * v for v in seed_vec) ** 0.5
            scores = []
            for vec in self.lite_vectors:
                dot = sum(a * b for a, b in zip(vec, seed_vec))
                norm = (sum(v * v for v in vec) ** 0.5) * seed_norm
                scores.append(dot / norm if norm else 0.0)
        else:
            # Last-resort: deterministic order excluding seed.
            return [idx for idx in range(len(self.songs)) if idx != seed_idx][:top_n]

        order = sorted(range(len(scores)), key=lambda idx: scores[idx], reverse=True)
        order = [idx for idx in order if idx != seed_idx]
        return order[:top_n]


RETRIEVER = Retriever(CATALOG)
def _similarity(seed: Song, candidate: Song) -> float:
    if seed.title == candidate.title:
        return -1.0

    seed_tags = set(seed.tags)
    cand_tags = set(candidate.tags)
    overlap = len(seed_tags & cand_tags)
    return overlap / max(len(seed_tags | cand_tags), 1)


def recommend(song_name: str, top_n: int = 5) -> dict:
    matched_song, fuzzy = _match_title(song_name)
    if not matched_song:
        return {"error": "Song not found", "query": song_name}

    seed_idx = CATALOG.index(matched_song)
    indices = RETRIEVER.similar_indices(seed_idx, max(1, top_n))
    picks = [{"artist": CATALOG[idx].artist, "song": CATALOG[idx].title} for idx in indices]
    ranked = sorted(CATALOG, key=lambda song: _similarity(matched_song, song), reverse=True)
    picks = [
        {"artist": song.artist, "song": song.title}
        for song in ranked[: max(1, top_n)]
        if song.title != matched_song.title
    ]

    return {
        "query": song_name,
        "matched_song": matched_song.title,
        "fuzzy_match": fuzzy,
        "retrieval_mode": RETRIEVER.mode,
        "recommendations": picks,
    }


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)

        if parsed.path == "/api/health":
            self._send_json({"status": "ok"})
            return

        if parsed.path != "/api/recommend":
            self._send_json({"error": "Not found"}, status=404)
            return

        params = parse_qs(parsed.query)
        song_name = (params.get("song") or [""])[0].strip()
        top_n_raw = (params.get("top_n") or ["5"])[0]

        if not song_name:
            self._send_json({"error": "Query param 'song' is required"}, status=400)
            return

        try:
            top_n = int(top_n_raw)
        except ValueError:
            self._send_json({"error": "top_n must be an integer"}, status=400)
            return

        payload = recommend(song_name=song_name, top_n=top_n)
        if "error" in payload:
            self._send_json(payload, status=404)
            return

        self._send_json(payload)


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", 8001), Handler)
    print("Recommendation API running at http://localhost:8001")
    server.serve_forever()


if __name__ == "__main__":
    main()
