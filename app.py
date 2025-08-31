import os
import io
import sqlite3
from dataclasses import dataclass
from typing import List, Tuple, Optional

from flask import Flask, render_template, request, redirect, url_for, flash
from PIL import Image, UnidentifiedImageError
import imagehash
import requests

DB_PATH = os.path.join("data", "products.db")
UPLOAD_DIR = os.path.join("static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")  # replace in prod


@dataclass
class Product:
    id: int
    name: str
    category: str
    image_url: str
    price: float
    phash: str


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_products() -> List[Product]:
    if not os.path.exists(DB_PATH):
        return []
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, category, image_url, price, phash FROM products"
        ).fetchall()
    return [
        Product(
            id=row["id"],
            name=row["name"],
            category=row["category"],
            image_url=row["image_url"],
            price=row["price"],
            phash=row["phash"],
        )
        for row in rows
    ]


def compute_phash_from_pil(img: Image.Image) -> imagehash.ImageHash:
    # Normalize image for consistent hashes
    img = img.convert("RGB")
    return imagehash.phash(img)


def compute_phash_from_upload(file_storage) -> Optional[imagehash.ImageHash]:
    try:
        img = Image.open(file_storage.stream)
        return compute_phash_from_pil(img)
    except UnidentifiedImageError:
        return None


def compute_phash_from_url(url: str, timeout=8) -> Optional[imagehash.ImageHash]:
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content))
        return compute_phash_from_pil(img)
    except Exception:
        return None


def score_from_distance(dist: int) -> int:
    # pHash is 64 bits; convert Hamming distance to 0-100 score (higher is more similar)
    return max(0, min(100, int(round(100 * (1 - dist / 64.0)))))


def find_similar(phash_hex: str, products: List[Product], max_results=24) -> List[Tuple[Product, int]]:
    query_hash = imagehash.hex_to_hash(phash_hex)
    scored: List[Tuple[Product, int]] = []
    for p in products:
        try:
            dist = query_hash - imagehash.hex_to_hash(p.phash)
            score = score_from_distance(dist)
            scored.append((p, score))
        except Exception:
            continue
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:max_results]


@app.route("/", methods=["GET"])
def index():
    products = load_products()
    product_count = len(products)
    db_ready = os.path.exists(DB_PATH)
    return render_template("index.html", product_count=product_count, db_ready=db_ready)


@app.route("/search", methods=["POST"])
def search():
    if not os.path.exists(DB_PATH):
        flash("Product database not found. Please run scripts/build_index.py first.", "danger")
        return redirect(url_for("index"))

    min_score = int(request.form.get("min_score", 50))
    max_results = int(request.form.get("max_results", 24))

    file = request.files.get("image_file")
    image_url = request.form.get("image_url", "").strip()

    query_hash: Optional[imagehash.ImageHash] = None
    preview_path: Optional[str] = None

    if file and file.filename:
        # Save for preview
        safe_name = file.filename.replace("/", "_").replace("\\", "_")
        saved_path = os.path.join(UPLOAD_DIR, safe_name)
        file.stream.seek(0)
        file.save(saved_path)
        preview_path = "/" + saved_path.replace("\\", "/")
        # Re-open for hashing (ensure stream is fresh)
        with open(saved_path, "rb") as f:
            try:
                img = Image.open(f)
                query_hash = compute_phash_from_pil(img)
            except UnidentifiedImageError:
                query_hash = None

    elif image_url:
        query_hash = compute_phash_from_url(image_url)
        preview_path = image_url
    else:
        flash("Please provide an image file or an image URL.", "warning")
        return redirect(url_for("index"))

    if query_hash is None:
        flash("Could not process the image. Please try a different file or URL.", "danger")
        return redirect(url_for("index"))

    products = load_products()
    results = find_similar(str(query_hash), products, max_results=max_results)
    # server-side threshold filter
    results = [(p, s) for (p, s) in results if s >= min_score]

    return render_template(
        "results.html",
        preview_path=preview_path,
        results=results,
        min_score=min_score,
        max_results=max_results,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
