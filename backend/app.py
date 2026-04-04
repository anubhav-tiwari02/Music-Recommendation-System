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


@dataclass(frozen=True)
class Song:
    artist: str
    title: str
    tags: tuple[str, ...]


CATALOG: List[Song] = [
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
