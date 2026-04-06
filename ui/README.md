# Responsive UI (Prototype)

This folder contains a responsive front-end for the music recommendation project.

## Run locally

Start the recommendation API (Terminal 1):

```bash
python backend/app.py
```

Then start the UI server (Terminal 2):

```bash
cd ui
python -m http.server 8000
```

Then open `http://localhost:8000` in your browser.

## Notes

- The UI now fetches recommendations from `http://localhost:8001/api/recommend`.
- The backend uses vector retrieval with automatic mode fallback:
  - `embeddings` mode via `sentence-transformers` when available
  - `tfidf` mode when scikit-learn is available
  - `lite_tfidf` mode as a zero-dependency fallback.
- You can swap backend ranking logic with notebook/model artifacts in a future step.
- The backend currently uses an in-memory demo catalog and fuzzy title matching.
- You can swap backend ranking logic with notebook/model artifacts in a future step.
- This is a UI prototype with mock recommendation data.
- It demonstrates exact + fuzzy title matching behavior and a mobile-first responsive layout.
- You can wire this UI to the notebook/model output via an API in a future step.
