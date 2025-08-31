# Visual Product Matcher (Flask)

A simple, production-quality Flask app that finds visually similar products for an uploaded image or image URL. Uses perceptual hashing (pHash) for fast, reliable similarity without heavy GPU/ML dependencies.

## Features
- Upload image or paste image URL
- View uploaded image and similar products with similarity scores
- Filter results by score (server- and client-side)
- 60+ sample products with images and metadata (SQLite)
- Responsive UI (Bootstrap), loading states, and basic error handling

## Tech
Flask, SQLite, Pillow, ImageHash, Bootstrap.

## Quickstart (Local)
1. Python 3.10+ recommended. Create venv and install deps:
   - `python -m venv .venv && source .venv/bin/activate` (Windows: `.venv\Scripts\activate`)
   - `pip install -r requirements.txt`
2. Build the product database:
   - `python scripts/build_index.py`
3. Run the app:
   - `python app.py`
4. Open http://localhost:5000

## Deploy (Render free)
1. Push this repo to GitHub.
2. Create a new Web Service on Render:
   - Runtime: Python
   - Build command: `pip install -r requirements.txt && python scripts/build_index.py`
   - Start command: `gunicorn app:app`
3. Optional: set `SECRET_KEY` environment variable.

## Notes and Tradeoffs
- Similarity uses 64-bit pHash (fast and reliable for small datasets). Score is derived from Hamming distance.
- For higher semantic quality, you can upgrade to CLIP embeddings + FAISS, but pHash meets the brief within the 8-hour limit.

## Approach (≤200 words)
We index each product image with a perceptual hash (pHash), which captures visual structure. At query time (upload or URL), we compute the pHash of the input image and compare it to product hashes using Hamming distance. We convert distance to a 0–100 similarity score and sort the results. The product database (60 items) is stored in SQLite with names, categories, prices, and image URLs. The UI is built with Flask templates and Bootstrap, with a responsive grid, loading overlay during processing, and both server- and client-side score filtering for a smooth UX. This approach avoids heavy ML dependencies, deploys easily on free hosting, and remains accurate enough for a small catalog.
# visual-product-matcher
